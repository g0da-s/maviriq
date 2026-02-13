"""Consistency grader — measures Pass^k (all k trials agree on verdict).

This is critical for agent reliability. If the same idea produces BUILD on
one run and SKIP on another, the prompts need work.

Usage:
    Run the eval suite with --trials=3 to enable consistency checking.
"""

from __future__ import annotations

from tests.evals.harness import GradeResult, TrialResult


def grade_verdict_consistency(trials: list[TrialResult]) -> GradeResult:
    """Check that all trials for the same case produce the same verdict.

    This measures Pass^k — the probability that ALL k trials succeed.
    For reliability-critical applications, this is the key metric.
    """
    verdicts = []
    for t in trials:
        if t.synthesis is None:
            continue
        v = t.synthesis.verdict
        verdicts.append(v.value if hasattr(v, "value") else str(v))

    if len(verdicts) < 2:
        return GradeResult(
            grader="consistency:verdict",
            agent="synthesis",
            passed=True,
            score=1.0,
            details="Fewer than 2 trials with synthesis output — can't check consistency",
        )

    unique = set(verdicts)
    all_agree = len(unique) == 1
    # Score: fraction of trials that agree with the majority
    from collections import Counter
    most_common = Counter(verdicts).most_common(1)[0]
    agreement_ratio = most_common[1] / len(verdicts)

    return GradeResult(
        grader="consistency:verdict",
        agent="synthesis",
        passed=all_agree,
        score=agreement_ratio,
        details=f"Verdicts across {len(verdicts)} trials: {verdicts} — {'CONSISTENT' if all_agree else 'INCONSISTENT'}",
    )


def grade_confidence_consistency(trials: list[TrialResult]) -> GradeResult:
    """Check that confidence scores are reasonably consistent across trials.

    Allows some variance (LLMs are non-deterministic) but flags if the
    spread is too wide (e.g., 0.3 vs 0.9 for the same idea).
    """
    confidences = []
    for t in trials:
        if t.synthesis is None:
            continue
        confidences.append(t.synthesis.confidence)

    if len(confidences) < 2:
        return GradeResult(
            grader="consistency:confidence",
            agent="synthesis",
            passed=True,
            score=1.0,
            details="Fewer than 2 trials — can't check consistency",
        )

    spread = max(confidences) - min(confidences)
    mean = sum(confidences) / len(confidences)
    passed = spread <= 0.25  # Allow up to 0.25 variance
    score = max(0.0, 1.0 - spread / 0.5)  # Penalize wider spreads

    return GradeResult(
        grader="consistency:confidence",
        agent="synthesis",
        passed=passed,
        score=score,
        details=f"Confidences: {[f'{c:.2f}' for c in confidences]} (spread: {spread:.2f}, mean: {mean:.2f})",
    )


def grade_opportunity_score_consistency(trials: list[TrialResult]) -> GradeResult:
    """Check that opportunity scores are consistent across trials."""
    scores = []
    for t in trials:
        if t.synthesis is None:
            continue
        scores.append(t.synthesis.opportunity_score)

    if len(scores) < 2:
        return GradeResult(
            grader="consistency:opportunity_score",
            agent="synthesis",
            passed=True,
            score=1.0,
            details="Fewer than 2 trials — can't check consistency",
        )

    spread = max(scores) - min(scores)
    passed = spread <= 0.30
    score = max(0.0, 1.0 - spread / 0.5)

    return GradeResult(
        grader="consistency:opportunity_score",
        agent="synthesis",
        passed=passed,
        score=score,
        details=f"Opportunity scores: {[f'{s:.2f}' for s in scores]} (spread: {spread:.2f})",
    )


def run_consistency_graders(trials: list[TrialResult]) -> list[GradeResult]:
    """Run all consistency graders on a set of trials for the same case."""
    return [
        grade_verdict_consistency(trials),
        grade_confidence_consistency(trials),
        grade_opportunity_score_consistency(trials),
    ]
