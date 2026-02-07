import logging

from maverick.agents.base import BaseAgent
from maverick.models.schemas import (
    SynthesisInput,
    SynthesisOutput,
)

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """\
You are a product strategist delivering a final BUILD/SKIP/CONDITIONAL verdict on a business idea.

You have access to:
- Pain research (who suffers, how much, evidence)
- Competitive analysis (what exists, gaps, pricing)
- Viability assessment (do people pay, can we reach them, what's the opportunity)

Your job: Synthesize ALL of this into a clear verdict.

**Verdict rules:**
- BUILD: Strong pain + viable market + reachable users + meaningful gap
- SKIP: Weak pain OR saturated market OR unreachable users OR no gap
- CONDITIONAL: Viable BUT only under specific conditions (specify what those are)

**What to include:**
- Verdict + confidence (0.0-1.0, be honest)
- One-line summary (what is this, why does it matter)
- Reasoning (3-5 paragraphs, cite the data)
- Key strengths (why BUILD)
- Key risks (why SKIP or be cautious)
- If BUILD: recommended MVP (what to build first)
- If BUILD: positioning (how to differentiate from competitors)
- Target user summary (who exactly are you building for)
- Estimated market size (rough order of magnitude based on data)
- Next steps (actionable items for the founder)

Be critical. Don't oversell weak ideas. This is NOT a pitch deck — it's an honest assessment.
If the data is insufficient or contradictory, lower your confidence and say so."""


class SynthesisAgent(BaseAgent[SynthesisInput, SynthesisOutput]):
    name = "Synthesis & Verdict"
    description = "Combines all research and delivers a BUILD/SKIP/CONDITIONAL verdict"

    async def run(self, input_data: SynthesisInput) -> SynthesisOutput:
        idea = input_data.idea
        pain = input_data.pain_discovery
        competitors = input_data.competitor_research
        viability = input_data.viability

        # Build the full context
        context = f"""
IDEA: {idea}

═══ PAIN RESEARCH ═══
Target user: {pain.primary_target_user.label}
{len(pain.pain_points)} pain points found (avg severity: {sum(p.pain_severity for p in pain.pain_points) / len(pain.pain_points):.1f}/5)
Pain summary: {pain.pain_summary}

Top pain points:
{chr(10).join(f'{i+1}. "{p.quote}" - {p.author_context} (severity: {p.pain_severity}/5, source: {p.source})' for i, p in enumerate(pain.pain_points[:5]))}

User segments found:
{chr(10).join(f'- {s.label} ({s.frequency} mentions, willingness to pay: {s.willingness_to_pay})' for s in pain.user_segments)}

═══ COMPETITIVE LANDSCAPE ═══
{len(competitors.competitors)} competitors
Market saturation: {competitors.market_saturation}
Avg price: {competitors.avg_price_point}

Top competitors:
{chr(10).join(f'{i+1}. {c.name}: {c.one_liner}' + chr(10) + f'   Pricing: {", ".join(p.price for p in c.pricing)}' + chr(10) + f'   Strengths: {", ".join(c.strengths[:2])}' + chr(10) + f'   Weaknesses: {", ".join(c.weaknesses[:2])}' for i, c in enumerate(competitors.competitors[:5]))}

Common complaints:
{chr(10).join(f'- {c}' for c in competitors.common_complaints)}

Underserved needs:
{chr(10).join(f'- {n}' for n in competitors.underserved_needs)}

═══ VIABILITY ANALYSIS ═══
People pay: {viability.people_pay} - {viability.people_pay_reasoning}
Reachability: {viability.reachability} - {viability.reachability_reasoning}
Market gap: {viability.gap_size} - {viability.market_gap}
Opportunity score: {viability.opportunity_score:.0%}

Key signals:
{chr(10).join(f'- [{s.direction.upper()}] {s.signal} (confidence: {s.confidence:.0%})' for s in viability.signals[:5])}

Risk factors:
{chr(10).join(f'- {r}' for r in viability.risk_factors)}
"""

        result = await self.llm.generate_structured(
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=context,
            output_schema=SynthesisOutput,
        )

        return result
