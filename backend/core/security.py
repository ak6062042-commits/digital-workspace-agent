"""Local API authentication, bounded request bodies, and in-memory rate limiting."""
from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.core.config import settings


class LocalRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= settings.rate_limit_per_minute:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        hits.append(now)


limiter = LocalRateLimiter()


async def require_api_token(
    request: Request,
    x_workspace_token: str | None = Header(default=None),
) -> None:
    supplied = x_workspace_token or ""
    if not hmac.compare_digest(supplied, settings.api_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid X-Workspace-Token required")
    client = request.client.host if request.client else "unknown"
    limiter.check(client)


async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.request_max_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": "Request body too large"},
        )
    return await call_next(request)
