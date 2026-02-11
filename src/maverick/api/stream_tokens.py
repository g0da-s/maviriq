"""One-time tokens for SSE stream authentication.

Instead of passing the full JWT as a query parameter (which leaks into logs,
browser history, and referrer headers), the frontend exchanges its JWT for a
short-lived, single-use token scoped to a specific validation run.

Uses Redis when REDIS_URL is configured, otherwise falls back to in-memory.
"""

import logging
import secrets
import time

logger = logging.getLogger(__name__)

_TOKEN_TTL_SECONDS = 30


# ---------------------------------------------------------------------------
# In-memory fallback (single-worker / local dev only)
# ---------------------------------------------------------------------------

class _InMemoryTokenStore:
    def __init__(self) -> None:
        # token -> (user_id, run_id, expires_at)
        self._tokens: dict[str, tuple[str, str, float]] = {}

    def create(self, user_id: str, run_id: str) -> str:
        self._cleanup()
        token = secrets.token_urlsafe(32)
        self._tokens[token] = (user_id, run_id, time.monotonic() + _TOKEN_TTL_SECONDS)
        return token

    def consume(self, token: str, run_id: str) -> str | None:
        """Validate and consume a one-time token. Returns user_id or None."""
        self._cleanup()
        entry = self._tokens.pop(token, None)
        if entry is None:
            return None
        user_id, token_run_id, expires_at = entry
        if time.monotonic() > expires_at:
            return None
        if token_run_id != run_id:
            return None
        return user_id

    def _cleanup(self) -> None:
        now = time.monotonic()
        expired = [t for t, (_, _, exp) in self._tokens.items() if now > exp]
        for t in expired:
            del self._tokens[t]


# ---------------------------------------------------------------------------
# Redis-backed store (works across workers, auto-expires via TTL)
# ---------------------------------------------------------------------------

class _RedisTokenStore:
    def __init__(self, redis_url: str) -> None:
        import redis

        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._redis.ping()
        logger.info("Stream token store connected to Redis")

    def create(self, user_id: str, run_id: str) -> str:
        token = secrets.token_urlsafe(32)
        key = f"stok:{token}"
        # Store as "user_id:run_id", Redis TTL handles expiration
        self._redis.set(key, f"{user_id}:{run_id}", ex=_TOKEN_TTL_SECONDS)
        return token

    def consume(self, token: str, run_id: str) -> str | None:
        """Validate and consume a one-time token. Returns user_id or None."""
        key = f"stok:{token}"
        # GETDEL is atomic: fetch and delete in one operation (single-use)
        value = self._redis.getdel(key)
        if value is None:
            return None
        stored_user_id, stored_run_id = value.split(":", 1)
        if stored_run_id != run_id:
            return None
        return stored_user_id


# ---------------------------------------------------------------------------
# Singleton initialisation
# ---------------------------------------------------------------------------

def _create_store() -> _InMemoryTokenStore | _RedisTokenStore:
    from maverick.config import settings

    if settings.redis_url:
        try:
            return _RedisTokenStore(settings.redis_url)
        except Exception:
            logger.warning("Failed to connect to Redis — falling back to in-memory stream token store")
    return _InMemoryTokenStore()


stream_token_store = _create_store()
