"""Eval-specific pytest configuration.

Adds:
  --trials=N      Run each case N times for consistency checking (default: 1)
  --eval-case=ID  Run only a specific case by ID
  --category=CAT  Run only cases in a specific category
  --skip-model    Skip model-based graders (faster, cheaper)
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--trials",
        action="store",
        default="1",
        help="Number of trials per case for consistency checking",
    )
    parser.addoption(
        "--eval-case",
        action="store",
        default=None,
        help="Run only a specific case by ID",
    )
    parser.addoption(
        "--category",
        action="store",
        default=None,
        help="Run only cases in a specific category",
    )
    parser.addoption(
        "--skip-model",
        action="store_true",
        default=False,
        help="Skip model-based graders (faster and cheaper)",
    )


@pytest.fixture(scope="session")
def num_trials(request: pytest.FixtureRequest) -> int:
    return int(request.config.getoption("--trials"))


@pytest.fixture(scope="session")
def eval_case_filter(request: pytest.FixtureRequest) -> str | None:
    return request.config.getoption("--eval-case")


@pytest.fixture(scope="session")
def category_filter(request: pytest.FixtureRequest) -> str | None:
    return request.config.getoption("--category")


@pytest.fixture(scope="session")
def skip_model_graders(request: pytest.FixtureRequest) -> bool:
    return request.config.getoption("--skip-model")


@pytest.fixture(autouse=True)
def require_eval_api_keys():
    """Skip eval tests if real API keys are not set.

    Evals use real LLM + search calls, so they need real keys.
    The regular test suite uses mocks and sets dummy keys.
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    serper_key = os.environ.get("SERPER_API_KEY", "")

    if anthropic_key in ("", "test-key"):
        pytest.skip("Evals require a real ANTHROPIC_API_KEY")
    if serper_key in ("", "test-key"):
        pytest.skip("Evals require a real SERPER_API_KEY")
