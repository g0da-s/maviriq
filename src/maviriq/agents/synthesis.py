from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field, field_validator

from maviriq.agents.base import BaseAgent
from maviriq.models.schemas import (
    SynthesisInput,
    SynthesisOutput,
    Verdict,
    ViabilitySignal,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Intermediate schemas (internal to this module)
# ──────────────────────────────────────────────

class _ViabilityAnalysis(BaseModel):
    """Pass 1: Focused quantitative viability analysis."""

    people_pay: bool
    people_pay_reasoning: str
    reachability: Literal["easy", "moderate", "hard"]
    reachability_reasoning: str
    market_gap: str
    gap_size: Literal["large", "medium", "small", "none"]
    signals: list[ViabilitySignal]
    estimated_market_size: str

    @field_validator("reachability", mode="before")
    @classmethod
    def normalize_reachability(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("easy", "moderate", "hard"):
            return v_lower
        if "easy" in v_lower:
            return "easy"
        if "hard" in v_lower:
            return "hard"
        return "moderate"

    @field_validator("gap_size", mode="before")
    @classmethod
    def normalize_gap_size(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v_lower = v.lower().strip()
        if v_lower in ("large", "medium", "small", "none"):
            return v_lower
        if "large" in v_lower:
            return "large"
        if "small" in v_lower:
            return "small"
        if "none" in v_lower:
            return "none"
        return "medium"


class _VerdictStrategy(BaseModel):
    """Pass 2: Verdict, narrative, and strategy synthesis."""

    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    one_line_summary: str
    reasoning: str
    key_strengths: list[str]
    key_risks: list[str]
    recommended_mvp: str | None = None
    recommended_positioning: str | None = None
    target_user_summary: str
    next_steps: list[str]
    differentiation_strategy: str | None = None
    previous_attempts_summary: str | None = None
    lessons_from_failures: str | None = None

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, v: str) -> str:
        if isinstance(v, str) and v.upper().strip() == "CONDITIONAL":
            return "MAYBE"
        return v


# ──────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────

_VIABILITY_PROMPT = """\
You are a market viability analyst. Your job is to assess the commercial viability \
of a business idea based on research data.

Focus ONLY on these questions — be precise and cite the data:

1. **Do people pay for this?** (bool + reasoning)
   - Look at competitor pricing data. Are there paying customers?
   - Is there evidence of willingness to pay from pain research?
   - Reasoning: 1-2 sentences max. These display in small metric cards.

2. **Can we reach the target users?** ("easy" / "moderate" / "hard" + reasoning)
   - Where do these users spend time online?
   - Are there clear distribution channels?
   - Reasoning: 1-2 sentences max. These display in small metric cards.

3. **What's the market gap?** (description + size: "large" / "medium" / "small" / "none")
   - What do existing solutions miss?
   - How significant is the unmet need?

4. **Viability signals** (list of observations)
   - Each signal has: description, direction (positive/negative/neutral), confidence (0.0-1.0), source
   - Include signals from ALL research dimensions: pain, competition, market, failures
   - Be specific — "users complain about X on Reddit" not "there is demand"

5. **Estimated market size** (rough order of magnitude)
   - Narrow to the specific niche, not the broad category
   - Show your reasoning if the data supports it

Bias toward skepticism. If data is weak or contradictory, say so explicitly.
Do NOT provide a verdict — that comes in the next step."""

_VERDICT_PROMPT = """\
You are a product strategist delivering a final BUILD/SKIP/MAYBE verdict on a business idea.

A viability analysis has already been completed (see below). Your job is to synthesize \
ALL the research AND the viability analysis into a clear verdict and actionable strategy.

**Verdict rules:**
- BUILD: Strong pain + viable market + reachable users + meaningful gap
- SKIP: Weak pain OR saturated market OR unreachable users OR no gap
- MAYBE: Viable BUT only under specific conditions (specify what those are)

IMPORTANT — Be evidence-driven, not encouraging:
- Let the data decide. Don't inflate weak ideas, but don't artificially suppress strong ones either.
- If prior startups failed at this exact idea, you need a CLEAR reason why this time would be different to justify BUILD.
- Your job is an HONEST assessment — not a pitch deck, not a death sentence.

**Confidence calibration (be precise, avoid clustering around 0.55-0.65):**
- 0.85+: BUILD — overwhelming evidence across all dimensions
- 0.65-0.84: MAYBE leaning BUILD — strong signals but 1-2 real concerns
- 0.45-0.64: MAYBE leaning SKIP — some positive signals but significant gaps or risks
- 0.25-0.44: SKIP — weak pain, crowded market, or hard to reach users
- Below 0.25: SKIP — no evidence of pain, no gap, or major red flags
The confidence score should MATCH the verdict. A BUILD below 0.65 or a SKIP above 0.65 needs explicit justification in your reasoning.
Think carefully about where THIS SPECIFIC idea falls. Different ideas should get meaningfully different scores.

**What to provide:**
- Verdict + confidence (0.0-1.0, calibrated per the scale above)
- One-line summary: explain WHY you gave this verdict, do NOT restate the idea. \
  Max 20 words. Focus on the key insight (e.g. "Strong pain but saturated market with \
  entrenched players makes differentiation difficult")
- Reasoning (3-5 paragraphs, cite the data AND the viability analysis)
- Key strengths (why BUILD) — be specific but concise. Lead with the insight, then \
  briefly cite evidence. Don't repeat info already in the metric cards above.
- Key risks (why SKIP or be cautious) — same: concise, insight-first, no redundancy.
- If BUILD: recommended MVP (what to build first)
- If BUILD: positioning (how to differentiate from competitors)
- Target user summary (who exactly are you building for)
- Next steps — each must include a specific action, a channel/method, and a concrete \
  metric or milestone. Not generic advice.
- Differentiation strategy: what SPECIFIC angle should this product take?
- Previous attempts summary: what was tried before and what happened?
- Lessons from failures: what must the founder do differently?

Use the viability analysis as established facts. Do NOT contradict its findings — build on them.
Be critical. Don't oversell weak ideas. This is NOT a pitch deck — it's an honest assessment."""


# ──────────────────────────────────────────────
# Agent
# ──────────────────────────────────────────────

class SynthesisAgent(BaseAgent[SynthesisInput, SynthesisOutput]):
    name = "Synthesis & Verdict"
    description = "Combines all research and delivers a BUILD/SKIP/MAYBE verdict"
    output_schema = SynthesisOutput

    # Synthesis doesn't use tools — these are stubs to satisfy the ABC.
    def get_system_prompt(self, input_data: SynthesisInput) -> str:
        return _VERDICT_PROMPT

    def get_user_prompt(self, input_data: SynthesisInput) -> str:
        return ""

    def get_tools(self) -> list[dict[str, Any]]:
        return []

    def get_tool_executors(self) -> dict[str, Callable[[str], Awaitable[str]]]:
        return {}

    async def run(self, input_data: SynthesisInput) -> SynthesisOutput:
        context = self._build_research_context(input_data)

        # Pass 1: Viability Analysis
        viability = await self.llm.generate_structured(
            system_prompt=_VIABILITY_PROMPT,
            user_prompt=context,
            output_schema=_ViabilityAnalysis,
            use_research_model=True,
        )

        # Pass 2: Verdict & Strategy (receives research + viability results)
        verdict_context = context + self._format_viability_results(viability)
        verdict = await self.llm.generate_structured(
            system_prompt=_VERDICT_PROMPT,
            user_prompt=verdict_context,
            output_schema=_VerdictStrategy,
            use_research_model=True,
        )

        # Merge into final SynthesisOutput
        return SynthesisOutput(
            # From Pass 1
            people_pay=viability.people_pay,
            people_pay_reasoning=viability.people_pay_reasoning,
            reachability=viability.reachability,
            reachability_reasoning=viability.reachability_reasoning,
            market_gap=viability.market_gap,
            gap_size=viability.gap_size,
            signals=viability.signals,
            estimated_market_size=viability.estimated_market_size,
            # From Pass 2
            verdict=verdict.verdict,
            confidence=verdict.confidence,
            one_line_summary=verdict.one_line_summary,
            reasoning=verdict.reasoning,
            key_strengths=verdict.key_strengths,
            key_risks=verdict.key_risks,
            recommended_mvp=verdict.recommended_mvp,
            recommended_positioning=verdict.recommended_positioning,
            target_user_summary=verdict.target_user_summary,
            next_steps=verdict.next_steps,
            differentiation_strategy=verdict.differentiation_strategy,
            previous_attempts_summary=verdict.previous_attempts_summary,
            lessons_from_failures=verdict.lessons_from_failures,
        )

    def _build_research_context(self, input_data: SynthesisInput) -> str:
        """Build the full research context string from all agent outputs."""
        idea = input_data.idea
        pain = input_data.pain_discovery
        competitors = input_data.competitor_research
        market_intel = input_data.market_intelligence
        graveyard = input_data.graveyard_research

        avg_severity = (
            f"{sum(p.pain_severity for p in pain.pain_points) / len(pain.pain_points):.1f}/5"
            if pain.pain_points else "N/A"
        )

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
{chr(10).join(f'{i+1}. {c.name} [{c.competitor_type}]: {c.one_liner}' + chr(10) + f'   Pricing: {", ".join(p.price for p in c.pricing)}' + chr(10) + f'   Strengths: {", ".join(c.strengths[:2])}' + chr(10) + f'   Weaknesses: {", ".join(c.weaknesses[:2])}' for i, c in enumerate(competitors.competitors[:5])) or "None found"}

Common complaints:
{chr(10).join(f'- {c}' for c in competitors.common_complaints) or "None found"}

Underserved needs:
{chr(10).join(f'- {n}' for n in competitors.underserved_needs) or "None found"}
"""

        if market_intel:
            context += f"""
═══ MARKET INTELLIGENCE ═══
Market size estimate: {market_intel.market_size_estimate}
Growth direction: {market_intel.growth_direction}
TAM reasoning: {market_intel.tam_reasoning}

Distribution channels:
{chr(10).join(f'- {ch.channel} (reach: {ch.reach_estimate}, effort: {ch.effort})' for ch in market_intel.distribution_channels) or "None found"}

Funding signals:
{chr(10).join(f'- {sig}' for sig in market_intel.funding_signals) or "None found"}
"""

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

"""

        return context

    def _format_viability_results(self, viability: _ViabilityAnalysis) -> str:
        """Format Pass 1 viability results as context for Pass 2."""
        signals_text = "\n".join(
            f"- [{sig.direction.upper()}] {sig.signal} "
            f"(confidence: {sig.confidence:.2f}, source: {sig.source})"
            for sig in viability.signals
        ) or "None"

        return f"""

═══ VIABILITY ANALYSIS (completed) ═══
People pay: {"Yes" if viability.people_pay else "No"}
Reasoning: {viability.people_pay_reasoning}

Reachability: {viability.reachability}
Reasoning: {viability.reachability_reasoning}

Market gap: {viability.market_gap}
Gap size: {viability.gap_size}

Estimated market size: {viability.estimated_market_size}

Viability signals:
{signals_text}
"""
