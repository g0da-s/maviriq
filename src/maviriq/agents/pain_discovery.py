import asyncio
import logging

from maviriq.agents import InsufficientDataError
from maviriq.agents.base import BaseAgent
from maviriq.config import settings
from maviriq.models.schemas import (
    PainDiscoveryInput,
    PainDiscoveryOutput,
)

logger = logging.getLogger(__name__)

QUERY_GENERATION_PROMPT = """\
You generate search queries to find evidence of people struggling with a problem.
Return 6-8 diverse search queries. Mix these types:
- Direct complaints: "[topic] frustrating", "[topic] hard"
- Reddit-specific: "[topic] reddit complaints", "why does [topic] suck"
- Forum/community: "[topic] alternative needed", "better way to [topic]"
- Question-based: "how to [topic] without [pain]"
Keep queries natural and varied. No quotes around the query text."""

RETRY_QUERY_GENERATION_PROMPT = """\
You generate BROADER search queries to find evidence of people struggling with a problem.
The first round of searches found insufficient data. Generate 6-8 NEW queries that are:
- Broader in scope (less specific keywords)
- Targeting different communities or platforms
- Using different phrasing and angles
- Exploring adjacent problem spaces
Do NOT repeat queries from the previous round. No quotes around the query text."""

PAIN_EXTRACTION_PROMPT = """\
You are a market research analyst. Your job is to extract real pain points from search results.

Rules:
- Only extract GENUINE complaints or frustrations, not product reviews or marketing content.
- For each pain point, identify WHO is complaining based on context clues (their job title, \
the subreddit they posted in, how they describe themselves).
- Rate severity 1-5: 1=minor annoyance, 3=significant friction, 5=blocking/desperate.
- Group the complainers into user segments and count how many pain points each segment has.
- For willingness_to_pay, use ONLY one of these exact values: "high", "medium", or "low". No other text.
- Pick the PRIMARY target user: the segment with the most pain points AND highest severity.
- If the data is insufficient (fewer than 5 real pain points found), set data_quality to "partial".
- Do NOT fabricate quotes or sources. If a snippet is vague, skip it."""


class PainDiscoveryAgent(BaseAgent[PainDiscoveryInput, PainDiscoveryOutput]):
    name = "Pain & User Discovery"
    description = "Finds evidence that a problem exists and identifies who suffers from it"

    async def run(self, input_data: PainDiscoveryInput) -> PainDiscoveryOutput:
        idea = input_data.idea
        result = await self._search_and_extract(idea, queries=None, previous=None)

        for attempt in range(settings.agent_max_retries):
            if result.data_quality != "partial":
                break
            logger.info(
                "Pain discovery returned partial data (attempt %d) — retrying with broader queries",
                attempt + 1,
            )
            retry_queries = await self.llm.generate_list(
                system_prompt=RETRY_QUERY_GENERATION_PROMPT,
                user_prompt=(
                    f"Idea: {idea}\n"
                    f"Previous queries (do NOT repeat): {result.search_queries_used}\n"
                    f"Pain summary so far: {result.pain_summary}"
                ),
                use_cheap_model=True,
            )
            result = await self._search_and_extract(idea, queries=retry_queries, previous=result)

        return result

    async def _search_and_extract(
        self,
        idea: str,
        queries: list[str] | None,
        previous: PainDiscoveryOutput | None,
    ) -> PainDiscoveryOutput:
        is_retry = queries is not None

        # Step 1: Get queries (either generated or provided for retry)
        if queries is None:
            queries = await self.llm.generate_list(
                system_prompt=QUERY_GENERATION_PROMPT,
                user_prompt=f"Generate search queries for this idea: {idea}",
                use_cheap_model=True,
            )
            logger.info(f"Generated {len(queries)} search queries for '{idea}'")

        # Step 2: Run searches with source mix based on attempt
        if is_retry:
            search_tasks = [
                *[self.search.search_twitter(q) for q in queries[:3]],
                *[self.search.search_youtube(q) for q in queries[:2]],
                *[self.search.search_news(q) for q in queries[:2]],
                *[self.search.search(q) for q in queries],
            ]
        else:
            search_tasks = [
                *[self.search.search_reddit(q) for q in queries[:3]],
                *[self.search.search_hackernews(q) for q in queries[:2]],
                *[self.search.search(q) for q in queries],
                *[self.search.search_twitter(q) for q in queries[:2]],
                self.search.search_youtube(queries[0]),
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
        logger.info(f"Collected {len(all_snippets)} unique snippets ({failed_count}/{len(search_tasks)} searches failed)")

        if failed_count > len(search_tasks) * 0.5:
            raise InsufficientDataError(
                f"Too many search failures ({failed_count}/{len(search_tasks)}). "
                "Cannot produce reliable pain discovery results."
            )

        # Step 3: Feed all snippets to Claude for extraction
        snippets_text = "\n\n".join(
            f"[{s['source']}] {s['title']}\n{s['url']}\n{s['snippet']}"
            for s in all_snippets[:50]
        )

        # If retry, include previous pain points so the LLM can merge
        if previous is not None:
            previous_points = "\n".join(
                f'- "{p.quote}" (source: {p.source}, severity: {p.pain_severity})'
                for p in previous.pain_points
            )
            user_prompt = (
                f"Idea: {idea}\n\n"
                f"Previously found pain points (include these plus any new ones):\n"
                f"{previous_points}\n\n"
                f"New search results:\n\n{snippets_text}"
            )
        else:
            user_prompt = f"Idea: {idea}\n\nSearch results:\n\n{snippets_text}"

        result = await self.llm.generate_structured(
            system_prompt=PAIN_EXTRACTION_PROMPT,
            user_prompt=user_prompt,
            output_schema=PainDiscoveryOutput,
        )

        result.idea = idea
        result.search_queries_used = queries
        return result
