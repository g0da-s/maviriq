"""Model-based graders — uses an LLM (Haiku) as a judge to evaluate output quality.

These graders handle subjective quality checks that code can't:
- Are pain points grounded and plausible?
- Are competitors actually relevant to the idea?
- Is the synthesis reasoning well-argued and data-driven?
- Does the market intelligence make sense?

We use Haiku (cheap model) to judge Sonnet's (reasoning model) output.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

from tests.evals.harness import GoldenCase, GradeResult

logger = logging.getLogger(__name__)


class JudgmentResult(BaseModel):
    """Structured output from the LLM judge."""

    score: float = Field(ge=0.0, le=1.0, description="Quality score from 0.0 (terrible) to 1.0 (excellent)")
    passed: bool = Field(description="Whether this meets the minimum quality bar")
    reasoning: str = Field(description="Brief explanation of the judgment")


async def _judge(
    system_prompt: str,
    user_prompt: str,
) -> JudgmentResult:
    """Run a single LLM judgment using the cheap model."""
    from maviriq.services.llm import LLMService

    llm = LLMService()
    result = await llm.generate_structured(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_schema=JudgmentResult,
        use_cheap_model=True,  # Use Haiku to judge Sonnet
    )
    return result


# ──────────────────────────────────────────────
# Pain Discovery model graders
# ──────────────────────────────────────────────

PAIN_GROUNDEDNESS_SYSTEM = """\
You are an eval grader for an AI research agent. Your job is to judge whether \
the pain points found by the agent are grounded and plausible.

A pain point is GROUNDED if:
- The quote sounds like something a real person would say (not generic marketing speak)
- The author_context is specific enough to be believable
- The severity rating makes sense for the complaint
- The source attribution is reasonable (e.g., Reddit for casual complaints)

A pain point is NOT grounded if:
- The quote is too perfect or reads like it was fabricated
- The severity is wildly inappropriate (e.g., severity 5 for a minor UI annoyance)
- The author_context is suspiciously generic ("user", "someone")

Score 0.0 = clearly fabricated, 1.0 = convincingly real. Pass threshold: 0.5"""


async def grade_pain_groundedness(case: GoldenCase, output: Any) -> GradeResult:
    """Use LLM to judge whether pain points seem grounded vs fabricated."""
    if not output or not output.pain_points:
        return GradeResult(
            grader="model:pain_groundedness",
            agent="pain_discovery",
            passed=True,
            score=0.5,
            details="No pain points to judge",
        )

    points_text = "\n".join(
        f'- Quote: "{p.quote}" | Source: {p.source} | Author: {p.author_context} | Severity: {p.pain_severity}/5'
        for p in output.pain_points[:8]  # limit to save tokens
    )

    user_prompt = f"""\
Business idea: {case.idea}

Pain points found by the research agent:
{points_text}

Judge whether these pain points appear grounded and plausible, or fabricated."""

    try:
        judgment = await _judge(PAIN_GROUNDEDNESS_SYSTEM, user_prompt)
        return GradeResult(
            grader="model:pain_groundedness",
            agent="pain_discovery",
            passed=judgment.passed,
            score=judgment.score,
            details=judgment.reasoning,
        )
    except Exception as e:
        return GradeResult(
            grader="model:pain_groundedness",
            agent="pain_discovery",
            passed=True,
            score=0.5,
            details=f"Judge failed: {e}",
        )


PAIN_TARGET_USER_SYSTEM = """\
You are an eval grader. Judge whether the chosen primary target user makes \
sense for the business idea.

A GOOD target user is:
- Specific enough to build for (not "everyone" or "businesses")
- Has the most pain AND highest willingness to pay
- Is reachable through known channels

A BAD target user is:
- Too broad ("people", "companies")
- Not the segment with the most pain
- Unreachable or unmonetizable

Score 0.0 = nonsensical target, 1.0 = perfectly chosen. Pass threshold: 0.5"""


async def grade_pain_target_user_quality(case: GoldenCase, output: Any) -> GradeResult:
    """Use LLM to judge whether the chosen target user is sensible."""
    if not output or not output.primary_target_user:
        return GradeResult(
            grader="model:pain_target_user_quality",
            agent="pain_discovery",
            passed=False,
            score=0.0,
            details="No target user",
        )

    segments_text = "\n".join(
        f"- {s.label}: {s.description} (frequency: {s.frequency}, WTP: {s.willingness_to_pay})"
        for s in output.user_segments
    )

    user_prompt = f"""\
Business idea: {case.idea}

User segments discovered:
{segments_text}

Chosen primary target user: {output.primary_target_user.label}
Description: {output.primary_target_user.description}
Willingness to pay: {output.primary_target_user.willingness_to_pay}

Judge whether this is a well-chosen primary target user for this idea."""

    try:
        judgment = await _judge(PAIN_TARGET_USER_SYSTEM, user_prompt)
        return GradeResult(
            grader="model:pain_target_user_quality",
            agent="pain_discovery",
            passed=judgment.passed,
            score=judgment.score,
            details=judgment.reasoning,
        )
    except Exception as e:
        return GradeResult(
            grader="model:pain_target_user_quality",
            agent="pain_discovery",
            passed=True,
            score=0.5,
            details=f"Judge failed: {e}",
        )


# ──────────────────────────────────────────────
# Competitor Research model graders
# ──────────────────────────────────────────────

COMPETITOR_RELEVANCE_SYSTEM = """\
You are an eval grader. Judge whether the competitors found are actually \
relevant to the business idea.

RELEVANT competitors:
- Solve a similar problem for a similar audience
- Would be considered alternatives by the target user
- Are actual companies/products, not random unrelated results

IRRELEVANT competitors:
- Solve a completely different problem
- Target a completely different audience
- Are not real products (fabricated names/URLs)

Score 0.0 = completely irrelevant, 1.0 = perfectly relevant. Pass threshold: 0.5"""


async def grade_competitor_relevance(case: GoldenCase, output: Any) -> GradeResult:
    """Use LLM to judge whether found competitors are relevant to the idea."""
    if not output or not output.competitors:
        return GradeResult(
            grader="model:competitor_relevance",
            agent="competitor_research",
            passed=True,
            score=0.5,
            details="No competitors to judge",
        )

    comps_text = "\n".join(
        f"- {c.name} ({c.url}): {c.one_liner}"
        for c in output.competitors[:8]
    )

    user_prompt = f"""\
Business idea: {case.idea}

Competitors found by the research agent:
{comps_text}

Judge whether these competitors are actually relevant to this business idea."""

    try:
        judgment = await _judge(COMPETITOR_RELEVANCE_SYSTEM, user_prompt)
        return GradeResult(
            grader="model:competitor_relevance",
            agent="competitor_research",
            passed=judgment.passed,
            score=judgment.score,
            details=judgment.reasoning,
        )
    except Exception as e:
        return GradeResult(
            grader="model:competitor_relevance",
            agent="competitor_research",
            passed=True,
            score=0.5,
            details=f"Judge failed: {e}",
        )


# ──────────────────────────────────────────────
# Market Intelligence model graders
# ──────────────────────────────────────────────

MARKET_TAM_SYSTEM = """\
You are an eval grader. Judge whether the market size estimate (TAM) is \
reasonable for the business idea.

A GOOD TAM estimate:
- Is in the right order of magnitude for this market
- Has logical reasoning that explains how the number was derived
- Acknowledges uncertainty when data is sparse
- Is not obviously fabricated (e.g., "$50B market" for a tiny niche)

A BAD TAM estimate:
- Is wildly off (orders of magnitude wrong)
- Has no reasoning or circular reasoning
- Claims precision without data ("exactly $3.2B")

Score 0.0 = completely wrong, 1.0 = well-reasoned and plausible. Pass threshold: 0.5"""


async def grade_market_tam_quality(case: GoldenCase, output: Any) -> GradeResult:
    """Use LLM to judge whether the TAM estimate is reasonable."""
    if not output:
        return GradeResult(
            grader="model:market_tam_quality",
            agent="market_intelligence",
            passed=True,
            score=0.5,
            details="No market intelligence output",
        )

    user_prompt = f"""\
Business idea: {case.idea}
Category: {case.category}

Market size estimate: {output.market_size_estimate}
Growth direction: {output.growth_direction}
TAM reasoning: {output.tam_reasoning}

Judge whether this market size estimate is reasonable and well-reasoned."""

    try:
        judgment = await _judge(MARKET_TAM_SYSTEM, user_prompt)
        return GradeResult(
            grader="model:market_tam_quality",
            agent="market_intelligence",
            passed=judgment.passed,
            score=judgment.score,
            details=judgment.reasoning,
        )
    except Exception as e:
        return GradeResult(
            grader="model:market_tam_quality",
            agent="market_intelligence",
            passed=True,
            score=0.5,
            details=f"Judge failed: {e}",
        )


# ──────────────────────────────────────────────
# Synthesis model graders
# ──────────────────────────────────────────────

SYNTHESIS_REASONING_SYSTEM = """\
You are an eval grader. Judge the quality of the synthesis agent's reasoning.

GOOD reasoning:
- Cites specific data from the research (pain points, competitor names, market data)
- Connects evidence to the verdict logically
- Addresses counterarguments and risks
- Is appropriately skeptical (doesn't oversell weak ideas)
- Mentions specific competitors, pain quotes, or market figures

BAD reasoning:
- Is generic and could apply to any idea
- Doesn't reference the actual research data
- Is overly optimistic without justification
- Uses vague language ("some users", "potential market")

Score 0.0 = generic/unsupported, 1.0 = data-driven and well-argued. Pass threshold: 0.5"""


async def grade_synthesis_reasoning_quality(case: GoldenCase, output: Any) -> GradeResult:
    """Use LLM to judge the quality of synthesis reasoning."""
    if not output:
        return GradeResult(
            grader="model:synthesis_reasoning_quality",
            agent="synthesis",
            passed=False,
            score=0.0,
            details="No synthesis output",
        )

    user_prompt = f"""\
Business idea: {case.idea}
Category: {case.category} ({case.notes})
Verdict: {output.verdict}
Confidence: {output.confidence}

One-line summary: {output.one_line_summary}

Reasoning:
{output.reasoning}

Key strengths: {output.key_strengths}
Key risks: {output.key_risks}

Judge whether this reasoning is well-argued and data-driven, or generic and unsupported."""

    try:
        judgment = await _judge(SYNTHESIS_REASONING_SYSTEM, user_prompt)
        return GradeResult(
            grader="model:synthesis_reasoning_quality",
            agent="synthesis",
            passed=judgment.passed,
            score=judgment.score,
            details=judgment.reasoning,
        )
    except Exception as e:
        return GradeResult(
            grader="model:synthesis_reasoning_quality",
            agent="synthesis",
            passed=True,
            score=0.5,
            details=f"Judge failed: {e}",
        )


SYNTHESIS_SKEPTICISM_SYSTEM = """\
You are an eval grader. Judge whether the synthesis agent is appropriately \
skeptical, especially for weak ideas.

The synthesis agent is told to be biased toward skepticism. Most ideas should \
get SKIP or MAYBE, not BUILD.

APPROPRIATE skepticism:
- Bad ideas get SKIP with clear reasoning
- Saturated markets get flagged as high-risk
- Failed ideas are recognized with caution
- BUILD is reserved for ideas with strong evidence across all dimensions

INAPPROPRIATE behavior:
- Giving BUILD to obviously bad ideas
- Being too generous with confidence scores
- Ignoring red flags (failed predecessors, saturated markets)
- Giving the same confidence to very different ideas

Score 0.0 = not skeptical enough, 1.0 = appropriately calibrated. Pass threshold: 0.5"""


async def grade_synthesis_skepticism(case: GoldenCase, output: Any) -> GradeResult:
    """Use LLM to judge whether synthesis is appropriately skeptical."""
    if not output:
        return GradeResult(
            grader="model:synthesis_skepticism",
            agent="synthesis",
            passed=True,
            score=0.5,
            details="No synthesis output",
        )

    verdict = output.verdict.value if hasattr(output.verdict, "value") else str(output.verdict)

    user_prompt = f"""\
Business idea: {case.idea}
Category: {case.category}
Notes: {case.notes}
Expected verdict(s): {case.expected_verdict}
Expected confidence range: {case.confidence_range}

Actual verdict: {verdict}
Actual confidence: {output.confidence}
One-line summary: {output.one_line_summary}
Key risks identified: {output.key_risks}

Judge whether the agent is appropriately skeptical for this idea.
Consider: Is the verdict and confidence level right for this type of idea?"""

    try:
        judgment = await _judge(SYNTHESIS_SKEPTICISM_SYSTEM, user_prompt)
        return GradeResult(
            grader="model:synthesis_skepticism",
            agent="synthesis",
            passed=judgment.passed,
            score=judgment.score,
            details=judgment.reasoning,
        )
    except Exception as e:
        return GradeResult(
            grader="model:synthesis_skepticism",
            agent="synthesis",
            passed=True,
            score=0.5,
            details=f"Judge failed: {e}",
        )


# ──────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────

ALL_MODEL_GRADERS = {
    "pain_discovery": [
        grade_pain_groundedness,
        grade_pain_target_user_quality,
    ],
    "competitor_research": [
        grade_competitor_relevance,
    ],
    "market_intelligence": [
        grade_market_tam_quality,
    ],
    "synthesis": [
        grade_synthesis_reasoning_quality,
        grade_synthesis_skepticism,
    ],
}


async def run_all_model_graders(case: GoldenCase, trial: Any) -> list[GradeResult]:
    """Run all model graders against a trial result.

    Model graders are async (they call the LLM), so we run them in parallel.
    """
    agent_output_map = {
        "pain_discovery": trial.pain_discovery,
        "competitor_research": trial.competitor_research,
        "market_intelligence": trial.market_intelligence,
        "synthesis": trial.synthesis,
    }

    tasks = []
    for agent_name, graders in ALL_MODEL_GRADERS.items():
        output = agent_output_map.get(agent_name)
        for grader_fn in graders:
            tasks.append(grader_fn(case, output))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    grade_results = []
    for r in results:
        if isinstance(r, Exception):
            grade_results.append(
                GradeResult(
                    grader="model:unknown",
                    agent="unknown",
                    passed=True,
                    score=0.5,
                    details=f"Model grader crashed: {r}",
                )
            )
        else:
            grade_results.append(r)

    return grade_results
