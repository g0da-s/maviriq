import logging

from maviriq.agents.base import BaseAgent
from maviriq.models.schemas import (
    SynthesisInput,
    SynthesisOutput,
)

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """\
You are a product strategist delivering a final BUILD/SKIP/MAYBE verdict on a business idea.

You have access to:
- Pain research (who suffers, how much, evidence)
- Competitive analysis (what exists, gaps, pricing)
- Market intelligence (market size, distribution channels, monetization signals)
- Graveyard research (failed startups, warning signs, lessons from failures)

Your job: Synthesize ALL of this into a clear verdict.

**Verdict rules:**
- BUILD: Strong pain + viable market + reachable users + meaningful gap
- SKIP: Weak pain OR saturated market OR unreachable users OR no gap
- MAYBE: Viable BUT only under specific conditions (specify what those are)

IMPORTANT — Bias toward skepticism:
- Most ideas should get SKIP or MAYBE. BUILD requires STRONG evidence across ALL dimensions.
- If prior startups failed at this exact idea, you need a CLEAR reason why this time is different.
- Your job is to SAVE the founder from wasting 6 months. Be honest, not encouraging.

**Confidence calibration (be precise, avoid defaulting to 0.60-0.65):**
- 0.90+: Overwhelming evidence — strong pain, clear gap, easy reach, proven willingness to pay
- 0.75-0.89: Strong evidence with minor concerns — most signals positive, 1-2 risks
- 0.55-0.74: Mixed evidence — some positive signals but real concerns or data gaps
- 0.35-0.54: Weak case — limited pain evidence, crowded market, or hard to reach users
- Below 0.35: Very weak — insufficient data, no clear pain, or major red flags
Think carefully about where THIS SPECIFIC idea falls. Different ideas should get meaningfully different scores.

**What to include:**
- Verdict + confidence (0.0-1.0, calibrated per the scale above)
- One-line summary: explain WHY you gave this verdict, do NOT restate the idea. Focus on the key insight (e.g. "Strong pain but saturated market with entrenched players makes differentiation difficult")
- Reasoning (3-5 paragraphs, cite the data)
- Key strengths (why BUILD)
- Key risks (why SKIP or be cautious)
- If BUILD: recommended MVP (what to build first)
- If BUILD: positioning (how to differentiate from competitors)
- Target user summary (who exactly are you building for)
- Estimated market size (rough order of magnitude based on data)
- Next steps (actionable items for the founder)

You MUST also answer these viability questions:
1. Do people pay for this? (bool + reasoning, based on competitor pricing and monetization signals)
2. Can we reach the target users? ("easy"/"moderate"/"hard" + reasoning)
3. What's the market gap? (description + size: "large"/"medium"/"small"/"none")
4. Viability signals: observations with direction (positive/negative/neutral) and confidence
5. Risk factors: specific things that could kill this idea
6. Opportunity score: 0.0-1.0 holistic assessment

Additionally provide:
- Differentiation strategy: what SPECIFIC angle should this product take?
- Previous attempts summary: what was tried before and what happened?
- Lessons from failures: what must the founder do differently?

Be critical. Don't oversell weak ideas. This is NOT a pitch deck — it's an honest assessment.
If the data is insufficient or contradictory, lower your confidence and say so."""


class SynthesisAgent(BaseAgent[SynthesisInput, SynthesisOutput]):
    name = "Synthesis & Verdict"
    description = "Combines all research and delivers a BUILD/SKIP/MAYBE verdict"

    async def run(self, input_data: SynthesisInput) -> SynthesisOutput:
        idea = input_data.idea
        pain = input_data.pain_discovery
        competitors = input_data.competitor_research
        market_intel = input_data.market_intelligence
        graveyard = input_data.graveyard_research

        avg_severity = (
            f"{sum(p.pain_severity for p in pain.pain_points) / len(pain.pain_points):.1f}/5"
            if pain.pain_points else "N/A"
        )

        # Build the full context
        context = f"""
IDEA: {idea}

═══ PAIN RESEARCH ═══
Target user: {pain.primary_target_user.label}
{len(pain.pain_points)} pain points found (avg severity: {avg_severity})
Pain summary: {pain.pain_summary}

Top pain points:
{chr(10).join(f'{i+1}. "{p.quote}" - {p.author_context} (severity: {p.pain_severity}/5, source: {p.source})' for i, p in enumerate(pain.pain_points[:5])) or "None found"}

User segments found:
{chr(10).join(f'- {s.label} ({s.frequency} mentions, willingness to pay: {s.willingness_to_pay})' for s in pain.user_segments) or "None found"}

═══ COMPETITIVE LANDSCAPE ═══
{len(competitors.competitors)} competitors
Market saturation: {competitors.market_saturation}
Avg price: {competitors.avg_price_point}

Top competitors:
{chr(10).join(f'{i+1}. {c.name}: {c.one_liner}' + chr(10) + f'   Pricing: {", ".join(p.price for p in c.pricing)}' + chr(10) + f'   Strengths: {", ".join(c.strengths[:2])}' + chr(10) + f'   Weaknesses: {", ".join(c.weaknesses[:2])}' for i, c in enumerate(competitors.competitors[:5])) or "None found"}

Common complaints:
{chr(10).join(f'- {c}' for c in competitors.common_complaints) or "None found"}

Underserved needs:
{chr(10).join(f'- {n}' for n in competitors.underserved_needs) or "None found"}
"""

        # Conditionally add market intelligence context
        if market_intel:
            context += f"""
═══ MARKET INTELLIGENCE ═══
Market size estimate: {market_intel.market_size_estimate}
Growth direction: {market_intel.growth_direction}
TAM reasoning: {market_intel.tam_reasoning}

Distribution channels:
{chr(10).join(f'- {ch.channel} (reach: {ch.reach_estimate}, effort: {ch.effort})' for ch in market_intel.distribution_channels) or "None found"}

Monetization signals:
{chr(10).join(f'- [{sig.strength.upper()}] {sig.signal} (source: {sig.source})' for sig in market_intel.monetization_signals) or "None found"}
"""

        # Conditionally add graveyard research context
        if graveyard:
            context += f"""
═══ GRAVEYARD RESEARCH ═══
Previous attempts:
{chr(10).join(f'- {a.name}: {a.what_they_did} → Shut down because: {a.shutdown_reason} ({a.year or "unknown year"})' for a in graveyard.previous_attempts) or "No previous attempts found"}

Common failure reasons:
{chr(10).join(f'- {r}' for r in graveyard.failure_reasons) or "None identified"}

Lessons learned: {graveyard.lessons_learned}

Churn signals:
{chr(10).join(f'- [{sig.severity.upper()}] {sig.signal} (source: {sig.source})' for sig in graveyard.churn_signals) or "None found"}

Competitor health signals:
{chr(10).join(f'- {sig.company}: [{sig.direction.upper()}] {sig.signal} (source: {sig.source})' for sig in graveyard.competitor_health_signals) or "None found"}
"""

        result = await self.llm.generate_structured(
            system_prompt=SYNTHESIS_PROMPT,
            user_prompt=context,
            output_schema=SynthesisOutput,
        )

        return result
