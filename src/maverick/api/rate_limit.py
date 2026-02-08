"""Simple in-memory rate limiter for auth endpoints.

Prevents brute-force password guessing. Validation endpoints
don't need rate limiting — the credit system handles that.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding window rate limiter keyed by arbitrary string."""

    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        """Raise 429 if key has exceeded max_requests in the last window_seconds."""
        now = time.monotonic()
        cutoff = now - window_seconds

        hits = self._hits[key]
        self._hits[key] = [t for t in hits if t > cutoff]

        if len(self._hits[key]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again in {window_seconds} seconds.",
            )

        self._hits[key].append(now)


_limiter = RateLimiter()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_auth(request: Request) -> None:
    """Limit auth attempts: 10 per minute per IP to prevent brute force."""
    ip = _get_client_ip(request)
    _limiter.check(f"auth:{ip}", 10, 60)


def rate_limit_register(request: Request) -> None:
    """Limit account creation: 1 per hour per IP to prevent free-credit farming."""
    ip = _get_client_ip(request)
    _limiter.check(f"register:{ip}", 1, 3600)
