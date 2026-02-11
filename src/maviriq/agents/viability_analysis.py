import logging

from maviriq.agents.base import BaseAgent
from maviriq.models.schemas import (
    ViabilityInput,
    ViabilityOutput,
)

logger = logging.getLogger(__name__)

VIABILITY_PROMPT = """\
You are a startup advisor analyzing whether an idea is viable. Answer three critical questions:

1. **Do people pay for this?**
   - Look at competitor pricing data
   - Check if users are complaining about existing paid tools (proves willingness to pay)
   - If competitors have users/reviews, people DO pay
   - Verdict: true/false + reasoning

2. **Can we reach the target users?**
   - Where do they hang out? (subreddits, forums, communities you saw in the data)
   - How engaged are those communities?
   - Difficulty: "easy" (active online communities), "moderate" (scattered), "hard" (offline/gatekept)
   - Reasoning

3. **What's the market gap?**
   - What do ALL competitors struggle with (common complaints)?
   - What do users wish existed?
   - Is this gap large, medium, small, or nonexistent?
   - Description of the gap

Also provide:
- Viability signals (observations from the data + direction: positive/negative)
- Risk factors (things that could kill this idea)
- Opportunity score (0.0-1.0, holistic assessment)

Base everything on the actual data provided. No speculation."""


class ViabilityAnalysisAgent(BaseAgent[ViabilityInput, ViabilityOutput]):
    name = "Viability Analysis"
    description = "Analyzes willingness to pay, reachability, and market gaps"

    async def run(self, input_data: ViabilityInput) -> ViabilityOutput:
        idea = input_data.idea
        pain = input_data.pain_discovery
        competitors = input_data.competitor_research

        avg_severity = (
            f"{sum(p.pain_severity for p in pain.pain_points) / len(pain.pain_points):.1f}/5"
            if pain.pain_points else "N/A (no pain points found)"
        )
        sources = ", ".join(set(p.source for p in pain.pain_points)) if pain.pain_points else "none"

        # Build a comprehensive context from prior agents
        context = f"""
IDEA: {idea}

TARGET USER:
{pain.primary_target_user.label} - {pain.primary_target_user.description}
Willingness to pay: {pain.primary_target_user.willingness_to_pay}

PAIN EVIDENCE:
{len(pain.pain_points)} pain points found across {sources}
Average severity: {avg_severity}
Pain summary: {pain.pain_summary}

Sample complaints:
{chr(10).join(f'- "{p.quote}" ({p.source})' for p in pain.pain_points[:5]) or "None found"}

COMPETITIVE LANDSCAPE:
{len(competitors.competitors)} competitors found
Market saturation: {competitors.market_saturation}
Average price: {competitors.avg_price_point}

Competitors:
{chr(10).join(f'- {c.name}: {c.one_liner} (Pricing: {", ".join(p.price for p in c.pricing[:2])})' for c in competitors.competitors[:5]) or "None found"}

Common complaints:
{chr(10).join(f'- {c}' for c in competitors.common_complaints) or "None found"}

Underserved needs:
{chr(10).join(f'- {n}' for n in competitors.underserved_needs) or "None found"}
"""

        result = await self.llm.generate_structured(
            system_prompt=VIABILITY_PROMPT,
            user_prompt=context,
            output_schema=ViabilityOutput,
        )

        return result
