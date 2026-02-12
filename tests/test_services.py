"""Tests for LLM and Search services."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

from maviriq.services.llm import LLMService
from maviriq.services.search import SearchResult, SerperService


# ──────────────────────────────────────────────
# LLM Service Tests
# ──────────────────────────────────────────────

class TestLLMService:
    @pytest.fixture
    def llm(self):
        mock_model = MagicMock(name="model")
        mock_cheap = MagicMock(name="cheap_model")
        with patch("maviriq.services.llm.ChatAnthropic", side_effect=[mock_model, mock_cheap]):
            with patch("maviriq.services.llm.settings") as mock_settings:
                mock_settings.reasoning_model = "claude-sonnet-4-5-20250929"
                mock_settings.cheap_model = "claude-haiku-4-5-20251001"
                service = LLMService()
        return service

    @pytest.mark.asyncio
    async def test_generate_structured_returns_typed_output(self, llm):
        class TestOutput(BaseModel):
            name: str
            score: int

        expected = TestOutput(name="test", score=42)

        # LangChain: model.with_structured_output(schema).ainvoke(messages)
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=expected)
        llm.model.with_structured_output = MagicMock(return_value=mock_structured)

        result = await llm.generate_structured(
            system_prompt="test",
            user_prompt="test",
            output_schema=TestOutput,
        )

        assert isinstance(result, TestOutput)
        assert result.name == "test"
        assert result.score == 42
        llm.model.with_structured_output.assert_called_once_with(TestOutput)

    @pytest.mark.asyncio
    async def test_generate_structured_uses_cheap_model_when_requested(self, llm):
        class TestOutput(BaseModel):
            value: str

        expected = TestOutput(value="cheap")
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=expected)
        llm.cheap_model.with_structured_output = MagicMock(return_value=mock_structured)

        await llm.generate_structured(
            system_prompt="test",
            user_prompt="test",
            output_schema=TestOutput,
            use_cheap_model=True,
        )

        # Should have used cheap_model, not model
        llm.cheap_model.with_structured_output.assert_called_once_with(TestOutput)
        llm.model.with_structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_structured_retries_on_api_error(self, llm):
        from tenacity import RetryError
        from anthropic import APIConnectionError

        class TestOutput(BaseModel):
            value: str

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )
        llm.model.with_structured_output = MagicMock(return_value=mock_structured)

        with pytest.raises(RetryError):
            await llm.generate_structured(
                system_prompt="test",
                user_prompt="test",
                output_schema=TestOutput,
            )

        # Should have retried 3 times
        assert mock_structured.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_text(self, llm):
        mock_response = MagicMock()
        mock_response.content = "Hello world"
        llm.model.ainvoke = AsyncMock(return_value=mock_response)

        result = await llm.generate_text(
            system_prompt="test",
            user_prompt="test",
        )

        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_generate_list(self, llm):
        # generate_list calls generate_structured internally with ListOutput schema
        from pydantic import BaseModel as _BM

        class ListOutput(_BM):
            items: list[str]

        expected = ListOutput(items=["query1", "query2", "query3"])
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=expected)
        llm.cheap_model.with_structured_output = MagicMock(return_value=mock_structured)

        result = await llm.generate_list(
            system_prompt="test",
            user_prompt="test",
        )

        assert result == ["query1", "query2", "query3"]


# ──────────────────────────────────────────────
# Search Service Tests
# ──────────────────────────────────────────────

class TestSearchResult:
    def test_to_dict(self):
        r = SearchResult(title="Test", url="https://example.com", snippet="A snippet")
        d = r.to_dict()
        assert d == {
            "title": "Test",
            "url": "https://example.com",
            "snippet": "A snippet",
            "source": "google",
        }

    def test_custom_source(self):
        r = SearchResult(title="Test", url="https://example.com", snippet="A snippet", source="reddit")
        assert r.source == "reddit"


class TestSerperService:
    @pytest.fixture
    def serper(self):
        with patch("maviriq.services.search.settings") as mock_settings:
            mock_settings.serper_api_key = "test-key"
            mock_settings.serper_base_url = "https://google.serper.dev"
            mock_settings.serper_max_concurrent = 10
            mock_settings.search_cache_ttl = 86400
            service = SerperService()
            # Mock the cache to always miss (no DB needed for unit test)
            service.cache = MagicMock()
            service.cache.get = AsyncMock(return_value=None)
            service.cache.set = AsyncMock()
            return service

    @pytest.mark.asyncio
    async def test_search_parses_serper_response(self, serper):
        mock_response_data = {
            "organic": [
                {"title": "Result 1", "link": "https://example.com/1", "snippet": "Snippet 1"},
                {"title": "Result 2", "link": "https://example.com/2", "snippet": "Snippet 2"},
            ]
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            results = await serper.search("test query")

        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example.com/1"
        assert results[0].source == "google"

    @pytest.mark.asyncio
    async def test_search_reddit_sets_source(self, serper):
        mock_response_data = {
            "organic": [
                {"title": "Reddit Post", "link": "https://reddit.com/r/test/123", "snippet": "Reddit snippet"},
            ]
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            results = await serper.search_reddit("test query")

        assert len(results) == 1
        assert results[0].source == "reddit"

    @pytest.mark.asyncio
    async def test_search_uses_cache_when_available(self, serper):
        cached_data = [
            {"title": "Cached", "url": "https://cached.com", "snippet": "From cache", "source": "google"}
        ]
        serper.cache.get = AsyncMock(return_value=cached_data)

        results = await serper.search("cached query")

        assert len(results) == 1
        assert results[0].title == "Cached"
        # Should not have made an HTTP call
        serper.cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_handles_empty_response(self, serper):
        mock_response_data = {"organic": []}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client

            results = await serper.search("empty query")

        assert results == []

    @pytest.mark.asyncio
    async def test_multi_search_deduplicates(self, serper):
        call_count = 0

        async def mock_search(query, num_results=10):
            nonlocal call_count
            call_count += 1
            # Return overlapping results
            return [
                SearchResult(title="Same", url="https://same.com", snippet="same"),
                SearchResult(title=f"Unique {call_count}", url=f"https://unique{call_count}.com", snippet="unique"),
            ]

        serper.search = mock_search
        results = await serper.multi_search(["q1", "q2", "q3"])

        # Should have 4 unique URLs: 1 shared + 3 unique
        urls = [r.url for r in results]
        assert len(urls) == len(set(urls))  # No duplicates
        assert "https://same.com" in urls
