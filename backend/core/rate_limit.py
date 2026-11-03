"""
Lightweight in-memory rate limiting for sensitive endpoints (login, password reset).

Usage:
    @router.post("/login", dependencies=[Depends(rate_limit(5, 60))])

Limits are per client IP and per route, inside a single process. When running
several API workers behind a proxy, start uvicorn with ``--proxy-headers`` so the
real client IP is used, and move this to Redis if you need a global limit.
"""
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Tuple

from fastapi import HTTPException, Request, status

_hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def rate_limit(max_requests: int, window_seconds: int) -> Callable:
    """Return a dependency that allows ``max_requests`` per ``window_seconds`` per IP."""

    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, request.url.path)
        now = time.monotonic()
        hits = _hits[key]

        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= max_requests:
            retry_after = int(window_seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)

    return dependency
