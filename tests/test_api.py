"""Tests for API endpoints."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from maverick.main import app
from maverick.models.schemas import ValidationRun, ValidationStatus
from maverick.storage.repository import ValidationRepository


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCreateValidation:
    def test_create_returns_run_id(self):
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


class TestGetValidation:
    @pytest.mark.asyncio
    async def test_get_existing_validation(self):
        # Insert a run directly into DB
        repo = ValidationRepository()
        run = ValidationRun(
            id="val_gettest001",
            idea="Test get endpoint",
            status=ValidationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        await repo.create(run)

        response = client.get("/api/validations/val_gettest001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "val_gettest001"
        assert data["idea"] == "Test get endpoint"

    def test_get_nonexistent_returns_404(self):
        response = client.get("/api/validations/val_doesnotexist")
        assert response.status_code == 404


class TestListValidations:
    @pytest.mark.asyncio
    async def test_list_empty(self):
        response = client.get("/api/validations")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == [] or isinstance(data["items"], list)
        assert data["page"] == 1
        assert data["per_page"] == 20

    @pytest.mark.asyncio
    async def test_list_with_items(self):
        repo = ValidationRepository()
        for i in range(3):
            run = ValidationRun(
                id=f"val_apilist{i:03d}",
                idea=f"API List Test {i}",
                status=ValidationStatus.PENDING,
            )
            await repo.create(run)

        response = client.get("/api/validations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_list_pagination(self):
        repo = ValidationRepository()
        for i in range(5):
            run = ValidationRun(
                id=f"val_apipage{i:03d}",
                idea=f"API Page Test {i}",
                status=ValidationStatus.PENDING,
            )
            await repo.create(run)

        response = client.get("/api/validations?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["per_page"] == 2


class TestDeleteValidation:
    @pytest.mark.asyncio
    async def test_delete_existing(self):
        repo = ValidationRepository()
        run = ValidationRun(
            id="val_deltest001",
            idea="Delete test",
            status=ValidationStatus.PENDING,
        )
        await repo.create(run)

        response = client.delete("/api/validations/val_deltest001")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify it's gone
        get_response = client.get("/api/validations/val_deltest001")
        assert get_response.status_code == 404

    def test_delete_nonexistent_returns_404(self):
        response = client.delete("/api/validations/val_doesnotexist")
        assert response.status_code == 404
