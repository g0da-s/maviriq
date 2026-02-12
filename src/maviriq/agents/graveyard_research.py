import asyncio
import logging

from maviriq.agents import InsufficientDataError
from maviriq.agents.base import BaseAgent
from maviriq.config import settings
from maviriq.models.schemas import (
    GraveyardResearchInput,
    GraveyardResearchOutput,
)

logger = logging.getLogger(__name__)

QUERY_GENERATION_PROMPT = """\
You generate search queries to find failed startups, shuttered products, and warning signs \
in a given market. The goal is to learn from past failures.
Return 8-10 diverse search queries. Mix these types:
- Failures: "[idea] startup failed", "site:failory.com [idea]", "[idea] post-mortem"
- Shutdowns: "[idea] shut down", "[idea] pivoted", "[idea] acqui-hired"
- Churn/dissatisfaction: "alternatives to [idea]", '"[idea]" cancelled OR churned'
- Competitor health: "[idea] startup funding round", "[idea] startup layoffs"
- Lessons: "[idea] lessons learned", "why [idea] startups fail"
Keep queries natural and varied. No quotes around the query text."""

RETRY_QUERY_GENERATION_PROMPT = """\
You generate BROADER search queries to find failed startups and warning signs in a market.
The first round of searches found insufficient data. Generate 8-10 NEW queries that are:
- Broader in scope (adjacent markets, wider industry failures)
- Targeting different sources (blog posts, podcasts, investor analyses)
- Using different phrasing and angles
- Looking for indirect signals (layoffs, pivots, acquisition-hires)
Do NOT repeat queries from the previous round. No quotes around the query text."""

EXTRACTION_PROMPT = """\
You are a startup failure analyst. Your job is to extract information about previous \
attempts, failures, and warning signs from search results.

Rules:
- Identify previous attempts: startups that tried something similar and failed or shut down. \
  Include what they did, why they shut down, and when (if available).
- Extract failure reasons: common reasons why startups in this space fail.
- Summarize lessons learned: what must the founder do differently to succeed?
- Identify churn signals: evidence that users leave existing products. \
  Rate severity as "high", "medium", or "low".
- Identify competitor health signals: evidence about whether existing players are \
  thriving or struggling. Direction: "positive", "negative", or "neutral".
- If data is insufficient (no failed startups found), set data_quality to "partial" \
  and note that the space may be untested.
- Do NOT fabricate failed startups. Only report what you find in the data."""


class GraveyardResearchAgent(BaseAgent[GraveyardResearchInput, GraveyardResearchOutput]):
    name = "Graveyard Research"
    description = "Finds failed startups and warning signs in the market"

    async def run(self, input_data: GraveyardResearchInput) -> GraveyardResearchOutput:
        idea = input_data.idea
        result = await self._search_and_extract(idea, queries=None, previous=None)

        for attempt in range(settings.agent_max_retries):
            if result.data_quality != "partial":
                break
            logger.info(
                "Graveyard research returned partial data (attempt %d) — retrying with broader queries",
                attempt + 1,
            )
            retry_queries = await self.llm.generate_list(
                system_prompt=RETRY_QUERY_GENERATION_PROMPT,
                user_prompt=(
                    f"Idea: {idea}\n"
                    f"Previous queries (do NOT repeat): {result.search_queries_used}\n"
                    f"Lessons so far: {result.lessons_learned}"
                ),
                use_cheap_model=True,
            )
            result = await self._search_and_extract(idea, queries=retry_queries, previous=result)

        return result

    async def _search_and_extract(
        self,
        idea: str,
        queries: list[str] | None,
        previous: GraveyardResearchOutput | None,
    ) -> GraveyardResearchOutput:
        is_retry = queries is not None

        # Step 1: Generate search queries
        if queries is None:
            queries = await self.llm.generate_list(
                system_prompt=QUERY_GENERATION_PROMPT,
                user_prompt=f"Generate search queries for this idea: {idea}",
                use_cheap_model=True,
            )
            logger.info(f"Generated {len(queries)} graveyard research queries for '{idea}'")

        # Step 2: Run parallel searches across multiple sources
        if is_retry:
            search_tasks = [
                *[self.search.search(q) for q in queries],
                *[self.search.search_news(q) for q in queries[:4]],
                *[self.search.search_twitter(q) for q in queries[:2]],
                *[self.search.search_youtube(q) for q in queries[:2]],
            ]
        else:
            search_tasks = [
                *[self.search.search(q) for q in queries],
                *[self.search.search_news(q) for q in queries[:3]],
                *[self.search.search_reddit(q) for q in queries[:2]],
                *[self.search.search_hackernews(q) for q in queries[:2]],
            ]

        results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Deduplicate and collect all snippets
        seen_urls: set[str] = set()
        all_snippets: list[dict] = []
        for r in results_lists:
            if isinstance(r, Exception):
                logger.warning(f"Search failed: {r}")
                continue
            for item in r:
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    all_snippets.append(item.to_dict())

        failed_count = sum(1 for r in results_lists if isinstance(r, Exception))
        logger.info(
            f"Collected {len(all_snippets)} unique snippets "
            f"({failed_count}/{len(search_tasks)} searches failed)"
        )

        if failed_count > len(search_tasks) * 0.5:
            raise InsufficientDataError(
                f"Too many search failures ({failed_count}/{len(search_tasks)}). "
                "Cannot produce reliable graveyard research results."
            )

        # Step 3: Feed snippets to LLM for structured extraction
        snippets_text = "\n\n".join(
            f"[{s['source']}] {s['title']}\n{s['url']}\n{s['snippet']}"
            for s in all_snippets[:50]
        )

        if previous is not None:
            prev_attempts = "\n".join(
                f"- {a.name}: {a.what_they_did} → {a.shutdown_reason}"
                for a in previous.previous_attempts
            )
            user_prompt = (
                f"Idea: {idea}\n\n"
                f"Previous findings (include these plus any new ones):\n"
                f"Previous attempts:\n{prev_attempts}\n"
                f"Failure reasons: {previous.failure_reasons}\n"
                f"Lessons: {previous.lessons_learned}\n\n"
                f"New search results:\n\n{snippets_text}"
            )
        else:
            user_prompt = f"Idea: {idea}\n\nSearch results:\n\n{snippets_text}"

        result = await self.llm.generate_structured(
            system_prompt=EXTRACTION_PROMPT,
            user_prompt=user_prompt,
            output_schema=GraveyardResearchOutput,
        )

        result.search_queries_used = queries
        return result
