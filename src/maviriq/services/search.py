import asyncio
import logging

import httpx
from tenacity import before_sleep_log, retry, retry_if_exception, stop_after_attempt, wait_exponential

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

    async def search_reddit(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search Reddit via Serper site: query."""
        results = await self.search(f"site:reddit.com {query}", num_results)
        for r in results:
            r.source = "reddit"
        return results

    async def search_hackernews(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search Hacker News via Serper site: query."""
        results = await self.search(f"site:news.ycombinator.com {query}", num_results)
        for r in results:
            r.source = "hackernews"
        return results

    async def search_g2(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search G2 reviews via Serper site: query."""
        results = await self.search(f"site:g2.com {query}", num_results)
        for r in results:
            r.source = "g2"
        return results

    async def search_capterra(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search Capterra via Serper site: query."""
        results = await self.search(f"site:capterra.com {query}", num_results)
        for r in results:
            r.source = "capterra"
        return results

    async def search_twitter(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search Twitter/X via Serper site: query."""
        results = await self.search(f"site:x.com {query}", num_results)
        for r in results:
            r.source = "twitter"
        return results

    async def search_producthunt(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search Product Hunt via Serper site: query."""
        results = await self.search(f"site:producthunt.com {query}", num_results)
        for r in results:
            r.source = "producthunt"
        return results

    async def search_linkedin_jobs(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search LinkedIn Jobs via Serper site: query."""
        results = await self.search(f"site:linkedin.com/jobs {query}", num_results)
        for r in results:
            r.source = "linkedin_jobs"
        return results

    async def search_indiehackers(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search Indie Hackers via Serper site: query."""
        results = await self.search(f"site:indiehackers.com {query}", num_results)
        for r in results:
            r.source = "indiehackers"
        return results

    async def search_crunchbase(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search Crunchbase via Serper site: query."""
        results = await self.search(f"site:crunchbase.com {query}", num_results)
        for r in results:
            r.source = "crunchbase"
        return results

    async def search_youtube(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search YouTube via Serper site: query."""
        results = await self.search(f"site:youtube.com {query}", num_results)
        for r in results:
            r.source = "youtube"
        return results

    @retry(**_RETRY_POLICY)
    async def search_news(self, query: str, num_results: int = 10) -> list[SearchResult]:
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
            query, "serper_news", [r.to_dict() for r in results], settings.search_cache_ttl
        )

        return results

    async def multi_search(self, queries: list[str]) -> list[SearchResult]:
        """Run multiple searches in parallel, deduplicate results by URL."""
        tasks = [self.search(q) for q in queries]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        all_results: list[SearchResult] = []

        for result in results_lists:
            if isinstance(result, Exception):
                logger.warning(f"Search query failed: {result}")
                continue
            for r in result:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r)

        return all_results
