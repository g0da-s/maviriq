from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, field_validator

from maviriq.agents.base import BaseAgent, ToolExecutors, ToolSchemas
from maviriq.models.schemas import (
    SynthesisInput,
    SynthesisOutput,
    Verdict,
    ViabilitySignal,
    _normalize_literal,
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
    def normalize_reachability(cls, v: object) -> object:
        return _normalize_literal(v, ("easy", "moderate", "hard"), "moderate")

    @field_validator("gap_size", mode="before")
    @classmethod
    def normalize_gap_size(cls, v: object) -> object:
        return _normalize_literal(v, ("large", "medium", "small", "none"), "medium")


class _VerdictStrategy(BaseModel):
    """Pass 2: Verdict, narrative, and strategy synthesis."""

    verdict: Verdict
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
    def normalize_verdict(cls, v: object) -> object:
        if isinstance(v, str) and v.upper().strip() == "CONDITIONAL":
            return "MAYBE"
        return v

    @field_validator("key_strengths", "key_risks", "next_steps", mode="before")
    @classmethod
    def coerce_str_to_list(cls, v: object) -> object:
        """LLMs sometimes return a bullet-point string instead of a list."""
        if isinstance(v, str):
            lines = [ln.lstrip("-•* ").strip() for ln in v.strip().splitlines()]
            return [ln for ln in lines if ln]
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

TONE & LENGTH:
- Write like a sharp founder talking to another founder. No corporate speak, no filler.
- people_pay_reasoning: 1-2 sentences max. These display in small metric cards. \
  GOOD: "3 competitors charge $20-50/mo with paying customers. Pain is real and funded." \
  BAD: "Based on the competitor analysis, there appears to be evidence suggesting willingness to pay."
- reachability_reasoning: 1-2 sentences max. Same metric card format. \
  GOOD: "Target users live on r/devops and HN. ProductHunt launch = instant visibility." \
  BAD: "Distribution channels exist through various online communities and platforms."
- market_gap: 2-3 sentences. What's missing and why it matters.
- Each signal: 1 sentence, specific. "Devs on r/golang complain about slow CI — 12 threads in 6 months" \
  not "there is demand for faster tools."

<example>
GOOD viability analysis (for "AI code review for Python security"):
- people_pay: true
- people_pay_reasoning: "CodeRabbit charges $19/seat/mo, Snyk has enterprise pricing. Devs already pay for code security."
- reachability: "easy"
- reachability_reasoning: "VS Code marketplace + GitHub Actions = built-in distribution. Python devs are on r/python (1.5M members)."
- market_gap: "Existing tools flag issues but don't auto-fix. Python-specific security context is weak across all players."
- gap_size: "medium"
- signals: [positive] "8 pain points about AI-generated code security on HN" / [negative] "CodeRabbit has 2yr head start with deep GitHub integration"
</example>

Be evidence-driven, not pessimistic or optimistic. If the data is strong, say so. \
If the data is weak, say so. Don't inflate weak signals, but don't deflate strong ones either. \
Your job is accurate assessment — let the data speak.
Do NOT provide a verdict — that comes in the next step."""

_VERDICT_PROMPT = """\
You are a product strategist delivering a final BUILD/SKIP/MAYBE verdict on a business idea.

A viability analysis has already been completed (see below). Your job is to synthesize \
ALL the research AND the viability analysis into a clear verdict and actionable strategy.

**Verdict rules:**
- BUILD: Strong pain + viable market + reachable users + meaningful gap
- SKIP: Weak pain OR saturated market OR unreachable users OR no gap
- MAYBE: Viable BUT only under specific conditions (specify what those are)

IMPORTANT — Be evidence-driven, not encouraging AND not artificially pessimistic:
- Let the data decide. Don't inflate weak ideas, but don't deflate strong ones either.
- If prior startups failed at this exact idea, you need a CLEAR reason why this time would be different to justify BUILD.
- Competition VALIDATES demand — finding competitors is positive signal, not automatic SKIP. \
  Saturated markets with entrenched players warrant caution, but "competitors exist" alone \
  is not a reason to SKIP.
- If the research found 5+ real pain points with high-impact severity, funded competitors \
  with paying customers, and a growing market, that is strong BUILD evidence. Don't SKIP \
  just because risks exist — every real business has risks.
- Your job is an HONEST assessment — not a pitch deck, not a death sentence.

**Verdict calibration — use the evidence, not your gut:**
- BUILD means you would tell a friend to quit their job for this. Pain is screaming, \
  people are paying competitors, the gap is real, and users are reachable.
- SKIP means you would tell a friend to save their time. Pain is weak or fabricated, \
  the market is locked down by incumbents, or there is no viable path to users.
- MAYBE means the signal is mixed — some dimensions are strong but others have real holes. \
  Always specify WHAT would need to be true to flip this to BUILD.

VERDICT CALIBRATION EXAMPLES:
- "AI code review tool" with 8 high-severity pain points, 4 funded competitors, $500M market → BUILD
- "Social network for pets" with 0 pain points, failed predecessors, no monetization path → SKIP
- "On-demand barber app" with moderate pain, 1 failed predecessor, real but risky market → MAYBE
- "Generic CRM for small businesses" with pain but Salesforce/HubSpot dominate → SKIP
- "API docs from code" with strong developer pain, 2-3 competitors, growing market → BUILD

The confidence score is computed separately from your verdict. \
Focus on getting the verdict and reasoning right — be honest about what the data says.

TONE — write like a sharp founder advising another founder:
- No corporate speak, no filler, no hedging with "it appears that" or "based on the analysis."
- Be direct and conversational. Imagine you're at a coffee shop telling a friend whether \
  their idea is worth quitting their job for.
- GOOD: "Devs are screaming about this on HN. 3 competitors exist but they all suck at Python. Ship it."
- BAD: "The analysis suggests that there is a meaningful market opportunity with several positive indicators."

**What to provide (with length guidance):**
- Verdict (BUILD / SKIP / MAYBE)
- one_line_summary: 1 sentence, max 20 words. Explain WHY this verdict, don't restate the idea. \
  GOOD: "Strong pain but saturated market with entrenched players makes differentiation difficult" \
  BAD: "An AI code review tool for Python security vulnerabilities"
- reasoning: 3-4 short paragraphs. Cite the data. Write in plain language a founder can skim \
  in 30 seconds. No walls of text.
- key_strengths (3-5 items) — YC partner notecard style. \
  Max 15 words each. Blunt, punchy, no source citations, no parenthetical references. \
  Don't repeat what the metric cards already show (pain severity, competition level, etc.). \
  Focus on WHY a founder should be excited. \
  GOOD: "Devs already mass-adopting AI code — this problem grows itself" \
  GOOD: "Competitors charge $30+/mo — room for a freemium wedge" \
  GOOD: "No incumbent owns the workflow — land-grab opportunity" \
  BAD: "Strong pain: AI-generated code introduces security vulnerabilities (Google News, severity 4/5)" \
  BAD: "Willingness to pay: Established competitors with paid subscription models demonstrate customers are willing to pay"
- key_risks (3-5 items) — same YC notecard style. Max 15 words. \
  Specific and sharp, not generic warnings. Name the competitor, name the failure mode. \
  GOOD: "CodeRabbit has 2yr head start and deep GitHub integration" \
  GOOD: "Devs hate false positives — one bad week and they uninstall" \
  BAD: "Market saturation: Several competitors already exist, including CodeRabbit, CodiumAI, and SonarQube"
- recommended_mvp: 2-3 sentences if BUILD. What to build first, what to skip. \
  GOOD: "VS Code extension that scans Python files on save. Flag top 5 OWASP issues only — no noise. Ship in 2 weeks." \
  BAD: "Develop a comprehensive code analysis platform with multi-language support and CI/CD integration."
- recommended_positioning: 1-2 sentences if BUILD. How to stand out. \
  GOOD: "The Python-only security tool that actually understands your codebase context." \
  BAD: "Position as a differentiated AI-powered code review solution."
- target_user_summary: 1-2 sentences. Who exactly, in plain language. \
  GOOD: "Senior Python devs at startups (10-50 people) shipping fast and worried about security debt." \
  BAD: "Software developers and engineering teams who require code security solutions."
- next_steps: 3-5 items. Each must include a specific action + channel + concrete metric. \
  <example>
  GOOD next steps:
  - "Post on r/Python asking 'how do you handle security reviews?' — aim for 20+ responses in 1 week"
  - "Build a VS Code extension MVP that flags OWASP Top 5 in Python — ship to 10 beta users in 2 weeks"
  - "DM 5 CTOs from YC W24 batch who mentioned security pain — get 3 discovery calls booked"
  BAD next steps:
  - "Conduct customer discovery interviews"
  - "Build an MVP"
  - "Validate the market"
  </example>
- differentiation_strategy: 2-3 sentences. What SPECIFIC angle should this product take?
- previous_attempts_summary: 1-2 sentences. What was tried before and what happened? \
  Skip if no previous attempts found.
- lessons_from_failures: 1-2 sentences. What must the founder do differently? \
  Skip if no failures found.

Use the viability analysis as established facts. Do NOT contradict its findings — build on them.
Be direct. Don't oversell weak ideas. This is NOT a pitch deck — it's an honest assessment \
from one founder to another."""


# ──────────────────────────────────────────────
# Deterministic confidence scoring
# ──────────────────────────────────────────────


def _compute_confidence(
    viability: _ViabilityAnalysis,
    input_data: SynthesisInput,
) -> float:
    """Compute confidence from structured research data — no LLM involved.

    Scores 6 dimensions from categorical/countable data already extracted
    by the research agents and Pass 1 viability analysis.  Returns a
    weighted average clamped to [0.05, 0.95].
    """
    pain = input_data.pain_discovery
    comp = input_data.competitor_research
    market = input_data.market_intelligence
    graveyard = input_data.graveyard_research

    # {dimension: (score, weight)}
    scores: dict[str, tuple[float, float]] = {}

    # 1. Pain evidence (weight 0.25) — count + severity of pain points
    high = sum(1 for p in pain.pain_points if p.pain_severity == "high")
    mod = sum(1 for p in pain.pain_points if p.pain_severity == "moderate")
    total = len(pain.pain_points)
    if total == 0:
        pain_score = 0.1
    else:
        pain_score = min(1.0, (high * 1.0 + mod * 0.5) / 5.0)
        pain_score = min(1.0, pain_score + (total / 20.0) * 0.2)
    scores["pain"] = (pain_score, 0.25)

    # 2. Willingness to pay (weight 0.20) — people_pay bool + segment WTP
    wtp_score = 0.7 if viability.people_pay else 0.2
    high_wtp = sum(1 for s in pain.user_segments if s.willingness_to_pay == "high")
    if high_wtp >= 2:
        wtp_score = min(1.0, wtp_score + 0.2)
    elif high_wtp == 1:
        wtp_score = min(1.0, wtp_score + 0.1)
    scores["willingness_to_pay"] = (wtp_score, 0.20)

    # 3. Market gap (weight 0.20) — gap_size from viability analysis
    #    Tighter spread so a single category flip doesn't swing score >4pts
    gap_map = {"large": 0.85, "medium": 0.65, "small": 0.4, "none": 0.1}
    scores["market_gap"] = (gap_map.get(viability.gap_size, 0.5), 0.20)

    # 4. Reachability (weight 0.15) — reachability from viability analysis
    reach_map = {"easy": 0.85, "moderate": 0.6, "hard": 0.3}
    scores["reachability"] = (reach_map.get(viability.reachability, 0.5), 0.15)

    # 5. Competition health (weight 0.10) — saturation + unserved needs
    sat_map = {"low": 0.75, "medium": 0.6, "high": 0.35}
    comp_score = sat_map.get(comp.market_saturation, 0.5)
    if comp.underserved_needs:
        comp_score = min(1.0, comp_score + len(comp.underserved_needs) * 0.05)
    scores["competition"] = (comp_score, 0.10)

    # 6. Market momentum (weight 0.10) — growth direction
    if market:
        growth_map = {"growing": 0.8, "stable": 0.5, "shrinking": 0.2, "unknown": 0.45}
        scores["momentum"] = (growth_map.get(market.growth_direction, 0.4), 0.10)
    else:
        scores["momentum"] = (0.4, 0.10)

    # Weighted average
    total_score = sum(s * w for s, w in scores.values())
    total_weight = sum(w for _, w in scores.values())
    confidence = total_score / total_weight

    # Penalty for graveyard failures with no clear differentiator
    if graveyard and len(graveyard.previous_attempts) >= 3:
        confidence *= 0.85  # 15% penalty for crowded graveyard

    return round(max(0.05, min(0.95, confidence)), 2)


def _apply_verdict_guardrail(verdict: Verdict | str, confidence: float) -> float:
    """Soft-clamp confidence so it doesn't contradict the verdict.

    Prevents displaying "BUILD 28%" or "SKIP 85%" — keeps the number
    directionally consistent with the qualitative assessment.
    """
    v = verdict.upper()
    if v == "BUILD":
        return max(confidence, 0.55)
    elif v == "SKIP":
        return min(confidence, 0.50)
    else:  # MAYBE
        return max(0.35, min(0.70, confidence))


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

    def get_tools_and_executors(self) -> tuple[ToolSchemas, ToolExecutors]:
        return [], {}

    async def run(self, input_data: SynthesisInput, language: str = "en") -> SynthesisOutput:
        context = self._build_research_context(input_data)

        # Language instruction for non-English output
        lang_suffix = ""
        if language == "lt":
            lang_suffix = (
                "\n\nLANGUAGE REQUIREMENT: Write ALL user-facing text in Lithuanian (lietuvių kalba). "
                "This includes: one_line_summary, reasoning, key_strengths, key_risks, market_gap, "
                "people_pay_reasoning, reachability_reasoning, recommended_mvp, recommended_positioning, "
                "target_user_summary, next_steps, differentiation_strategy, previous_attempts_summary, "
                "lessons_from_failures, estimated_market_size, and each viability signal description. "
                "Keep enum values (BUILD/SKIP/MAYBE, positive/negative/neutral, easy/moderate/hard, "
                "large/medium/small/none) in English — only translate the free-text prose."
            )

        # Pass 1: Viability Analysis (temperature=0 for stable categoricals)
        viability = await self.llm.generate_structured(
            system_prompt=_VIABILITY_PROMPT + lang_suffix,
            user_prompt=context,
            output_schema=_ViabilityAnalysis,
            use_scoring_model=True,
        )

        # Pass 2: Verdict & Strategy (low-temp Sonnet)
        verdict_context = context + self._format_viability_results(viability)
        verdict = await self.llm.generate_structured(
            system_prompt=_VERDICT_PROMPT + lang_suffix,
            user_prompt=verdict_context,
            output_schema=_VerdictStrategy,
            use_synthesis_model=True,
        )

        # Confidence computed algorithmically from structured data
        confidence = _compute_confidence(viability, input_data)
        confidence = _apply_verdict_guardrail(verdict.verdict, confidence)

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
            # From Pass 2 (confidence from _compute_confidence above)
            verdict=verdict.verdict,
            confidence=confidence,
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

        severity_counts = {"high": 0, "moderate": 0, "mild": 0}
        for p in pain.pain_points:
            severity_counts[p.pain_severity] = (
                severity_counts.get(p.pain_severity, 0) + 1
            )
        high_impact = severity_counts["high"]
        pain_signal = (
            f"{high_impact} of {len(pain.pain_points)} high-impact "
            f"({severity_counts['high']} high, {severity_counts['moderate']} moderate, "
            f"{severity_counts['mild']} mild)"
            if pain.pain_points
            else "N/A"
        )

        context = f"""
IDEA: {idea}

═══ PAIN RESEARCH ═══
Target user: {pain.primary_target_user.label}
{len(pain.pain_points)} pain points found — {pain_signal}
Pain summary: {pain.pain_summary}

Top pain points{f" (showing top 5 of {len(pain.pain_points)})" if len(pain.pain_points) > 5 else ""}:
{chr(10).join(f'{i + 1}. "{p.quote}" - {p.author_context} (severity: {p.pain_severity}, source: {p.source})' for i, p in enumerate(pain.pain_points[:5])) or "None found"}

User segments found:
{chr(10).join(f"- {s.label} ({s.frequency} mentions, willingness to pay: {s.willingness_to_pay})" for s in pain.user_segments) or "None found"}

═══ COMPETITIVE LANDSCAPE ═══
{len(competitors.competitors)} competitors
Market saturation: {competitors.market_saturation}
Avg price: {competitors.avg_price_point}

Top competitors{f" (showing top 5 of {len(competitors.competitors)})" if len(competitors.competitors) > 5 else ""}:
{chr(10).join(f"{i + 1}. {c.name} [{c.competitor_type}]: {c.one_liner}" + chr(10) + f"   Pricing: {', '.join(p.price for p in c.pricing)}" + chr(10) + f"   Strengths: {', '.join(c.strengths[:2])}" + chr(10) + f"   Weaknesses: {', '.join(c.weaknesses[:2])}" for i, c in enumerate(competitors.competitors[:5])) or "None found"}

Common complaints:
{chr(10).join(f"- {c}" for c in competitors.common_complaints) or "None found"}

Underserved needs:
{chr(10).join(f"- {n}" for n in competitors.underserved_needs) or "None found"}
"""

        if market_intel:
            context += f"""
═══ MARKET INTELLIGENCE ═══
Market size estimate: {market_intel.market_size_estimate}
Growth direction: {market_intel.growth_direction}
TAM reasoning: {market_intel.tam_reasoning}

Distribution channels:
{chr(10).join(f"- {ch.channel} (reach: {ch.reach_estimate}, effort: {ch.effort})" for ch in market_intel.distribution_channels) or "None found"}

Funding signals:
{chr(10).join(f"- {sig}" for sig in market_intel.funding_signals) or "None found"}
"""

        if graveyard:
            context += f"""
═══ GRAVEYARD RESEARCH ═══
Previous attempts:
{chr(10).join(f"- {a.name}: {a.what_they_did} → Shut down because: {a.shutdown_reason} ({a.year or 'unknown year'})" for a in graveyard.previous_attempts) or "No previous attempts found"}

Failure patterns across attempts:
{chr(10).join(f"- {r}" for r in graveyard.failure_reasons) or "None identified"}

Lessons learned:
{graveyard.lessons_learned or "None identified"}
"""

        return context

    def _format_viability_results(self, viability: _ViabilityAnalysis) -> str:
        """Format Pass 1 viability results as context for Pass 2."""
        signals_text = (
            "\n".join(
                f"- [{sig.direction.upper()}] {sig.signal} "
                f"(confidence: {sig.confidence:.2f}, source: {sig.source})"
                for sig in viability.signals
            )
            or "None"
        )

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
