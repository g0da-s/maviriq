import asyncio
import logging

from maviriq.agents import InsufficientDataError
from maviriq.agents.base import BaseAgent
from maviriq.config import settings
from maviriq.models.schemas import (
    MarketIntelligenceInput,
    MarketIntelligenceOutput,
)

logger = logging.getLogger(__name__)

QUERY_GENERATION_PROMPT = """\
You generate search queries to understand the market size, distribution channels, \
and monetization potential for a product idea.
Return 8-10 diverse search queries. Mix these types:
- Market sizing: "how many [target users]", "[idea] total addressable market"
- Monetization: '"[problem]" "will pay"', "[idea] pricing model"
- Distribution: "[idea] Shopify app OR Chrome extension", "[target user] community"
- Trends: "[idea] industry report", "[idea] market growth"
- Indie/startup signals: "site:indiehackers.com [idea]", "[idea] MRR"
Keep queries natural and varied. No quotes around the query text."""

RETRY_QUERY_GENERATION_PROMPT = """\
You generate BROADER search queries to understand market size, distribution, and monetization.
The first round of searches found insufficient data. Generate 8-10 NEW queries that are:
- Broader in scope (adjacent markets, larger industry categories)
- Targeting different data sources (reports, blog posts, investor decks)
- Using different phrasing and angles
- Looking for proxy metrics and analogous markets
Do NOT repeat queries from the previous round. No quotes around the query text."""

EXTRACTION_PROMPT = """\
You are a market intelligence analyst. Your job is to extract market sizing, \
distribution channels, and monetization signals from search results.

Rules:
- Estimate the total addressable market (TAM) based on available data. \
  Use order-of-magnitude estimates if exact numbers aren't available.
- Determine growth direction: "growing", "stable", "shrinking", or "unknown".
- Identify distribution channels: how can the founder reach target users? \
  Rate effort as "low", "medium", or "high".
- Extract monetization signals: evidence that people will pay for this. \
  Rate strength as "strong", "moderate", or "weak".
- If data is insufficient (very few relevant results), set data_quality to "partial".
- Do NOT fabricate data. If you can't find market size info, say "insufficient data" \
  and explain what you did find in tam_reasoning."""


class MarketIntelligenceAgent(BaseAgent[MarketIntelligenceInput, MarketIntelligenceOutput]):
    name = "Market Intelligence"
    description = "Researches market size, distribution channels, and monetization signals"

    async def run(self, input_data: MarketIntelligenceInput) -> MarketIntelligenceOutput:
        idea = input_data.idea
        result = await self._search_and_extract(idea, queries=None, previous=None)

        for attempt in range(settings.agent_max_retries):
            if result.data_quality != "partial":
                break
            logger.info(
                "Market intelligence returned partial data (attempt %d) — retrying with broader queries",
                attempt + 1,
            )
            retry_queries = await self.llm.generate_list(
                system_prompt=RETRY_QUERY_GENERATION_PROMPT,
                user_prompt=(
                    f"Idea: {idea}\n"
                    f"Previous queries (do NOT repeat): {result.search_queries_used}\n"
                    f"TAM reasoning so far: {result.tam_reasoning}"
                ),
                use_cheap_model=True,
            )
            result = await self._search_and_extract(idea, queries=retry_queries, previous=result)

        return result

    async def _search_and_extract(
        self,
        idea: str,
        queries: list[str] | None,
        previous: MarketIntelligenceOutput | None,
    ) -> MarketIntelligenceOutput:
        is_retry = queries is not None

        # Step 1: Generate search queries
        if queries is None:
            queries = await self.llm.generate_list(
                system_prompt=QUERY_GENERATION_PROMPT,
                user_prompt=f"Generate search queries for this idea: {idea}",
                use_cheap_model=True,
            )
            logger.info(f"Generated {len(queries)} market intelligence queries for '{idea}'")

        # Step 2: Run parallel searches across multiple sources
        if is_retry:
            search_tasks = [
                *[self.search.search(q) for q in queries],
                *[self.search.search_news(q) for q in queries[:4]],
                *[self.search.search_youtube(q) for q in queries[:2]],
            ]
        else:
            search_tasks = [
                *[self.search.search(q) for q in queries],
                *[self.search.search_news(q) for q in queries[:3]],
                self.search.search_producthunt(idea),
                self.search.search_crunchbase(idea),
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
                "Cannot produce reliable market intelligence results."
            )

        # Step 3: Feed snippets to LLM for structured extraction
        snippets_text = "\n\n".join(
            f"[{s['source']}] {s['title']}\n{s['url']}\n{s['snippet']}"
            for s in all_snippets[:50]
        )

        if previous is not None:
            channels_text = "\n".join(
                f"- {ch.channel} (reach: {ch.reach_estimate}, effort: {ch.effort})"
                for ch in previous.distribution_channels
            )
            signals_text = "\n".join(
                f"- [{sig.strength}] {sig.signal} (source: {sig.source})"
                for sig in previous.monetization_signals
            )
            user_prompt = (
                f"Idea: {idea}\n\n"
                f"Previous findings (include these plus any new ones):\n"
                f"Market size: {previous.market_size_estimate}\n"
                f"Growth: {previous.growth_direction}\n"
                f"Distribution channels:\n{channels_text}\n"
                f"Monetization signals:\n{signals_text}\n\n"
                f"New search results:\n\n{snippets_text}"
            )
        else:
            user_prompt = f"Idea: {idea}\n\nSearch results:\n\n{snippets_text}"

        result = await self.llm.generate_structured(
            system_prompt=EXTRACTION_PROMPT,
            user_prompt=user_prompt,
            output_schema=MarketIntelligenceOutput,
        )

        result.search_queries_used = queries
        return result
