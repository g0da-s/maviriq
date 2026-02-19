import asyncio
import logging

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from maviriq.config import settings
from maviriq.storage.repository import SearchCacheRepository

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on transient errors: timeouts, connection failures, 429, 5xx."""
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False


_RETRY_POLICY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception(_is_retryable),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)


class SearchResult:
    def __init__(self, title: str, url: str, snippet: str, source: str = "google"):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
        }


class SerperService:
    def __init__(self) -> None:
        self.api_key = settings.serper_api_key
        self.base_url = settings.serper_base_url
        self._semaphore = asyncio.Semaphore(settings.serper_max_concurrent)
        self.cache = SearchCacheRepository()

    @retry(**_RETRY_POLICY)
    async def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        # Check cache first
        cached = await self.cache.get(query, "serper")
        if cached:
            logger.debug(f"Cache hit for query: {query}")
            return [SearchResult(**r) for r in cached]

        async with self._semaphore:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={"q": query, "num": num_results},
                )
                response.raise_for_status()
                data = response.json()

        results = []
        for item in data.get("organic", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="google",
                )
            )

        # Cache results
        await self.cache.set(
            query, "serper", [r.to_dict() for r in results], settings.search_cache_ttl
        )

        return results

    async def _site_search(
        self, site: str, source: str, query: str, num_results: int = 10
    ) -> list[SearchResult]:
        """Search a specific site via Serper site: query."""
        results = await self.search(f"site:{site} {query}", num_results)
        for r in results:
            r.source = source
        return results

    # Site-specific search methods — used by agent tool executors via getattr()
    async def search_reddit(
        self, query: str, num_results: int = 10
    ) -> list[SearchResult]:
        return await self._site_search("reddit.com", "reddit", query, num_results)

    async def search_hackernews(
        self, query: str, num_results: int = 10
    ) -> list[SearchResult]:
        return await self._site_search(
            "news.ycombinator.com", "hackernews", query, num_results
        )

    async def search_g2(self, query: str, num_results: int = 5) -> list[SearchResult]:
        return await self._site_search("g2.com", "g2", query, num_results)

    async def search_capterra(
        self, query: str, num_results: int = 5
    ) -> list[SearchResult]:
        return await self._site_search("capterra.com", "capterra", query, num_results)

    async def search_producthunt(
        self, query: str, num_results: int = 10
    ) -> list[SearchResult]:
        return await self._site_search(
            "producthunt.com", "producthunt", query, num_results
        )

    async def search_indiehackers(
        self, query: str, num_results: int = 10
    ) -> list[SearchResult]:
        return await self._site_search(
            "indiehackers.com", "indiehackers", query, num_results
        )

    async def search_crunchbase(
        self, query: str, num_results: int = 5
    ) -> list[SearchResult]:
        return await self._site_search(
            "crunchbase.com", "crunchbase", query, num_results
        )

    @retry(**_RETRY_POLICY)
    async def search_news(
        self, query: str, num_results: int = 10
    ) -> list[SearchResult]:
        """Search Google News via Serper /news endpoint."""
        cached = await self.cache.get(query, "serper_news")
        if cached:
            logger.debug(f"Cache hit for news query: {query}")
            return [SearchResult(**r) for r in cached]

        async with self._semaphore:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/news",
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={"q": query, "num": num_results},
                )
                response.raise_for_status()
                data = response.json()

        results = []
        for item in data.get("news", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="google_news",
                )
            )

        await self.cache.set(
            query,
            "serper_news",
            [r.to_dict() for r in results],
            settings.search_cache_ttl,
        )

        return results

    @retry(**_RETRY_POLICY)
    async def scrape_url(self, url: str) -> str:
        """Scrape a URL and return its text content (via Serper /scrape)."""
        cached = await self.cache.get(url, "serper_scrape")
        if cached:
            logger.debug(f"Cache hit for scrape: {url}")
            return cached if isinstance(cached, str) else cached[0]

        async with self._semaphore:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={"url": url},
                )
                response.raise_for_status()
                data = response.json()

        text = data.get("text", "")
        # Truncate to avoid blowing up context
        if len(text) > 8000:
            text = text[:8000] + "\n\n[...truncated]"

        await self.cache.set(url, "serper_scrape", [text], settings.search_cache_ttl)
        return text
