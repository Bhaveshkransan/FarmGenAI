"""
backend/middleware/rate_limiter.py

Sliding-window in-memory rate limiter middleware.
Default: 60 requests / 60 seconds per IP.
"""

import time
import logging
from collections import defaultdict, deque
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("RateLimiter")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # {ip: deque of timestamps}
        self._buckets: dict = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static paths
        if request.url.path in ("/health", "/", "/docs", "/openapi.json"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._buckets[ip]

        # Evict old timestamps outside sliding window
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded. Try again shortly.",
                },
            )

        bucket.append(now)
        return await call_next(request)

