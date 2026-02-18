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
1. FIRST: Search for obvious market leaders and incumbents. Every category has \
   well-known players — search for "[category] market leaders", "[category] top \
   companies", "best [category] tools". Missing a household name like Salesforce \
   in CRM or Mailchimp in email marketing is a critical error.
2. Search G2 and Capterra for software reviews, ratings, and comparisons.
3. Search Product Hunt for recent product launches in this space.
4. Search Indie Hackers for bootstrapped competitors, revenue reports, and founder stories.
5. Search Crunchbase for startup funding and company information.
6. Refine your queries based on what you find — dig deeper on competitors.
8. IMPORTANT: After finding competitors, search for each one's pricing \
   (e.g. "[name] pricing", "[name] plans"). Pricing rarely appears in \
   initial snippets — you must search for it explicitly. Do NOT submit \
   until you have attempted pricing searches for your top competitors.

You can call multiple search tools in a single turn for parallel execution.

EXTRACTION RULES:
- For each competitor: extract name, URL, one-liner description.
- Classify each competitor's type:
  "direct" = solves the same problem for the same audience (e.g., Figma vs Sketch)
  "indirect" = solves a related problem or serves a different audience but users \
    might use it instead (e.g., Google Docs vs Notion for note-taking)
  "potential" = large company that could easily enter this space but hasn't yet \
    (e.g., Apple entering a new market)
- Extract pricing tiers if mentioned in search results (plan name, price, features).
- Extract strengths and weaknesses from review snippets.
- For review_sentiment, use ONLY: "positive", "mixed", or "negative".
- For review_count, use the number if mentioned, otherwise null.
- For source, indicate where you found it: "google", "g2", "capterra", etc.
- Synthesize market saturation: ONLY "low", "medium", or "high". Use these criteria:
  "low" = 0-2 direct competitors, no dominant player with millions of users, \
    fragmented or nascent market (e.g., a niche developer tool with 1-2 small startups)
  "medium" = 3-6 direct competitors, some funded but no single player dominates, \
    room for a differentiated new entrant (e.g., API documentation tools)
  "high" = 7+ direct competitors OR any competitor with >$100M revenue or millions \
    of users, entrenched players with strong network effects or switching costs \
    (e.g., CRM with Salesforce/HubSpot, email marketing with Mailchimp/ConvertKit, \
    project management with Jira/Asana/Monday)
- Determine average price point across competitors.
- List common complaints users have about existing solutions.
- Identify underserved needs (gaps in the market).
- Do NOT fabricate competitors. Only report what you find in the data.
- If the idea targets a niche or novel space and only 1-2 competitors exist, \
  that's a valid finding — it means the market is underserved. Do NOT pad the \
  list with irrelevant companies to hit a number.
- If zero competitors exist, report that honestly. An empty landscape is signal.
- However, if the idea targets a WELL-KNOWN category (CRM, email marketing, \
  project management, note-taking, etc.), there are definitely 5+ competitors. \
  If you've only found 2-3 in a known category, you haven't searched broadly \
  enough — try "[category] alternatives", "[category] top tools", or check \
  G2/Capterra category pages before submitting.

When you have mapped the landscape, call submit_result with your structured \
findings. Quality matters — each competitor should have strengths, weaknesses, \
and ideally pricing."""

TOOL_NAMES = [
    "search_web",
    "search_g2",
    "search_capterra",
    "search_producthunt",
    "search_indiehackers",
    "search_crunchbase",
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
