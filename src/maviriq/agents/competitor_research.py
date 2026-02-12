from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from maviriq.agents.base import BaseAgent
from maviriq.agents.tools import build_tools_for_agent
from maviriq.models.schemas import CompetitorResearchInput, CompetitorResearchOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a competitive intelligence analyst. Your mission is to map the \
competitive landscape for a business idea.

You have access to search tools. Use them strategically:
1. Start with broad Google searches to find direct competitors.
2. Search G2 and Capterra for software reviews, ratings, and comparisons.
3. Search Product Hunt for recent product launches in this space.
4. Search Crunchbase for startup funding and company information.
5. Search LinkedIn Jobs to gauge hiring activity and market demand.
6. Search Google News for recent competitive moves and announcements.
7. Refine your queries based on what you find — dig deeper on competitors.

You can call multiple search tools in a single turn for parallel execution.

EXTRACTION RULES:
- For each competitor: extract name, URL, one-liner description.
- Extract pricing tiers if mentioned in search results (plan name, price, features).
- Extract strengths and weaknesses from review snippets.
- For review_sentiment, use ONLY: "positive", "mixed", or "negative".
- For review_count, use the number if mentioned, otherwise null.
- For source, indicate where you found it: "google", "g2", "capterra", etc.
- Synthesize market saturation: ONLY "low", "medium", or "high".
- Determine average price point across competitors.
- List common complaints users have about existing solutions.
- Identify underserved needs (gaps in the market).
- Set data_quality to "partial" if fewer than 5 competitors found.
- Do NOT fabricate competitors. Only report what you find in the data.

When you have mapped the landscape (aim for 5-10 competitors with details), \
call submit_result with your structured findings."""

TOOL_NAMES = [
    "search_web",
    "search_g2",
    "search_capterra",
    "search_producthunt",
    "search_crunchbase",
    "search_linkedin_jobs",
    "search_news",
]


class CompetitorResearchAgent(BaseAgent[CompetitorResearchInput, CompetitorResearchOutput]):
    name = "Competitor Research"
    description = "Maps the competitive landscape and finds market gaps"
    output_schema = CompetitorResearchOutput

    def get_system_prompt(self, input_data: CompetitorResearchInput) -> str:
        return SYSTEM_PROMPT

    def get_user_prompt(self, input_data: CompetitorResearchInput) -> str:
        target_label = (
            input_data.target_user.label if input_data.target_user else "general users"
        )
        return (
            f"Research the competitive landscape for this business idea:\n\n"
            f"IDEA: {input_data.idea}\n"
            f"TARGET USER: {target_label}\n\n"
            f"Find competitors, their pricing, strengths/weaknesses, and market gaps. "
            f"Use multiple search tools and diverse queries."
        )

    def get_tools(self) -> list[dict[str, Any]]:
        schemas, _ = build_tools_for_agent(self.search, TOOL_NAMES)
        return schemas

    def get_tool_executors(self) -> dict[str, Callable[[str], Awaitable[str]]]:
        _, executors = build_tools_for_agent(self.search, TOOL_NAMES)
        return executors

    def post_process(
        self, input_data: CompetitorResearchInput, result: CompetitorResearchOutput
    ) -> CompetitorResearchOutput:
        if input_data.target_user is not None:
            result.target_user = input_data.target_user
        return result
