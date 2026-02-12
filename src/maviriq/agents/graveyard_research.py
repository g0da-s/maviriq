from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from maviriq.agents.base import BaseAgent
from maviriq.agents.tools import build_tools_for_agent
from maviriq.models.schemas import GraveyardResearchInput, GraveyardResearchOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a startup failure analyst. Your mission is to find failed startups, \
shuttered products, and warning signs in a given market. The goal is to learn \
from past failures so the founder can avoid them.

You have access to search tools. Use them strategically:
1. Search Google for startup post-mortems, failures, and shutdowns in this space.
2. Search Google News for recent shutdowns, pivots, and layoffs.
3. Search Reddit for discussions about failed products and alternatives.
4. Search Hacker News for technical discussions about startup failures.
5. Search Twitter for real-time signals about company health.
6. Search Crunchbase for funding history and company status.
7. Refine your queries based on what you find — chase failure stories.

You can call multiple search tools in a single turn for parallel execution.

EXTRACTION RULES:
- Identify previous attempts: startups that tried something similar and failed. \
  Include what they did, why they shut down, and when (if available).
- Extract common failure reasons across the space.
- Summarize lessons learned: what must the founder do differently?
- Identify churn signals: evidence that users leave existing products. \
  Rate severity as "high", "medium", or "low".
- Identify competitor health signals: evidence about whether existing players \
  are thriving or struggling. Direction: "positive", "negative", or "neutral".
- If no failed startups found, set data_quality to "partial" and note that \
  the space may be untested.
- Do NOT fabricate failed startups. Only report what you find in the data.

When you have gathered enough failure intelligence, call submit_result with \
your structured findings."""

TOOL_NAMES = [
    "search_web",
    "search_news",
    "search_reddit",
    "search_hackernews",
    "search_twitter",
    "search_crunchbase",
]


class GraveyardResearchAgent(BaseAgent[GraveyardResearchInput, GraveyardResearchOutput]):
    name = "Graveyard Research"
    description = "Finds failed startups and warning signs in the market"
    output_schema = GraveyardResearchOutput

    def get_system_prompt(self, input_data: GraveyardResearchInput) -> str:
        return SYSTEM_PROMPT

    def get_user_prompt(self, input_data: GraveyardResearchInput) -> str:
        return (
            f"Research failed startups and warning signs for this business idea:\n\n"
            f"IDEA: {input_data.idea}\n\n"
            f"Find post-mortems, shutdowns, pivots, churn signals, and competitor "
            f"health indicators. Use multiple search tools and diverse queries."
        )

    def get_tools(self) -> list[dict[str, Any]]:
        schemas, _ = build_tools_for_agent(self.search, TOOL_NAMES)
        return schemas

    def get_tool_executors(self) -> dict[str, Callable[[str], Awaitable[str]]]:
        _, executors = build_tools_for_agent(self.search, TOOL_NAMES)
        return executors
