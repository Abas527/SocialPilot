"""Small in-process sliding-window rate limiter.

Good enough for a single-process deployment. Behind several workers/instances,
swap `_hits` for Redis (or enforce limits at the proxy, see deploy/Caddyfile).
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from config import settings

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def reset() -> None:
    with _lock:
        _hits.clear()


def _client_ip(request: Request) -> str:
    # Trust X-Forwarded-For only when explicitly running behind a proxy.
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(key: str, limit: int, window_s: int) -> None:
    """Record one hit for `key`; raise 429 when over `limit` per `window_s`."""
    if not settings.rate_limit_enabled or limit <= 0:
        return
    now = time.monotonic()
    with _lock:
        hits = _hits[key]
        while hits and now - hits[0] >= window_s:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, int(window_s - (now - hits[0])) + 1)
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)


def limit_by_ip(name: str, limit: int, window_s: int = 60):
    """Dependency: limit unauthenticated endpoints per client IP."""

    def dependency(request: Request) -> None:
        check(f"{name}:ip:{_client_ip(request)}", limit, window_s)

    return dependency


def limit_by_user(name: str, limit: int, window_s: int = 60):
    """Dependency: limit authenticated endpoints per user."""
    from api.dependencies import require_auth

    def dependency(user: dict = Depends(require_auth)) -> None:
        check(f"{name}:user:{user['user_id']}", limit, window_s)

    return dependency
