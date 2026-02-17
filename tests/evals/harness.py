"""Eval harness — orchestrates running agents against golden cases and grading results.

Usage:
    # Run from repo root:
    pytest tests/evals/ -v --timeout=300

    # Filter by case category:
    pytest tests/evals/ -k "obviously_bad"

    # Run with multiple trials (consistency check):
    pytest tests/evals/ --trials=3

The harness loads golden cases from YAML, runs the real agents (with real LLM
and search calls), collects outputs, and passes them through code-based and
model-based graders.

Results are saved to tests/evals/results/ as JSON for later analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

CASES_DIR = Path(__file__).parent / "cases"
RESULTS_DIR = Path(__file__).parent / "results"


# ──────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────


@dataclass
class GoldenCase:
    """A single golden test case loaded from YAML."""

    id: str
    idea: str
    category: str
    expected_verdict: list[str]
    min_pain_points: int
    min_competitors: int
    known_competitors: list[str]
    expected_saturation: list[str]
    confidence_range: list[float]
    notes: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GoldenCase:
        return cls(
            id=d["id"],
            idea=d["idea"],
            category=d["category"],
            expected_verdict=d["expected_verdict"],
            min_pain_points=d.get("min_pain_points", 0),
            min_competitors=d.get("min_competitors", 0),
            known_competitors=d.get("known_competitors", []),
            expected_saturation=d.get("expected_saturation", []),
            confidence_range=d.get("confidence_range", [0.0, 1.0]),
            notes=d.get("notes", ""),
        )


@dataclass
class GradeResult:
    """Result from a single grader check."""

    grader: str  # e.g. "code:pain_point_count"
    passed: bool
    score: float  # 0.0–1.0
    details: str  # human-readable explanation
    agent: str = ""  # which agent this grades


@dataclass
class TrialResult:
    """Result of one trial (one run of all agents on one case)."""

    case_id: str
    trial_number: int
    pain_discovery: Any | None = None
    competitor_research: Any | None = None
    market_intelligence: Any | None = None
    graveyard_research: Any | None = None
    synthesis: Any | None = None
    grades: list[GradeResult] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0

    @property
    def passed(self) -> bool:
        """A trial passes if all grades pass."""
        return all(g.passed for g in self.grades) and self.error is None

    @property
    def score(self) -> float:
        """Average score across all grades."""
        if not self.grades:
            return 0.0
        return sum(g.score for g in self.grades) / len(self.grades)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "trial_number": self.trial_number,
            "passed": self.passed,
            "score": self.score,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "grades": [
                {
                    "grader": g.grader,
                    "agent": g.agent,
                    "passed": g.passed,
                    "score": g.score,
                    "details": g.details,
                }
                for g in self.grades
            ],
            "outputs": {
                "pain_discovery": _serialize(self.pain_discovery),
                "competitor_research": _serialize(self.competitor_research),
                "market_intelligence": _serialize(self.market_intelligence),
                "graveyard_research": _serialize(self.graveyard_research),
                "synthesis": _serialize(self.synthesis),
            },
        }


@dataclass
class EvalRun:
    """A complete eval run across all cases and trials."""

    started_at: str = ""
    cases: list[GoldenCase] = field(default_factory=list)
    trials: list[TrialResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.trials:
            return 0.0
        return sum(1 for t in self.trials if t.passed) / len(self.trials)

    def summary(self) -> dict[str, Any]:
        by_category: dict[str, list[TrialResult]] = {}
        for trial in self.trials:
            case = next((c for c in self.cases if c.id == trial.case_id), None)
            cat = case.category if case else "unknown"
            by_category.setdefault(cat, []).append(trial)

        return {
            "started_at": self.started_at,
            "total_trials": len(self.trials),
            "pass_rate": self.pass_rate,
            "avg_score": (
                sum(t.score for t in self.trials) / len(self.trials)
                if self.trials
                else 0.0
            ),
            "by_category": {
                cat: {
                    "trials": len(trials),
                    "pass_rate": sum(1 for t in trials if t.passed) / len(trials),
                    "avg_score": sum(t.score for t in trials) / len(trials),
                }
                for cat, trials in by_category.items()
            },
            "failed_cases": [
                {"case_id": t.case_id, "trial": t.trial_number, "error": t.error}
                for t in self.trials
                if not t.passed
            ],
        }

    def save(self, path: Path | None = None) -> Path:
        """Save full results to JSON."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = path or RESULTS_DIR / f"eval_{ts}.json"
        data = {
            "summary": self.summary(),
            "trials": [t.to_dict() for t in self.trials],
        }
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.info("Eval results saved to %s", path)
        return path


# ──────────────────────────────────────────────
# Loader
# ──────────────────────────────────────────────


def load_golden_cases(path: Path | None = None) -> list[GoldenCase]:
    """Load golden cases from YAML."""
    path = path or CASES_DIR / "golden_cases.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return [GoldenCase.from_dict(c) for c in data["cases"]]


# ──────────────────────────────────────────────
# Agent runner
# ──────────────────────────────────────────────


async def run_single_agent(agent_name: str, idea: str) -> Any:
    """Run a single agent with real LLM + search and return its output.

    This uses the real services — it costs money and takes time.
    """
    from maviriq.agents.competitor_research import CompetitorResearchAgent
    from maviriq.agents.graveyard_research import GraveyardResearchAgent
    from maviriq.agents.market_intelligence import MarketIntelligenceAgent
    from maviriq.agents.pain_discovery import PainDiscoveryAgent
    from maviriq.models.schemas import (
        CompetitorResearchInput,
        GraveyardResearchInput,
        MarketIntelligenceInput,
        PainDiscoveryInput,
    )
    from maviriq.services.llm import LLMService
    from maviriq.services.search import SerperService

    llm = LLMService()
    search = SerperService()

    if agent_name == "pain_discovery":
        agent = PainDiscoveryAgent(llm, search)
        return await agent.run(PainDiscoveryInput(idea=idea))
    elif agent_name == "competitor_research":
        agent = CompetitorResearchAgent(llm, search)
        return await agent.run(CompetitorResearchInput(idea=idea))
    elif agent_name == "market_intelligence":
        agent = MarketIntelligenceAgent(llm, search)
        return await agent.run(MarketIntelligenceInput(idea=idea))
    elif agent_name == "graveyard_research":
        agent = GraveyardResearchAgent(llm, search)
        return await agent.run(GraveyardResearchInput(idea=idea))
    else:
        raise ValueError(f"Unknown agent: {agent_name}")


async def run_full_pipeline(idea: str) -> TrialResult:
    """Run the full 5-agent pipeline on an idea and return raw outputs.

    Agents 1-4 run in pairs to stay within API rate limits, then synthesis
    runs on their combined output.
    """
    import time

    from maviriq.agents.synthesis import SynthesisAgent
    from maviriq.models.schemas import SynthesisInput
    from maviriq.services.llm import LLMService
    from maviriq.services.search import SerperService

    llm = LLMService()
    search = SerperService()

    trial = TrialResult(case_id="", trial_number=0)
    start = time.monotonic()

    try:
        # Run all 4 research agents in parallel.
        # Gemini's token limit (1M/min) can handle this; RPM retries are automatic.
        results = await asyncio.gather(
            run_single_agent("pain_discovery", idea),
            run_single_agent("competitor_research", idea),
            run_single_agent("market_intelligence", idea),
            run_single_agent("graveyard_research", idea),
            return_exceptions=True,
        )

        # Unpack, tolerating individual agent failures
        pain = results[0] if not isinstance(results[0], Exception) else None
        comp = results[1] if not isinstance(results[1], Exception) else None
        market = results[2] if not isinstance(results[2], Exception) else None
        grave = results[3] if not isinstance(results[3], Exception) else None

        if pain is None or comp is None:
            errors = []
            if isinstance(results[0], Exception):
                errors.append(f"pain_discovery: {results[0]}")
            if isinstance(results[1], Exception):
                errors.append(f"competitor_research: {results[1]}")
            trial.error = "; ".join(errors)
            trial.duration_seconds = time.monotonic() - start
            return trial

        trial.pain_discovery = pain
        trial.competitor_research = comp
        trial.market_intelligence = market
        trial.graveyard_research = grave

        # Backfill target_user on competitor output if needed
        if comp.target_user is None and pain.primary_target_user is not None:
            comp.target_user = pain.primary_target_user

        # Run synthesis
        synth_agent = SynthesisAgent(llm, search)
        synth_input = SynthesisInput(
            idea=idea,
            pain_discovery=pain,
            competitor_research=comp,
            market_intelligence=market,
            graveyard_research=grave,
        )
        trial.synthesis = await synth_agent.run(synth_input)

    except Exception as e:
        trial.error = str(e)
        logger.exception("Pipeline failed for idea: %s", idea)

    trial.duration_seconds = time.monotonic() - start
    return trial


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _serialize(obj: Any) -> Any:
    """Serialize a Pydantic model or None to a dict."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return str(obj)
