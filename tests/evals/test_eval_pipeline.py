"""Main eval test file — runs golden cases through the full pipeline and grades results.

This file defines pytest tests that:
1. Load golden cases from YAML
2. Run the full 5-agent pipeline with real LLM + search
3. Grade outputs with code-based and model-based graders
4. Optionally check consistency across multiple trials
5. Save results to JSON for analysis

Usage:
    # Run all evals (expensive — real API calls):
    pytest tests/evals/test_eval_pipeline.py -v --timeout=600

    # Run a single case:
    pytest tests/evals/test_eval_pipeline.py -v --eval-case=ai-pitch-deck-generator

    # Run only a category:
    pytest tests/evals/test_eval_pipeline.py -v --category=obviously_bad

    # Run with consistency checking (3 trials per case):
    pytest tests/evals/test_eval_pipeline.py -v --trials=3

    # Skip model graders (faster, cheaper):
    pytest tests/evals/test_eval_pipeline.py -v --skip-model

    # Combine filters:
    pytest tests/evals/test_eval_pipeline.py -v --category=saturated --skip-model --timeout=300
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import pytest

from tests.evals.graders.code_graders import run_all_code_graders
from tests.evals.graders.consistency import run_consistency_graders
from tests.evals.graders.model_graders import run_all_model_graders
from tests.evals.harness import (
    EvalRun,
    GoldenCase,
    TrialResult,
    load_golden_cases,
    run_full_pipeline,
)

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


# ──────────────────────────────────────────────
# Load and filter cases
# ──────────────────────────────────────────────


def _get_cases(eval_case_filter: str | None, category_filter: str | None) -> list[GoldenCase]:
    cases = load_golden_cases()

    if eval_case_filter:
        cases = [c for c in cases if c.id == eval_case_filter]
        if not cases:
            pytest.skip(f"No case found with id '{eval_case_filter}'")

    if category_filter:
        cases = [c for c in cases if c.category == category_filter]
        if not cases:
            pytest.skip(f"No cases found in category '{category_filter}'")

    return cases


# ──────────────────────────────────────────────
# Individual case eval
# ──────────────────────────────────────────────


class TestEvalPipeline:
    """Run each golden case through the full pipeline and grade it."""

    @pytest.mark.asyncio
    async def test_eval_single_case(
        self,
        eval_case_filter: str | None,
        category_filter: str | None,
        skip_model_graders: bool,
    ):
        """Run a single eval case (use --eval-case to select)."""
        if not eval_case_filter:
            pytest.skip("Use --eval-case=<id> to run a single case eval")

        cases = _get_cases(eval_case_filter, None)
        case = cases[0]

        print(f"\n{'='*60}")
        print(f"EVAL: {case.id}")
        print(f"IDEA: {case.idea}")
        print(f"CATEGORY: {case.category}")
        print(f"EXPECTED: {case.expected_verdict}")
        print(f"{'='*60}")

        # Run pipeline
        trial = await run_full_pipeline(case.idea)
        trial.case_id = case.id
        trial.trial_number = 1

        if trial.error:
            print(f"\nPIPELINE ERROR: {trial.error}")
            pytest.fail(f"Pipeline failed: {trial.error}")

        # Run code graders
        code_grades = run_all_code_graders(case, trial)
        trial.grades.extend(code_grades)

        # Run model graders
        if not skip_model_graders:
            model_grades = await run_all_model_graders(case, trial)
            trial.grades.extend(model_grades)

        # Print results
        _print_trial_results(case, trial)

        # Save results
        _save_single_result(case, trial)

        # Assert
        failed = [g for g in trial.grades if not g.passed]
        if failed:
            fail_summary = "\n".join(
                f"  FAIL [{g.grader}] {g.details}" for g in failed
            )
            print(f"\nFAILED GRADES:\n{fail_summary}")
            # Don't hard-fail — evals are informational, not blocking
            # pytest.fail(f"{len(failed)} graders failed:\n{fail_summary}")


class TestEvalSuite:
    """Run all golden cases (or a filtered subset)."""

    @pytest.mark.asyncio
    async def test_eval_all_cases(
        self,
        eval_case_filter: str | None,
        category_filter: str | None,
        num_trials: int,
        skip_model_graders: bool,
    ):
        """Run the full eval suite across all cases."""
        if eval_case_filter:
            pytest.skip("Single case mode — use TestEvalPipeline instead")

        cases = _get_cases(None, category_filter)

        print(f"\n{'='*60}")
        print(f"EVAL SUITE: {len(cases)} cases, {num_trials} trial(s) each")
        if category_filter:
            print(f"CATEGORY FILTER: {category_filter}")
        print(f"MODEL GRADERS: {'off' if skip_model_graders else 'on'}")
        print(f"{'='*60}")

        eval_run = EvalRun(
            started_at=_now(),
            cases=cases,
        )

        for case in cases:
            print(f"\n--- {case.id} ({case.category}) ---")
            case_trials: list[TrialResult] = []

            for trial_num in range(1, num_trials + 1):
                print(f"  Trial {trial_num}/{num_trials}...")

                trial = await run_full_pipeline(case.idea)
                trial.case_id = case.id
                trial.trial_number = trial_num

                if trial.error:
                    print(f"  ERROR: {trial.error}")
                    eval_run.trials.append(trial)
                    case_trials.append(trial)
                    continue

                # Code graders
                code_grades = run_all_code_graders(case, trial)
                trial.grades.extend(code_grades)

                # Model graders
                if not skip_model_graders:
                    model_grades = await run_all_model_graders(case, trial)
                    trial.grades.extend(model_grades)

                eval_run.trials.append(trial)
                case_trials.append(trial)

                verdict = "N/A"
                if trial.synthesis:
                    v = trial.synthesis.verdict
                    verdict = v.value if hasattr(v, "value") else str(v)
                passed = sum(1 for g in trial.grades if g.passed)
                total = len(trial.grades)
                print(f"  Verdict: {verdict} | Score: {trial.score:.2f} | Grades: {passed}/{total} passed")

            # Consistency graders (only if multiple trials)
            if len(case_trials) > 1:
                consistency_grades = run_consistency_graders(case_trials)
                # Attach consistency grades to the first trial for reporting
                case_trials[0].grades.extend(consistency_grades)
                for g in consistency_grades:
                    status = "PASS" if g.passed else "FAIL"
                    print(f"  [{status}] {g.grader}: {g.details}")

        # Print summary
        summary = eval_run.summary()
        print(f"\n{'='*60}")
        print("EVAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total trials: {summary['total_trials']}")
        print(f"Pass rate: {summary['pass_rate']:.1%}")
        print(f"Avg score: {summary['avg_score']:.2f}")
        print()
        for cat, stats in summary["by_category"].items():
            print(f"  {cat}: {stats['pass_rate']:.1%} pass rate, {stats['avg_score']:.2f} avg score ({stats['trials']} trials)")
        print()
        if summary["failed_cases"]:
            print("Failed cases:")
            for f in summary["failed_cases"]:
                print(f"  - {f['case_id']} (trial {f['trial']}): {f['error'] or 'grader failures'}")
        print(f"{'='*60}")

        # Save results
        result_path = eval_run.save()
        print(f"\nResults saved to: {result_path}")


# ──────────────────────────────────────────────
# Offline grading (grade pre-saved outputs without re-running agents)
# ──────────────────────────────────────────────


class TestEvalOffline:
    """Grade previously saved eval results without re-running agents.

    Use this to re-grade with updated graders without paying for new API calls.
    """

    @pytest.mark.asyncio
    async def test_regrade_latest(self, skip_model_graders: bool):
        """Re-grade the most recent eval results file."""
        results_files = sorted(RESULTS_DIR.glob("eval_*.json"))
        if not results_files:
            pytest.skip("No previous eval results to re-grade")

        latest = results_files[-1]
        print(f"\nRe-grading: {latest.name}")

        with open(latest) as f:
            data = json.load(f)

        cases = load_golden_cases()
        cases_by_id = {c.id: c for c in cases}

        regraded = 0
        for trial_data in data.get("trials", []):
            case = cases_by_id.get(trial_data.get("case_id"))
            if not case:
                continue

            outputs = trial_data.get("outputs", {})

            # Reconstruct minimal trial object for graders
            trial = _reconstruct_trial(trial_data, outputs)

            # Re-run code graders
            new_grades = run_all_code_graders(case, trial)

            passed = sum(1 for g in new_grades if g.passed)
            total = len(new_grades)
            print(f"  {case.id}: {passed}/{total} code grades passed (score: {sum(g.score for g in new_grades)/total:.2f})")
            regraded += 1

        print(f"\nRe-graded {regraded} trials")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _print_trial_results(case: GoldenCase, trial: TrialResult) -> None:
    """Print detailed results for a single trial."""
    print(f"\nDuration: {trial.duration_seconds:.1f}s")

    if trial.pain_discovery:
        print(f"Pain points: {len(trial.pain_discovery.pain_points)}")
        print(f"Target user: {trial.pain_discovery.primary_target_user.label}")

    if trial.competitor_research:
        names = [c.name for c in trial.competitor_research.competitors]
        print(f"Competitors: {names}")
        print(f"Saturation: {trial.competitor_research.market_saturation}")

    if trial.market_intelligence:
        print(f"TAM: {trial.market_intelligence.market_size_estimate}")
        print(f"Growth: {trial.market_intelligence.growth_direction}")

    if trial.graveyard_research:
        attempts = [a.name for a in trial.graveyard_research.previous_attempts]
        print(f"Failed attempts: {attempts}")

    if trial.synthesis:
        v = trial.synthesis.verdict
        verdict = v.value if hasattr(v, "value") else str(v)
        print(f"\nVERDICT: {verdict} (confidence: {trial.synthesis.confidence:.2f})")
        print(f"Summary: {trial.synthesis.one_line_summary}")
        print(f"Opportunity score: {trial.synthesis.opportunity_score:.2f}")

    print(f"\nGRADES ({len(trial.grades)} total):")
    for g in trial.grades:
        status = "PASS" if g.passed else "FAIL"
        print(f"  [{status}] {g.grader} ({g.score:.2f}): {g.details}")

    print(f"\nOverall score: {trial.score:.2f}")


def _save_single_result(case: GoldenCase, trial: TrialResult) -> None:
    """Save a single trial result to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"eval_{case.id}_{_now()}.json"
    data = {
        "case": {
            "id": case.id,
            "idea": case.idea,
            "category": case.category,
            "expected_verdict": case.expected_verdict,
        },
        "trial": trial.to_dict(),
    }
    path.write_text(json.dumps(data, indent=2, default=str))
    logger.info("Saved result to %s", path)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


class _SimpleNamespace:
    """Minimal object for reconstructing trial outputs from JSON."""

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            if isinstance(v, dict):
                setattr(self, k, _SimpleNamespace(**v))
            elif isinstance(v, list):
                setattr(self, k, [
                    _SimpleNamespace(**item) if isinstance(item, dict) else item
                    for item in v
                ])
            else:
                setattr(self, k, v)


def _reconstruct_trial(trial_data: dict, outputs: dict) -> TrialResult:
    """Reconstruct a TrialResult from saved JSON for re-grading."""
    trial = TrialResult(
        case_id=trial_data.get("case_id", ""),
        trial_number=trial_data.get("trial_number", 0),
    )

    for key in ("pain_discovery", "competitor_research", "market_intelligence", "graveyard_research", "synthesis"):
        data = outputs.get(key)
        if data and isinstance(data, dict):
            setattr(trial, key, _SimpleNamespace(**data))

    return trial
