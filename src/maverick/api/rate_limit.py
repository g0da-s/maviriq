"""Rate limiter for auth and validation endpoints.

Uses Redis (sorted-set sliding window) when REDIS_URL is configured,
otherwise falls back to an in-memory implementation for local development.
"""

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory fallback (single-worker / local dev only)
# ---------------------------------------------------------------------------

class _InMemoryLimiter:
    """Sliding window rate limiter stored in process memory."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds

        hits = self._hits[key]
        self._hits[key] = [t for t in hits if t > cutoff]

        if len(self._hits[key]) >= max_requests:
            logger.warning("Rate limit hit: %s (%d/%d in %ds)", key, max_requests, max_requests, window_seconds)
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {window_seconds} seconds.",
            )
        self._hits[key].append(now)


# ---------------------------------------------------------------------------
# Redis-backed limiter (works across workers and survives restarts)
# ---------------------------------------------------------------------------

class _RedisLimiter:
    """Sliding window rate limiter backed by Redis sorted sets."""

    def __init__(self, redis_url: str) -> None:
        import redis

        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        # Verify connection on startup
        self._redis.ping()
        logger.info("Rate limiter connected to Redis")

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.time()
        cutoff = now - window_seconds
        rkey = f"rl:{key}"

        pipe = self._redis.pipeline(transaction=True)
        pipe.zremrangebyscore(rkey, "-inf", cutoff)
        pipe.zcard(rkey)
        pipe.zadd(rkey, {f"{now}": now})
        pipe.expire(rkey, window_seconds)
        results = pipe.execute()

        current_count = results[1]  # zcard result (before adding current)
        if current_count >= max_requests:
            # Remove the entry we just added since we're rejecting
            self._redis.zrem(rkey, f"{now}")
            logger.warning("Rate limit hit: %s (%d/%d in %ds)", key, max_requests, max_requests, window_seconds)
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {window_seconds} seconds.",
            )


# ---------------------------------------------------------------------------
# Singleton initialisation
# ---------------------------------------------------------------------------

def _create_limiter() -> _InMemoryLimiter | _RedisLimiter:
    from maverick.config import settings

    if settings.redis_url:
        try:
            return _RedisLimiter(settings.redis_url)
        except Exception:
            logger.warning("Failed to connect to Redis — falling back to in-memory rate limiter", exc_info=True)
    return _InMemoryLimiter()


_limiter = _create_limiter()


# ---------------------------------------------------------------------------
# Public helpers (unchanged interface)
# ---------------------------------------------------------------------------

def _get_client_ip(request: Request) -> str:
    # Railway/Render set the real client IP as the rightmost entry in
    # X-Forwarded-For. The leftmost entries can be spoofed by the client.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_auth(request: Request) -> None:
    """Limit auth attempts: 10 per minute per IP to prevent brute force."""
    ip = _get_client_ip(request)
    _limiter.check(f"auth:{ip}", 10, 60)


def rate_limit_register(request: Request) -> None:
    """Limit account creation: 1 per hour per IP to prevent free-credit farming."""
    ip = _get_client_ip(request)
    _limiter.check(f"register:{ip}", 1, 3600)


def rate_limit_validation(user_id: str) -> None:
    """Limit validations: 5 per hour per user to protect LLM API costs."""
    _limiter.check(f"validation:{user_id}", 5, 3600)
