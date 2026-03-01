from __future__ import annotations

import logging
from datetime import datetime, timezone

from maviriq.agents.base import BaseAgent, ToolExecutors, ToolSchemas
from maviriq.agents.tools import build_tools_for_agent
from maviriq.models.schemas import ContextResearchInput, ContextResearchOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a research analyst. Your ONLY job is to build a context briefing \
about a business idea so that downstream research agents can do their work \
with full, up-to-date understanding.

You are NOT evaluating the idea. You are NOT finding competitors or pain \
points. You are building CONTEXT — what is this idea, what space is it in, \
what's happening in that space right now.

This is critical because your knowledge has a training cutoff. The idea may \
reference tools, platforms, regulations, or trends that launched AFTER your \
training. You MUST search to fill in any gaps.

═══ SEARCH STRATEGY (aim for 2-3 rounds, max 4) ═══

Turn 1 (parallel):
- search_web: the idea itself — what is it, how does it work, who uses it. \
  If the idea mentions a specific product/platform/technology you don't \
  recognize, search for it directly.
- search_news: recent news in the domain/space (add "{current_year}" to \
  your query for recency)

Turn 2 (parallel):
- search_web: key players, tools, and platforms in this space right now
- search_producthunt or search_hackernews: recent launches and discussions \
  in this space

Turn 3 (if gaps remain):
- Fill any remaining gaps, then submit immediately. Do NOT over-research.

═══ OUTPUT GUIDELINES ═══

- idea_analysis: 2-4 sentences. What is this idea? How would it work? \
  Who is the intended user? If the idea references something you had to \
  look up, explain it.
- current_landscape: 2-4 sentences. What's the current state of this space? \
  Is it crowded? Emerging? Regulated? Are there dominant players?
- key_players: 2-4 sentences. Name specific companies/products that operate \
  in or adjacent to this space. Include recent entrants.
- recent_developments: 2-4 sentences. What has changed in the last 6 months? \
  New launches, funding rounds, regulatory changes, market shifts? If nothing \
  recent stands out, say so.

Be factual and cite what you found. If searches reveal nothing about a \
specific field, say "No relevant information found" — do NOT invent context.

Today's date is {current_date}."""

TOOL_NAMES = [
    "search_web",
    "search_news",
    "search_hackernews",
    "search_producthunt",
]


class ContextResearchAgent(
    BaseAgent[ContextResearchInput, ContextResearchOutput]
):
    name = "Context Research"
    description = "Builds up-to-date context about the idea and its landscape"
    output_schema = ContextResearchOutput

    def get_system_prompt(self, input_data: ContextResearchInput) -> str:
        now = datetime.now(timezone.utc)
        return SYSTEM_PROMPT.format(
            current_year=now.year,
            current_date=now.strftime("%Y-%m-%d"),
        )

    def get_user_prompt(self, input_data: ContextResearchInput) -> str:
        return (
            f"Build a context briefing for this business idea:\n\n"
            f"IDEA: {input_data.idea}\n\n"
            f"Search to understand what this idea is about, what's happening "
            f"in the space right now, and any recent developments. "
            f"Fire off parallel searches in your first turn."
        )

    def get_tools_and_executors(self) -> tuple[ToolSchemas, ToolExecutors]:
        return build_tools_for_agent(self.search, TOOL_NAMES)
