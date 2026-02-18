from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from maviriq.agents.base import BaseAgent
from maviriq.agents.tools import build_tools_for_agent
from maviriq.models.schemas import MarketIntelligenceInput, MarketIntelligenceOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a market intelligence analyst. Your mission is to estimate market size, \
identify distribution channels, and assess market growth for a product idea.

You have access to search tools. Use them strategically:
1. Search Google for market size reports, TAM estimates, and industry analyses.
2. Search Google News for recent market trends and growth signals.
3. Search Product Hunt for product launches and maker community signals.
4. Search Crunchbase for funding activity and market validation.
5. Refine your queries based on what you find — chase promising leads.

You can call multiple search tools in a single turn for parallel execution.

TAM ESTIMATION — BE HONEST ABOUT SCOPE:
- Search results will give you BROAD market numbers (e.g., "$50B project management \
  market"). That is NOT the TAM for the founder's specific idea.
- Always narrow down: "The broad [category] market is $XB, but this idea targets \
  [specific niche], which is roughly [X%] of that = $Y."
- Show your reasoning in tam_reasoning. If you can't narrow it, say so explicitly: \
  "This is the broad category number; the actual niche TAM is likely much smaller \
  but I couldn't find specific data."
- Do NOT present a broad market number as if it's the addressable market for this idea.
- If you can't find any market size data, say "insufficient data" — do NOT guess.

MARKET GROWTH — REQUIRE EVIDENCE:
- Do NOT guess growth_direction from the TAM number alone. A large market can be \
  shrinking and a small market can be growing fast.
- Look for CAGR, year-over-year growth rates, or analyst projections in the market \
  size reports you already find (these reports almost always include growth data).
- Set growth_direction based on what you find:
  - "growing" = evidence of positive growth (CAGR > 5%, expanding demand)
  - "stable" = growth is flat or low single digits
  - "shrinking" = declining revenue, shrinking user base, or negative CAGR
  - "unknown" = you could not find any growth data — do NOT default to "growing"
- In growth_evidence, cite the specific data point (e.g., "AI code review market \
  projected to grow at 25% CAGR through 2028 — Grand View Research"). Keep it to \
  1-2 sentences. If you found nothing, say "No specific growth data found."

EXTRACTION RULES:
- Identify distribution channels: where can the founder reach potential users? \
  Think about where these users already spend time online and offline. \
  Rate effort as "low", "medium", or "high".
- Extract funding signals: evidence of investment activity in this space. \
  List recent funding rounds, acquisitions, or VC interest you find on Crunchbase \
  or in news articles. These indicate market validation (or lack thereof). \
  For each signal, provide it as an object with "description" (the signal text) \
  and "source_url" (the URL where you found this information, or null if unknown).
- Do NOT fabricate data.

NOTE: You do NOT need to assess monetization or pricing — the Competitor Research \
agent handles that separately.

When you have gathered enough market intelligence, call submit_result with \
your structured findings."""

TOOL_NAMES = [
    "search_web",
    "search_news",
    "search_producthunt",
    "search_crunchbase",
]


class MarketIntelligenceAgent(BaseAgent[MarketIntelligenceInput, MarketIntelligenceOutput]):
    name = "Market Intelligence"
    description = "Researches market size, growth trends, distribution channels, and funding activity"
    output_schema = MarketIntelligenceOutput

    def get_system_prompt(self, input_data: MarketIntelligenceInput) -> str:
        return SYSTEM_PROMPT

    def get_user_prompt(self, input_data: MarketIntelligenceInput) -> str:
        return (
            f"Research the market opportunity for this business idea:\n\n"
            f"IDEA: {input_data.idea}\n\n"
            f"Estimate market size (narrow to the specific niche), identify "
            f"distribution channels, and find funding activity signals. "
            f"Use multiple search tools and diverse queries."
        )

    def get_tools(self) -> list[dict[str, Any]]:
        schemas, _ = build_tools_for_agent(self.search, TOOL_NAMES)
        return schemas

    def get_tool_executors(self) -> dict[str, Callable[[str], Awaitable[str]]]:
        _, executors = build_tools_for_agent(self.search, TOOL_NAMES)
        return executors
