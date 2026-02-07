import asyncio
import logging

from maverick.agents.base import BaseAgent
from maverick.models.schemas import (
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

PAIN_EXTRACTION_PROMPT = """\
You are a market research analyst. Your job is to extract real pain points from search results.

Rules:
- Only extract GENUINE complaints or frustrations, not product reviews or marketing content.
- For each pain point, identify WHO is complaining based on context clues (their job title, \
the subreddit they posted in, how they describe themselves).
- Rate severity 1-5: 1=minor annoyance, 3=significant friction, 5=blocking/desperate.
- Group the complainers into user segments and count how many pain points each segment has.
- Pick the PRIMARY target user: the segment with the most pain points AND highest severity.
- If the data is insufficient (fewer than 5 real pain points found), set data_quality to "partial".
- Do NOT fabricate quotes or sources. If a snippet is vague, skip it."""


class PainDiscoveryAgent(BaseAgent[PainDiscoveryInput, PainDiscoveryOutput]):
    name = "Pain & User Discovery"
    description = "Finds evidence that a problem exists and identifies who suffers from it"

    async def run(self, input_data: PainDiscoveryInput) -> PainDiscoveryOutput:
        idea = input_data.idea

        # Step 1: Generate search queries using cheap model
        queries = await self.llm.generate_list(
            system_prompt=QUERY_GENERATION_PROMPT,
            user_prompt=f"Generate search queries for this idea: {idea}",
            use_cheap_model=True,
        )
        logger.info(f"Generated {len(queries)} search queries for '{idea}'")

        # Step 2: Run searches in parallel (Reddit, HN, and broad)
        reddit_queries = queries[:3]  # First 3 queries target Reddit
        hn_queries = queries[:2]  # First 2 for Hacker News
        broad_queries = queries  # All for broad search

        search_tasks = [
            *[self.search.search_reddit(q) for q in reddit_queries],
            *[self.search.search_hackernews(q) for q in hn_queries],
            *[self.search.search(q) for q in broad_queries],
        ]

        results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Deduplicate and collect all snippets
        seen_urls: set[str] = set()
        all_snippets: list[dict] = []
        for result in results_lists:
            if isinstance(result, Exception):
                logger.warning(f"Search failed: {result}")
                continue
            for r in result:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_snippets.append(r.to_dict())

        logger.info(f"Collected {len(all_snippets)} unique snippets")

        # Step 3: Feed all snippets to Claude for extraction
        snippets_text = "\n\n".join(
            f"[{s['source']}] {s['title']}\n{s['url']}\n{s['snippet']}"
            for s in all_snippets[:50]  # Cap at 50 to stay within token limits
        )

        result = await self.llm.generate_structured(
            system_prompt=PAIN_EXTRACTION_PROMPT,
            user_prompt=f"Idea: {idea}\n\nSearch results:\n\n{snippets_text}",
            output_schema=PainDiscoveryOutput,
        )

        # Attach metadata
        result.idea = idea
        result.search_queries_used = queries

        return result
