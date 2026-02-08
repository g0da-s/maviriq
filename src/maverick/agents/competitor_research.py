import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from maverick.agents.base import BaseAgent
from maverick.models.schemas import (
    CompetitorResearchInput,
    CompetitorResearchOutput,
)

logger = logging.getLogger(__name__)

COMPETITOR_SEARCH_QUERIES_PROMPT = """\
Generate 5-7 search queries to find competitors for this idea.
Include:
- "[idea] software", "[idea] tools"
- "best [idea] app", "[idea] SaaS"
- "[target user] tools for [problem]"
- Specific competitor sites: "site:g2.com [idea]", "site:capterra.com [idea]"
Keep natural and varied."""

COMPETITOR_ANALYSIS_PROMPT = """\
You are a competitive intelligence analyst. Extract competitor information from search results.

For each competitor found:
- Extract name, URL, what they do (one-liner)
- Pricing tiers (from search snippets or pricing pages)
- Strengths and weaknesses (from review snippets if available)
- Review sentiment and count if mentioned

Then synthesize:
- Market saturation: use ONLY one of "low", "medium", or "high"
- Average price point (free, $10-50/mo, $50-200/mo, enterprise)
- Common complaints across competitors
- Underserved needs (gaps in existing solutions)

For review_sentiment, use ONLY one of: "positive", "mixed", or "negative". No other text.
If fewer than 5 competitors found, set data_quality to "partial".
Do NOT fabricate competitors. Only report what you find in the data."""


class CompetitorResearchAgent(BaseAgent[CompetitorResearchInput, CompetitorResearchOutput]):
    name = "Competitor Research"
    description = "Maps the competitive landscape and finds market gaps"

    async def run(self, input_data: CompetitorResearchInput) -> CompetitorResearchOutput:
        idea = input_data.idea
        target_user = input_data.target_user

        # Step 1: Generate search queries
        queries = await self.llm.generate_list(
            system_prompt=COMPETITOR_SEARCH_QUERIES_PROMPT,
            user_prompt=f"Idea: {idea}\nTarget user: {target_user.label}",
            use_cheap_model=True,
        )
        logger.info(f"Generated {len(queries)} competitor search queries")

        # Step 2: Run searches (including G2/Capterra)
        search_tasks = [
            *[self.search.search(q) for q in queries],
            self.search.search_g2(idea),
            self.search.search_capterra(idea),
        ]

        results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Collect unique results
        seen_urls: set[str] = set()
        all_results: list[dict] = []
        for result in results_lists:
            if isinstance(result, Exception):
                logger.warning(f"Search failed: {result}")
                continue
            for r in result:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r.to_dict())

        logger.info(f"Found {len(all_results)} unique results")

        # Step 3: For top 10 competitors, try to scrape pricing pages
        # (Simple heuristic: look for URLs that seem like product pages)
        pricing_data = await self._scrape_pricing_pages(all_results[:10])

        # Step 4: Feed everything to Claude for structured extraction
        search_text = "\n\n".join(
            f"[{r['source']}] {r['title']}\n{r['url']}\n{r['snippet']}"
            for r in all_results[:40]
        )

        pricing_text = "\n\n".join(
            f"Pricing from {url}:\n{text}" for url, text in pricing_data.items()
        )

        result = await self.llm.generate_structured(
            system_prompt=COMPETITOR_ANALYSIS_PROMPT,
            user_prompt=f"Idea: {idea}\nTarget user: {target_user.label}\n\n"
            f"Search results:\n{search_text}\n\n"
            f"Pricing pages:\n{pricing_text}",
            output_schema=CompetitorResearchOutput,
        )

        result.target_user = target_user
        return result

    async def _scrape_pricing_pages(self, results: list[dict]) -> dict[str, str]:
        """Try to scrape pricing pages for top competitors."""
        pricing_data: dict[str, str] = {}

        async def scrape_one(url: str) -> tuple[str, str | None]:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    # Simple extraction: get text from HTML
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Look for pricing-related keywords
                    for tag in soup.find_all(["div", "section", "table"]):
                        text = tag.get_text(separator=" ", strip=True)
                        if any(
                            keyword in text.lower()
                            for keyword in ["pricing", "price", "$", "plan", "free", "trial"]
                        ):
                            if len(text) < 2000:  # Keep it short
                                return url, text[:1000]
                    return url, None
            except Exception as e:
                logger.debug(f"Failed to scrape {url}: {e}")
                return url, None

        tasks = [scrape_one(r["url"]) for r in results if "pricing" in r["url"].lower()]
        results_tuples = await asyncio.gather(*tasks)

        for url, text in results_tuples:
            if text:
                pricing_data[url] = text

        return pricing_data
