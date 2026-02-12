from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from maviriq.agents.base import BaseAgent
from maviriq.agents.tools import build_tools_for_agent
from maviriq.models.schemas import PainDiscoveryInput, PainDiscoveryOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a market research analyst specializing in pain discovery. Your mission \
is to find REAL evidence that people struggle with a specific problem.

You have access to search tools. Use them strategically:
1. Start with broad searches to understand the landscape.
2. Search Reddit and Hacker News for genuine complaints and frustrations.
3. Search Twitter for real-time opinions and complaints.
4. Search YouTube for video reviews that mention pain points.
5. Search Google News for industry coverage of the problem.
6. Refine your queries based on what you find — go deeper on promising leads.

You can call multiple search tools in a single turn for parallel execution.

EXTRACTION RULES:
- Only extract GENUINE complaints or frustrations, not product reviews or marketing.
- For each pain point, the quote must be a real snippet from the search results. \
  Do NOT fabricate quotes or sources.
- For source_url, use the actual URL from search results.
- Rate severity 1-5: 1=minor annoyance, 3=significant friction, 5=blocking/desperate.
- For author_context, infer from clues (subreddit, how they describe themselves, \
  job title mentions). If unclear, say "unknown user".
- Group complainers into user segments and count how many pain points each has.
- For willingness_to_pay, use ONLY: "high", "medium", or "low".
- Pick the PRIMARY target user: the segment with the most pain AND highest severity.
- Set data_quality to "partial" if fewer than 5 real pain points found.

When you have gathered enough evidence (aim for 5-15 pain points across multiple \
sources), call submit_result with your structured findings."""

TOOL_NAMES = [
    "search_web",
    "search_reddit",
    "search_hackernews",
    "search_twitter",
    "search_youtube",
    "search_news",
]


class PainDiscoveryAgent(BaseAgent[PainDiscoveryInput, PainDiscoveryOutput]):
    name = "Pain & User Discovery"
    description = "Finds evidence that a problem exists and identifies who suffers from it"
    output_schema = PainDiscoveryOutput

    def get_system_prompt(self, input_data: PainDiscoveryInput) -> str:
        return SYSTEM_PROMPT

    def get_user_prompt(self, input_data: PainDiscoveryInput) -> str:
        return (
            f"Research this business idea and find evidence of real pain points:\n\n"
            f"IDEA: {input_data.idea}\n\n"
            f"Search for genuine complaints, frustrations, and unmet needs related "
            f"to this idea. Use multiple search tools and diverse queries."
        )

    def get_tools(self) -> list[dict[str, Any]]:
        schemas, _ = build_tools_for_agent(self.search, TOOL_NAMES)
        return schemas

    def get_tool_executors(self) -> dict[str, Callable[[str], Awaitable[str]]]:
        _, executors = build_tools_for_agent(self.search, TOOL_NAMES)
        return executors

    def post_process(
        self, input_data: PainDiscoveryInput, result: PainDiscoveryOutput
    ) -> PainDiscoveryOutput:
        result.idea = input_data.idea
        return result
