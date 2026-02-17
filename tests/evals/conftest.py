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
def mock_supabase():
    """Override the root conftest mock — evals use the real Supabase client."""
    yield None


@pytest.fixture(autouse=True)
def require_eval_api_keys():
    """Skip eval tests if real API keys are not set.

    Evals use real LLM + search calls, so they need real keys.
    The regular test suite uses mocks and sets dummy keys.
    """
    # Root conftest sets fake env vars (SERPER_API_KEY=test-key etc.)
    # which override .env in pydantic-settings. Remove them temporarily
    # so Settings() reads the real keys from .env.
    saved = {}
    for key in ("SERPER_API_KEY", "ANTHROPIC_API_KEY", "SUPABASE_URL",
                "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"):
        if os.environ.get(key) == "test-key" or os.environ.get(key) == "https://test.supabase.co" or os.environ.get(key) == "test-service-role-key" or os.environ.get(key) == "test-jwt-secret":
            saved[key] = os.environ.pop(key)

    from maviriq.config import Settings

    real_settings = Settings()

    if real_settings.google_api_key in ("", "test-key"):
        os.environ.update(saved)
        pytest.skip("Evals require a real GOOGLE_API_KEY")
    if real_settings.serper_api_key in ("", "test-key"):
        os.environ.update(saved)
        pytest.skip("Evals require a real SERPER_API_KEY")

    # Set the real keys in the environment so all code picks them up
    os.environ["SERPER_API_KEY"] = real_settings.serper_api_key
    os.environ["ANTHROPIC_API_KEY"] = real_settings.anthropic_api_key
    os.environ["GOOGLE_API_KEY"] = real_settings.google_api_key
    os.environ["SUPABASE_URL"] = real_settings.supabase_url
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = real_settings.supabase_service_role_key

    # Reload the settings singleton so it picks up the real keys
    import maviriq.config
    maviriq.config.settings = real_settings

    # Reset the Supabase client so it reconnects with real credentials
    import maviriq.supabase_client
    maviriq.supabase_client._client = None
