"""Tests for API endpoints with mocked Supabase auth."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from maverick.main import app
from maverick.api.dependencies import get_current_user
from tests.conftest import FAKE_USER


def _result(data=None, count=None):
    return SimpleNamespace(data=data or [], count=count)


# Override get_current_user for all tests in this module
@pytest.fixture(autouse=True)
def override_auth():
    """Override the FastAPI auth dependency so requests don't need real JWTs."""
    async def fake_user():
        return FAKE_USER

    app.dependency_overrides[get_current_user] = fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCreateValidation:
    def test_create_returns_run_id(self, mock_supabase):
        # Mock deduct_credit RPC to return True
        mock_supabase.execute = AsyncMock(return_value=_result(data=True))

        with patch("maverick.api.routes._run_pipeline_background", new_callable=AsyncMock):
            response = client.post(
                "/api/validations",
                json={"idea": "AI pitch deck generator"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("val_")
        assert data["idea"] == "AI pitch deck generator"
        assert data["status"] == "running"
        assert "/stream" in data["stream_url"]

    def test_create_rejects_short_idea(self):
        response = client.post("/api/validations", json={"idea": "ab"})
        assert response.status_code == 422

    def test_create_rejects_empty_body(self):
        response = client.post("/api/validations", json={})
        assert response.status_code == 422

    def test_create_rejects_long_idea(self):
        response = client.post("/api/validations", json={"idea": "x" * 501})
        assert response.status_code == 422

    def test_create_returns_402_when_no_credits(self, mock_supabase):
        # Mock deduct_credit RPC to return False (insufficient credits)
        mock_supabase.execute = AsyncMock(return_value=_result(data=False))

        response = client.post(
            "/api/validations",
            json={"idea": "AI pitch deck generator"},
        )
        assert response.status_code == 402


class TestGetValidation:
    def test_get_existing_validation(self, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(data={
                "id": "val_gettest001",
                "idea": "Test get endpoint",
                "status": "running",
                "current_agent": 0,
                "started_at": "2025-01-01T00:00:00+00:00",
                "completed_at": None,
                "error": None,
                "pain_discovery_output": None,
                "competitor_research_output": None,
                "viability_output": None,
                "synthesis_output": None,
                "total_cost_cents": 0,
                "user_id": FAKE_USER["id"],
            })
        )

        response = client.get("/api/validations/val_gettest001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "val_gettest001"
        assert data["idea"] == "Test get endpoint"

    def test_get_nonexistent_returns_404(self, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=None))

        response = client.get("/api/validations/val_doesnotexist")
        assert response.status_code == 404


class TestListValidations:
    def test_list_empty(self, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=[], count=0))

        response = client.get("/api/validations")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["page"] == 1
        assert data["per_page"] == 20

    def test_list_with_items(self, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(
                data=[
                    {"id": f"val_apilist{i:03d}", "idea": f"API List Test {i}", "status": "pending", "synthesis_output": None, "created_at": "2025-01-01T00:00:00+00:00"}
                    for i in range(3)
                ],
                count=3,
            )
        )

        response = client.get("/api/validations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_list_pagination(self, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(
                data=[
                    {"id": f"val_apipage{i:03d}", "idea": f"API Page Test {i}", "status": "pending", "synthesis_output": None, "created_at": "2025-01-01T00:00:00+00:00"}
                    for i in range(2)
                ],
                count=5,
            )
        )

        response = client.get("/api/validations?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["per_page"] == 2


class TestDeleteValidation:
    def test_delete_existing(self, mock_supabase):
        # First call: repo.get() returns the run (ownership check)
        # Second call: repo.delete() returns data
        call_count = 0
        async def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # get() call — returns the validation
                return _result(data={
                    "id": "val_deltest001",
                    "idea": "Delete test",
                    "status": "pending",
                    "current_agent": 0,
                    "started_at": None,
                    "completed_at": None,
                    "error": None,
                    "pain_discovery_output": None,
                    "competitor_research_output": None,
                    "viability_output": None,
                    "synthesis_output": None,
                    "total_cost_cents": 0,
                    "user_id": FAKE_USER["id"],
                })
            else:
                # delete() call
                return _result(data=[{"id": "val_deltest001"}])

        mock_supabase.execute = AsyncMock(side_effect=side_effect)

        response = client.delete("/api/validations/val_deltest001")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_nonexistent_returns_404(self, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=None))

        response = client.delete("/api/validations/val_doesnotexist")
        assert response.status_code == 404


class TestAuthMe:
    def test_me_returns_user(self):
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == FAKE_USER["id"]
        assert data["email"] == FAKE_USER["email"]
        assert data["credits"] == FAKE_USER["credits"]
