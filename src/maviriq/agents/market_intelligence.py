from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from maviriq.agents.base import BaseAgent
from maviriq.agents.tools import build_tools_for_agent
from maviriq.models.schemas import MarketIntelligenceInput, MarketIntelligenceOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a market intelligence analyst. Your mission is to estimate market size, \
identify distribution channels, and extract monetization signals for a product idea.

You have access to search tools. Use them strategically:
1. Search Google for market size reports, TAM estimates, and industry analyses.
2. Search Google News for recent market trends and growth signals.
3. Search Product Hunt for product launches and maker community signals.
4. Search Crunchbase for funding activity and market validation.
5. Search YouTube for market analysis videos and product reviews.
6. Search Reddit for indie hacker discussions and monetization evidence.
7. Refine your queries based on what you find — chase promising leads.

You can call multiple search tools in a single turn for parallel execution.

EXTRACTION RULES:
- Estimate total addressable market (TAM). Use order-of-magnitude if exact \
  numbers aren't available. Explain your reasoning in tam_reasoning.
- For growth_direction, use ONLY: "growing", "stable", "shrinking", or "unknown".
- Identify distribution channels: how can the founder reach users? \
  Rate effort as "low", "medium", or "high".
- Extract monetization signals: evidence that people will pay. \
  Rate strength as "strong", "moderate", or "weak".
- If data is insufficient, set data_quality to "partial".
- Do NOT fabricate data. If you can't find market size info, say "insufficient data" \
  and explain what you did find in tam_reasoning.

When you have gathered enough market intelligence, call submit_result with \
your structured findings."""

TOOL_NAMES = [
    "search_web",
    "search_news",
    "search_producthunt",
    "search_crunchbase",
    "search_youtube",
    "search_reddit",
]


class MarketIntelligenceAgent(BaseAgent[MarketIntelligenceInput, MarketIntelligenceOutput]):
    name = "Market Intelligence"
    description = "Researches market size, distribution channels, and monetization signals"
    output_schema = MarketIntelligenceOutput

    def get_system_prompt(self, input_data: MarketIntelligenceInput) -> str:
        return SYSTEM_PROMPT

    def get_user_prompt(self, input_data: MarketIntelligenceInput) -> str:
        return (
            f"Research the market opportunity for this business idea:\n\n"
            f"IDEA: {input_data.idea}\n\n"
            f"Estimate market size, identify distribution channels, and find "
            f"evidence of monetization potential. Use multiple search tools "
            f"and diverse queries."
        )

    def get_tools(self) -> list[dict[str, Any]]:
        schemas, _ = build_tools_for_agent(self.search, TOOL_NAMES)
        return schemas

    def get_tool_executors(self) -> dict[str, Callable[[str], Awaitable[str]]]:
        _, executors = build_tools_for_agent(self.search, TOOL_NAMES)
        return executors
