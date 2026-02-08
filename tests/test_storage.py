"""Tests for repository layer with mocked Supabase client."""
import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock

from maverick.models.schemas import ValidationRun, ValidationStatus
from maverick.storage.repository import SearchCacheRepository, ValidationRepository


def _result(data=None, count=None):
    return SimpleNamespace(data=data or [], count=count)


class TestValidationRepository:
    @pytest.fixture
    def repo(self):
        return ValidationRepository()

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_supabase):
        run = ValidationRun(
            id="val_test001",
            idea="Test idea",
            status=ValidationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            user_id="user-123",
        )
        await repo.create(run)

        mock_supabase.table.assert_called_with("validation_runs")
        mock_supabase.insert.assert_called_once()
        insert_arg = mock_supabase.insert.call_args[0][0]
        assert insert_arg["id"] == "val_test001"
        assert insert_arg["idea"] == "Test idea"
        assert insert_arg["status"] == "running"
        assert insert_arg["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_get_existing(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(data={
                "id": "val_test001",
                "idea": "Test idea",
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
                "user_id": "user-123",
            })
        )

        result = await repo.get("val_test001")
        assert result is not None
        assert result.id == "val_test001"
        assert result.idea == "Test idea"
        assert result.status == ValidationStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=None))

        result = await repo.get("val_doesnotexist")
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repo, mock_supabase):
        run = ValidationRun(
            id="val_test002",
            idea="Update test",
            status=ValidationStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            current_agent=4,
        )
        await repo.update(run)

        mock_supabase.table.assert_called_with("validation_runs")
        mock_supabase.update.assert_called_once()
        update_arg = mock_supabase.update.call_args[0][0]
        assert update_arg["status"] == "completed"
        assert update_arg["current_agent"] == 4
        assert update_arg["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_update_with_agent_outputs(self, repo, mock_supabase, sample_pain_discovery):
        run = ValidationRun(
            id="val_test003",
            idea="Output test",
            status=ValidationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            current_agent=1,
            pain_discovery=sample_pain_discovery,
        )
        await repo.update(run)

        update_arg = mock_supabase.update.call_args[0][0]
        assert update_arg["pain_discovery_output"] is not None
        assert update_arg["pain_discovery_output"]["idea"] == "AI pitch deck generator"

    @pytest.mark.asyncio
    async def test_delete_existing(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(data=[{"id": "val_test004"}])
        )

        deleted = await repo.delete("val_test004")
        assert deleted is True
        mock_supabase.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=[]))

        deleted = await repo.delete("val_doesnotexist")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_empty(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=[], count=0))

        items, total = await repo.list()
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_list_with_items(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(
                data=[
                    {"id": f"val_list{i:03d}", "idea": f"Idea {i}", "status": "pending", "synthesis_output": None, "created_at": "2025-01-01T00:00:00+00:00"}
                    for i in range(3)
                ],
                count=3,
            )
        )

        items, total = await repo.list()
        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_list_pagination(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(
                data=[
                    {"id": f"val_page{i:03d}", "idea": f"Idea {i}", "status": "pending", "synthesis_output": None, "created_at": "2025-01-01T00:00:00+00:00"}
                    for i in range(2)
                ],
                count=5,
            )
        )

        items, total = await repo.list(page=1, per_page=2)
        assert total == 5
        assert len(items) == 2
        mock_supabase.range.assert_called_with(0, 1)

    @pytest.mark.asyncio
    async def test_list_includes_verdict_from_synthesis(self, repo, mock_supabase, sample_synthesis):
        mock_supabase.execute = AsyncMock(
            return_value=_result(
                data=[{
                    "id": "val_verdict001",
                    "idea": "Verdict test",
                    "status": "completed",
                    "synthesis_output": sample_synthesis.model_dump(),
                    "created_at": "2025-01-01T00:00:00+00:00",
                }],
                count=1,
            )
        )

        items, total = await repo.list()
        assert total == 1
        assert items[0].verdict is not None
        assert items[0].verdict.value == "BUILD"
        assert items[0].confidence == sample_synthesis.confidence

    @pytest.mark.asyncio
    async def test_list_filters_by_user_id(self, repo, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=[], count=0))

        await repo.list(user_id="user-123")
        # eq should be called with user_id filter
        mock_supabase.eq.assert_called_with("user_id", "user-123")


class TestSearchCacheRepository:
    @pytest.fixture
    def cache(self):
        return SearchCacheRepository()

    @pytest.mark.asyncio
    async def test_set(self, cache, mock_supabase):
        data = {"results": [{"title": "Cached result"}]}
        await cache.set("test query", "serper", data, ttl_seconds=3600)

        mock_supabase.table.assert_called_with("search_cache")
        mock_supabase.upsert.assert_called_once()
        upsert_arg = mock_supabase.upsert.call_args[0][0]
        assert upsert_arg["query"] == "test query"
        assert upsert_arg["source"] == "serper"
        assert upsert_arg["response"] == data

    @pytest.mark.asyncio
    async def test_get_hit(self, cache, mock_supabase):
        cached_data = {"results": [{"title": "Cached result"}]}
        mock_supabase.execute = AsyncMock(
            return_value=_result(data={"response": cached_data})
        )

        result = await cache.get("test query", "serper")
        assert result is not None
        assert result["results"][0]["title"] == "Cached result"

    @pytest.mark.asyncio
    async def test_get_miss(self, cache, mock_supabase):
        mock_supabase.execute = AsyncMock(return_value=_result(data=None))

        result = await cache.get("nonexistent query", "serper")
        assert result is None

    @pytest.mark.asyncio
    async def test_different_sources_use_different_hashes(self, cache):
        hash1 = cache._hash("same query", "serper")
        hash2 = cache._hash("same query", "reddit")
        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache, mock_supabase):
        mock_supabase.execute = AsyncMock(
            return_value=_result(data=[{"id": 1}, {"id": 2}])
        )

        deleted = await cache.cleanup_expired()
        assert deleted == 2
        mock_supabase.delete.assert_called_once()
