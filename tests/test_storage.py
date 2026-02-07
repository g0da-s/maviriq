"""Tests for database storage and repository layer."""
import pytest
from datetime import datetime, timezone

from maverick.models.schemas import ValidationRun, ValidationStatus
from maverick.storage.repository import SearchCacheRepository, ValidationRepository


class TestValidationRepository:
    @pytest.fixture
    def repo(self):
        return ValidationRepository()

    @pytest.mark.asyncio
    async def test_create_and_get(self, repo):
        run = ValidationRun(
            id="val_test001",
            idea="Test idea",
            status=ValidationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        await repo.create(run)

        fetched = await repo.get("val_test001")
        assert fetched is not None
        assert fetched.id == "val_test001"
        assert fetched.idea == "Test idea"
        assert fetched.status == ValidationStatus.RUNNING

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get("val_doesnotexist")
        assert result is None

    @pytest.mark.asyncio
    async def test_update(self, repo):
        run = ValidationRun(
            id="val_test002",
            idea="Update test",
            status=ValidationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        await repo.create(run)

        run.status = ValidationStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        run.current_agent = 4
        await repo.update(run)

        fetched = await repo.get("val_test002")
        assert fetched is not None
        assert fetched.status == ValidationStatus.COMPLETED
        assert fetched.current_agent == 4
        assert fetched.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_with_agent_outputs(self, repo, sample_pain_discovery):
        run = ValidationRun(
            id="val_test003",
            idea="Output test",
            status=ValidationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        await repo.create(run)

        run.pain_discovery = sample_pain_discovery
        run.current_agent = 1
        await repo.update(run)

        fetched = await repo.get("val_test003")
        assert fetched is not None
        assert fetched.pain_discovery is not None
        assert fetched.pain_discovery.idea == sample_pain_discovery.idea
        assert len(fetched.pain_discovery.pain_points) == len(sample_pain_discovery.pain_points)

    @pytest.mark.asyncio
    async def test_delete(self, repo):
        run = ValidationRun(
            id="val_test004",
            idea="Delete test",
            status=ValidationStatus.PENDING,
        )
        await repo.create(run)

        deleted = await repo.delete("val_test004")
        assert deleted is True

        fetched = await repo.get("val_test004")
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo):
        deleted = await repo.delete("val_doesnotexist")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_empty(self, repo):
        items, total = await repo.list()
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_list_with_items(self, repo):
        for i in range(3):
            run = ValidationRun(
                id=f"val_list{i:03d}",
                idea=f"Idea {i}",
                status=ValidationStatus.PENDING,
            )
            await repo.create(run)

        items, total = await repo.list()
        assert total == 3
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_list_pagination(self, repo):
        for i in range(5):
            run = ValidationRun(
                id=f"val_page{i:03d}",
                idea=f"Idea {i}",
                status=ValidationStatus.PENDING,
            )
            await repo.create(run)

        items, total = await repo.list(page=1, per_page=2)
        assert total == 5
        assert len(items) == 2

        items2, total2 = await repo.list(page=2, per_page=2)
        assert total2 == 5
        assert len(items2) == 2

        # Page 3 should have 1 item
        items3, total3 = await repo.list(page=3, per_page=2)
        assert total3 == 5
        assert len(items3) == 1

    @pytest.mark.asyncio
    async def test_list_includes_verdict_from_synthesis(self, repo, sample_synthesis):
        run = ValidationRun(
            id="val_verdict001",
            idea="Verdict test",
            status=ValidationStatus.COMPLETED,
            synthesis=sample_synthesis,
        )
        await repo.create(run)
        run.synthesis = sample_synthesis
        await repo.update(run)

        items, total = await repo.list()
        assert total == 1
        assert items[0].verdict is not None
        assert items[0].verdict.value == "BUILD"
        assert items[0].confidence == sample_synthesis.confidence


class TestSearchCacheRepository:
    @pytest.fixture
    def cache(self):
        return SearchCacheRepository()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        data = {"results": [{"title": "Cached result"}]}
        await cache.set("test query", "serper", data, ttl_seconds=3600)

        result = await cache.get("test query", "serper")
        assert result is not None
        assert result["results"][0]["title"] == "Cached result"

    @pytest.mark.asyncio
    async def test_get_miss(self, cache):
        result = await cache.get("nonexistent query", "serper")
        assert result is None

    @pytest.mark.asyncio
    async def test_different_sources_are_separate(self, cache):
        await cache.set("same query", "serper", {"source": "serper"})
        await cache.set("same query", "reddit", {"source": "reddit"})

        serper_result = await cache.get("same query", "serper")
        reddit_result = await cache.get("same query", "reddit")

        assert serper_result["source"] == "serper"
        assert reddit_result["source"] == "reddit"

    @pytest.mark.asyncio
    async def test_expired_cache_returns_none(self, cache):
        import asyncio
        # Set with 1s TTL then wait for it to expire
        await cache.set("expired query", "serper", {"data": "old"}, ttl_seconds=1)
        await asyncio.sleep(1.5)

        result = await cache.get("expired query", "serper")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache):
        import asyncio
        # Set entries with 1s TTL
        await cache.set("expired1", "serper", {"data": "old"}, ttl_seconds=1)
        await cache.set("expired2", "serper", {"data": "old"}, ttl_seconds=1)
        # Set valid entry
        await cache.set("valid", "serper", {"data": "fresh"}, ttl_seconds=3600)

        await asyncio.sleep(1.5)

        deleted = await cache.cleanup_expired()
        assert deleted >= 2

        # Valid entry should still exist
        result = await cache.get("valid", "serper")
        assert result is not None
