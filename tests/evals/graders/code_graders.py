"""Code-based (deterministic) graders for each agent.

These graders check structural properties of agent outputs:
- Field counts, value ranges, source diversity
- Expected competitors found, saturation levels
- Confidence calibration, verdict consistency
- Data quality flags

They're fast, free, and deterministic — the first line of defense.
"""

from __future__ import annotations

from typing import Any

from tests.evals.harness import GoldenCase, GradeResult


# ──────────────────────────────────────────────
# Pain Discovery graders
# ──────────────────────────────────────────────


def grade_pain_point_count(case: GoldenCase, output: Any) -> GradeResult:
    """Check that we found at least the minimum expected pain points."""
    count = len(output.pain_points) if output else 0
    passed = count >= case.min_pain_points
    return GradeResult(
        grader="code:pain_point_count",
        agent="pain_discovery",
        passed=passed,
        score=min(count / max(case.min_pain_points, 1), 1.0),
        details=f"Found {count} pain points (min expected: {case.min_pain_points})",
    )


def grade_pain_severity_distribution(case: GoldenCase, output: Any) -> GradeResult:
    """Check that severity ratings are distributed, not all the same value."""
    if not output or len(output.pain_points) < 3:
        return GradeResult(
            grader="code:pain_severity_distribution",
            agent="pain_discovery",
            passed=True,  # can't check distribution with < 3 points
            score=0.5,
            details="Too few pain points to check distribution",
        )

    severities = [p.pain_severity for p in output.pain_points]
    unique = len(set(severities))
    passed = unique >= 2  # at least 2 different severity values
    score = min(unique / 3, 1.0)  # ideally 3+ different values
    return GradeResult(
        grader="code:pain_severity_distribution",
        agent="pain_discovery",
        passed=passed,
        score=score,
        details=f"Severity values: {sorted(set(severities))} ({unique} unique across {len(severities)} points)",
    )


def grade_pain_source_diversity(case: GoldenCase, output: Any) -> GradeResult:
    """Check that pain points come from multiple sources, not all from one."""
    if not output or not output.pain_points:
        return GradeResult(
            grader="code:pain_source_diversity",
            agent="pain_discovery",
            passed=True,
            score=0.5,
            details="No pain points to check",
        )

    sources = set(p.source for p in output.pain_points)
    passed = len(sources) >= 2
    score = min(len(sources) / 3, 1.0)  # ideally 3+ sources
    return GradeResult(
        grader="code:pain_source_diversity",
        agent="pain_discovery",
        passed=passed,
        score=score,
        details=f"Sources used: {sorted(sources)}",
    )



def grade_pain_has_target_user(case: GoldenCase, output: Any) -> GradeResult:
    """Check that a primary target user was identified."""
    if not output:
        return GradeResult(
            grader="code:pain_has_target_user",
            agent="pain_discovery",
            passed=False,
            score=0.0,
            details="No output",
        )

    has_target = output.primary_target_user is not None
    has_label = has_target and bool(output.primary_target_user.label.strip())
    passed = has_label
    return GradeResult(
        grader="code:pain_has_target_user",
        agent="pain_discovery",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=f"Target user: '{output.primary_target_user.label}'" if has_target else "No target user",
    )


# ──────────────────────────────────────────────
# Competitor Research graders
# ──────────────────────────────────────────────


def grade_competitor_count(case: GoldenCase, output: Any) -> GradeResult:
    """Check that we found at least the minimum expected competitors."""
    count = len(output.competitors) if output else 0
    passed = count >= case.min_competitors
    return GradeResult(
        grader="code:competitor_count",
        agent="competitor_research",
        passed=passed,
        score=min(count / max(case.min_competitors, 1), 1.0),
        details=f"Found {count} competitors (min expected: {case.min_competitors})",
    )


def grade_known_competitors_found(case: GoldenCase, output: Any) -> GradeResult:
    """Check that known competitors were found (substring match on name)."""
    if not case.known_competitors:
        return GradeResult(
            grader="code:known_competitors_found",
            agent="competitor_research",
            passed=True,
            score=1.0,
            details="No known competitors to check",
        )

    if not output or not output.competitors:
        return GradeResult(
            grader="code:known_competitors_found",
            agent="competitor_research",
            passed=False,
            score=0.0,
            details=f"Expected to find: {case.known_competitors}, found none",
        )

    found_names = [c.name.lower() for c in output.competitors]
    matched = []
    missed = []
    for expected in case.known_competitors:
        if any(expected.lower() in name for name in found_names):
            matched.append(expected)
        else:
            missed.append(expected)

    # Passing requires finding at least half of known competitors
    ratio = len(matched) / len(case.known_competitors)
    passed = ratio >= 0.5
    return GradeResult(
        grader="code:known_competitors_found",
        agent="competitor_research",
        passed=passed,
        score=ratio,
        details=f"Found: {matched}, missed: {missed} (from actual: {[c.name for c in output.competitors]})",
    )


def grade_market_saturation(case: GoldenCase, output: Any) -> GradeResult:
    """Check that market saturation matches expected value(s)."""
    if not case.expected_saturation:
        return GradeResult(
            grader="code:market_saturation",
            agent="competitor_research",
            passed=True,
            score=1.0,
            details="No expected saturation to check",
        )

    if not output:
        return GradeResult(
            grader="code:market_saturation",
            agent="competitor_research",
            passed=False,
            score=0.0,
            details="No output",
        )

    actual = output.market_saturation
    passed = actual in case.expected_saturation
    return GradeResult(
        grader="code:market_saturation",
        agent="competitor_research",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=f"market_saturation='{actual}' (expected one of: {case.expected_saturation})",
    )


def grade_competitor_has_pricing(case: GoldenCase, output: Any) -> GradeResult:
    """Check that at least some competitors have pricing information."""
    if not output or not output.competitors:
        return GradeResult(
            grader="code:competitor_has_pricing",
            agent="competitor_research",
            passed=True,
            score=0.5,
            details="No competitors to check",
        )

    with_pricing = sum(1 for c in output.competitors if c.pricing)
    ratio = with_pricing / len(output.competitors)
    passed = ratio >= 0.3  # at least 30% should have pricing
    return GradeResult(
        grader="code:competitor_has_pricing",
        agent="competitor_research",
        passed=passed,
        score=ratio,
        details=f"{with_pricing}/{len(output.competitors)} competitors have pricing info",
    )


def grade_competitor_has_strengths_weaknesses(case: GoldenCase, output: Any) -> GradeResult:
    """Check that competitors have both strengths and weaknesses populated."""
    if not output or not output.competitors:
        return GradeResult(
            grader="code:competitor_strengths_weaknesses",
            agent="competitor_research",
            passed=True,
            score=0.5,
            details="No competitors to check",
        )

    complete = sum(
        1 for c in output.competitors if c.strengths and c.weaknesses
    )
    ratio = complete / len(output.competitors)
    passed = ratio >= 0.5
    return GradeResult(
        grader="code:competitor_strengths_weaknesses",
        agent="competitor_research",
        passed=passed,
        score=ratio,
        details=f"{complete}/{len(output.competitors)} competitors have both strengths and weaknesses",
    )


# ──────────────────────────────────────────────
# Market Intelligence graders
# ──────────────────────────────────────────────


def grade_market_has_tam(case: GoldenCase, output: Any) -> GradeResult:
    """Check that TAM estimate and reasoning are populated."""
    if not output:
        return GradeResult(
            grader="code:market_has_tam",
            agent="market_intelligence",
            passed=False,
            score=0.0,
            details="No output",
        )

    has_estimate = bool(output.market_size_estimate and output.market_size_estimate.strip())
    has_reasoning = bool(output.tam_reasoning and output.tam_reasoning.strip())
    passed = has_estimate and has_reasoning
    score = (int(has_estimate) + int(has_reasoning)) / 2
    return GradeResult(
        grader="code:market_has_tam",
        agent="market_intelligence",
        passed=passed,
        score=score,
        details=f"TAM estimate: {'yes' if has_estimate else 'no'}, reasoning: {'yes' if has_reasoning else 'no'}",
    )


def grade_market_growth_not_always_unknown(case: GoldenCase, output: Any) -> GradeResult:
    """Check that growth_direction is not always 'unknown' (indicates lazy output)."""
    if not output:
        return GradeResult(
            grader="code:market_growth_not_unknown",
            agent="market_intelligence",
            passed=True,
            score=0.5,
            details="No output",
        )

    is_unknown = output.growth_direction == "unknown"
    # For well-known markets, it should NOT be unknown
    well_known = case.category in ("saturated", "obviously_good")
    passed = not (is_unknown and well_known)
    return GradeResult(
        grader="code:market_growth_not_unknown",
        agent="market_intelligence",
        passed=passed,
        score=0.0 if (is_unknown and well_known) else 1.0,
        details=f"growth_direction='{output.growth_direction}' (category: {case.category})",
    )


def grade_market_has_channels(case: GoldenCase, output: Any) -> GradeResult:
    """Check that at least one distribution channel is identified."""
    if not output:
        return GradeResult(
            grader="code:market_has_channels",
            agent="market_intelligence",
            passed=False,
            score=0.0,
            details="No output",
        )

    count = len(output.distribution_channels)
    passed = count >= 1
    score = min(count / 3, 1.0)
    return GradeResult(
        grader="code:market_has_channels",
        agent="market_intelligence",
        passed=passed,
        score=score,
        details=f"Found {count} distribution channels",
    )


# ──────────────────────────────────────────────
# Graveyard Research graders
# ──────────────────────────────────────────────


def grade_graveyard_finds_failures(case: GoldenCase, output: Any) -> GradeResult:
    """For 'already_failed' cases, check that previous attempts were found."""
    if case.category != "already_failed":
        return GradeResult(
            grader="code:graveyard_finds_failures",
            agent="graveyard_research",
            passed=True,
            score=1.0,
            details=f"Not an 'already_failed' case (category: {case.category})",
        )

    if not output:
        return GradeResult(
            grader="code:graveyard_finds_failures",
            agent="graveyard_research",
            passed=False,
            score=0.0,
            details="No output for an already_failed case",
        )

    attempts = len(output.previous_attempts)
    passed = attempts >= 1
    return GradeResult(
        grader="code:graveyard_finds_failures",
        agent="graveyard_research",
        passed=passed,
        score=min(attempts / 2, 1.0),
        details=f"Found {attempts} previous attempts for a known-failure idea",
    )


def grade_graveyard_has_failure_reasons(case: GoldenCase, output: Any) -> GradeResult:
    """Check that failure_reasons are populated."""
    if not output:
        return GradeResult(
            grader="code:graveyard_has_failure_reasons",
            agent="graveyard_research",
            passed=True,
            score=0.5,
            details="No output",
        )

    count = len(output.failure_reasons)
    passed = count >= 1
    score = min(count / 3, 1.0)  # ideally 3+ failure reasons
    return GradeResult(
        grader="code:graveyard_has_failure_reasons",
        agent="graveyard_research",
        passed=passed,
        score=score,
        details=f"failure_reasons: {count}",
    )


# ──────────────────────────────────────────────
# Synthesis graders
# ──────────────────────────────────────────────


def grade_verdict_matches(case: GoldenCase, output: Any) -> GradeResult:
    """Check that the verdict matches expected verdict(s)."""
    if not output:
        return GradeResult(
            grader="code:verdict_matches",
            agent="synthesis",
            passed=False,
            score=0.0,
            details="No synthesis output",
        )

    actual = output.verdict.value if hasattr(output.verdict, "value") else str(output.verdict)
    passed = actual in case.expected_verdict
    # Partial credit: if it's the first (most likely) expected verdict
    score = 1.0 if passed and actual == case.expected_verdict[0] else (0.5 if passed else 0.0)
    return GradeResult(
        grader="code:verdict_matches",
        agent="synthesis",
        passed=passed,
        score=score,
        details=f"verdict='{actual}' (expected: {case.expected_verdict})",
    )


def grade_confidence_calibration(case: GoldenCase, output: Any) -> GradeResult:
    """Check that confidence falls within the expected range for this case."""
    if not output:
        return GradeResult(
            grader="code:confidence_calibration",
            agent="synthesis",
            passed=False,
            score=0.0,
            details="No synthesis output",
        )

    lo, hi = case.confidence_range
    actual = output.confidence
    passed = lo <= actual <= hi
    # Score based on distance from range if outside
    if passed:
        score = 1.0
    elif actual < lo:
        score = max(0.0, 1.0 - (lo - actual) / 0.3)
    else:
        score = max(0.0, 1.0 - (actual - hi) / 0.3)

    return GradeResult(
        grader="code:confidence_calibration",
        agent="synthesis",
        passed=passed,
        score=score,
        details=f"confidence={actual:.2f} (expected range: [{lo:.2f}, {hi:.2f}])",
    )


def grade_build_has_mvp(case: GoldenCase, output: Any) -> GradeResult:
    """BUILD verdicts should have a recommended MVP."""
    if not output:
        return GradeResult(
            grader="code:build_has_mvp",
            agent="synthesis",
            passed=True,
            score=0.5,
            details="No synthesis output",
        )

    verdict = output.verdict.value if hasattr(output.verdict, "value") else str(output.verdict)
    if verdict != "BUILD":
        return GradeResult(
            grader="code:build_has_mvp",
            agent="synthesis",
            passed=True,
            score=1.0,
            details=f"Verdict is {verdict}, MVP check not applicable",
        )

    has_mvp = bool(output.recommended_mvp and output.recommended_mvp.strip())
    return GradeResult(
        grader="code:build_has_mvp",
        agent="synthesis",
        passed=has_mvp,
        score=1.0 if has_mvp else 0.0,
        details=f"BUILD verdict {'has' if has_mvp else 'MISSING'} recommended MVP",
    )


def grade_summary_not_restating_idea(case: GoldenCase, output: Any) -> GradeResult:
    """Check that one_line_summary explains the verdict, not just restates the idea."""
    if not output:
        return GradeResult(
            grader="code:summary_not_restating",
            agent="synthesis",
            passed=True,
            score=0.5,
            details="No synthesis output",
        )

    summary = output.one_line_summary.lower()
    idea_words = set(case.idea.lower().split())
    summary_words = set(summary.split())

    # If >70% of the summary words are just the idea words, it's restating
    overlap = len(idea_words & summary_words)
    total = len(summary_words) or 1
    overlap_ratio = overlap / total
    passed = overlap_ratio < 0.7
    return GradeResult(
        grader="code:summary_not_restating",
        agent="synthesis",
        passed=passed,
        score=1.0 - overlap_ratio,
        details=f"Summary word overlap with idea: {overlap_ratio:.0%} ({'restating' if not passed else 'ok'})",
    )


def grade_reasoning_length(case: GoldenCase, output: Any) -> GradeResult:
    """Check that reasoning is substantive (3+ paragraphs)."""
    if not output:
        return GradeResult(
            grader="code:reasoning_length",
            agent="synthesis",
            passed=False,
            score=0.0,
            details="No synthesis output",
        )

    paragraphs = [p.strip() for p in output.reasoning.split("\n\n") if p.strip()]
    word_count = len(output.reasoning.split())
    passed = len(paragraphs) >= 2 and word_count >= 100
    return GradeResult(
        grader="code:reasoning_length",
        agent="synthesis",
        passed=passed,
        score=min(word_count / 200, 1.0),
        details=f"{len(paragraphs)} paragraphs, {word_count} words",
    )


def grade_next_steps_actionable(case: GoldenCase, output: Any) -> GradeResult:
    """Check that next_steps are populated."""
    if not output:
        return GradeResult(
            grader="code:next_steps_actionable",
            agent="synthesis",
            passed=False,
            score=0.0,
            details="No synthesis output",
        )

    count = len(output.next_steps)
    passed = count >= 2
    return GradeResult(
        grader="code:next_steps_actionable",
        agent="synthesis",
        passed=passed,
        score=min(count / 3, 1.0),
        details=f"{count} next steps provided",
    )


def grade_confidence_aligns_with_verdict(case: GoldenCase, output: Any) -> GradeResult:
    """Check that confidence is directionally consistent with verdict."""
    if not output:
        return GradeResult(
            grader="code:confidence_verdict_alignment",
            agent="synthesis",
            passed=False,
            score=0.0,
            details="No synthesis output",
        )

    verdict = output.verdict.value if hasattr(output.verdict, "value") else str(output.verdict)
    conf = output.confidence

    # BUILD should have high confidence, SKIP should have low
    if verdict == "BUILD" and conf < 0.4:
        passed = False
        details = f"BUILD verdict but confidence={conf:.2f} (< 0.4)"
    elif verdict == "SKIP" and conf > 0.7:
        passed = False
        details = f"SKIP verdict but confidence={conf:.2f} (> 0.7)"
    else:
        passed = True
        details = f"verdict={verdict}, confidence={conf:.2f} — aligned"

    return GradeResult(
        grader="code:confidence_verdict_alignment",
        agent="synthesis",
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
    )


# ──────────────────────────────────────────────
# Grader registry
# ──────────────────────────────────────────────

ALL_CODE_GRADERS = {
    "pain_discovery": [
        grade_pain_point_count,
        grade_pain_severity_distribution,
        grade_pain_source_diversity,
        grade_pain_has_target_user,
    ],
    "competitor_research": [
        grade_competitor_count,
        grade_known_competitors_found,
        grade_market_saturation,
        grade_competitor_has_pricing,
        grade_competitor_has_strengths_weaknesses,
    ],
    "market_intelligence": [
        grade_market_has_tam,
        grade_market_growth_not_always_unknown,
        grade_market_has_channels,
    ],
    "graveyard_research": [
        grade_graveyard_finds_failures,
        grade_graveyard_has_failure_reasons,
    ],
    "synthesis": [
        grade_verdict_matches,
        grade_confidence_calibration,
        grade_build_has_mvp,
        grade_summary_not_restating_idea,
        grade_reasoning_length,
        grade_next_steps_actionable,
        grade_confidence_aligns_with_verdict,
    ],
}


def run_all_code_graders(case: GoldenCase, trial: Any) -> list[GradeResult]:
    """Run all code graders against a trial result and return grade results."""
    results = []

    agent_output_map = {
        "pain_discovery": trial.pain_discovery,
        "competitor_research": trial.competitor_research,
        "market_intelligence": trial.market_intelligence,
        "graveyard_research": trial.graveyard_research,
        "synthesis": trial.synthesis,
    }

    for agent_name, graders in ALL_CODE_GRADERS.items():
        output = agent_output_map.get(agent_name)
        for grader_fn in graders:
            try:
                result = grader_fn(case, output)
                results.append(result)
            except Exception as e:
                results.append(
                    GradeResult(
                        grader=f"code:{grader_fn.__name__}",
                        agent=agent_name,
                        passed=False,
                        score=0.0,
                        details=f"Grader crashed: {e}",
                    )
                )

    return results
