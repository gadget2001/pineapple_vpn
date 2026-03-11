from __future__ import annotations

import time
from typing import Callable

import redis
from fastapi import Request, Response

from app.core.config import settings


class RateLimitMiddleware:
    def __init__(self, app: Callable):
        self.app = app
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"rl:{client_ip}:{path}:{int(time.time() // 60)}"

        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 60)

        if count > settings.rate_limit_per_minute:
            response = Response("Too Many Requests", status_code=429)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
