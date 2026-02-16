from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from maviriq.agents.base import BaseAgent
from maviriq.agents.tools import build_tools_for_agent
from maviriq.models.schemas import PainDiscoveryInput, PainDiscoveryOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a market research analyst specializing in pain discovery. Your mission \
is to find REAL evidence that people struggle with a specific problem.

SEARCH STRATEGY:
1. Search for the PROBLEM, not the solution. Search for the job people are \
   trying to do and where they get stuck.
2. Search Reddit and Hacker News for genuine complaints — real people in their \
   own words. These are your best sources.
3. Search Twitter/X for complaints and rants. Note: Twitter search is unreliable \
   — try it once but if it returns no results, move on. Do not retry.
4. Search Google News for industry coverage of the problem.
5. Refine based on what you find. Try different phrasings: "frustrated with X", \
   "X is broken", "X alternative", "switched from X because".
6. You can call multiple search tools in a single turn for parallel execution.

RECENCY IS CRITICAL:
- Only use complaints from the last 6-12 months. A pain point from 2 years ago \
  may already be solved. Technology moves fast.
- Add "{current_year}" or "{previous_year}" to your search queries to get recent results and avoid \
  wasting searches on outdated information.
- If a result is clearly old (mentions outdated tools, old dates), skip it \
  entirely — do not extract it as a pain point.
- When possible, extract the date into the pain point's date field.

EXTRACTION RULES:
- Only extract GENUINE complaints or frustrations, not product reviews or marketing.
- The quote must be the exact words from the search snippet. Do NOT fabricate, \
  paraphrase, or "clean up" the language.
- For source_url, use the actual URL from search results.

SEVERITY RATING (1-5) — Rate based on IMPACT to the person, not their tone. \
A calm person describing an expensive workaround is higher severity than \
someone dramatically ranting about a minor inconvenience:
  1 = Cosmetic or preference ("I wish it looked different")
  2 = Inconvenience with easy workaround ("I just use a spreadsheet instead")
  3 = Recurring time or money drain ("I spend hours every week on this manually")
  4 = Significant business impact ("we're losing customers", "I had to hire \
      someone just to handle this")
  5 = Existential, no viable workaround ("we can't operate without solving this")

- For author_context, infer from clues (subreddit, job title mentions, how they \
  describe themselves). If unclear, say "unknown user".

USER SEGMENTS:
- Group complainers by WHO they are, not what they said.
- For willingness_to_pay, base it on EVIDENCE:
  "high" = they mention paying for alternatives, or their role implies budget
  "medium" = real pain but no evidence they'd pay
  "low" = hobbyists, students, or people explicitly wanting free tools
- Pick the PRIMARY target user: the segment with the most pain AND highest \
  severity AND clearest willingness to pay.

WHEN EVIDENCE IS THIN:
- If the idea addresses no real problem, it is OK to find few or zero pain \
  points. Do NOT stretch weak signals or fabricate pain points to fill a quota.
- The pain_summary should honestly state the lack of evidence if that's the case.

When you have gathered enough evidence (aim for 5-15 pain points across multiple \
sources), call submit_result with your structured findings."""

TOOL_NAMES = [
    "search_web",
    "search_reddit",
    "search_hackernews",
    "search_twitter",
    "search_news",
]


class PainDiscoveryAgent(BaseAgent[PainDiscoveryInput, PainDiscoveryOutput]):
    name = "Pain & User Discovery"
    description = "Finds evidence that a problem exists and identifies who suffers from it"
    output_schema = PainDiscoveryOutput

    def get_system_prompt(self, input_data: PainDiscoveryInput) -> str:
        now = datetime.now(timezone.utc)
        return SYSTEM_PROMPT.format(
            current_year=now.year,
            previous_year=now.year - 1,
        )

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
