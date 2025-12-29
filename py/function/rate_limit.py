#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简易异步限流器。"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class RateLimiter:
    max_per_minute: Optional[int] = None
    max_per_day: Optional[int] = None
    name: str = "limiter"

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()
        self._events: list[float] = []

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def acquire(self) -> None:
        async with self._lock:
            now = time.time()
            self._trim(now)
            while not self._can_proceed(now):
                await asyncio.sleep(1)
                now = time.time()
                self._trim(now)
            self._events.append(now)

    def _trim(self, now: float) -> None:
        minute_ago = now - 60
        day_ago = now - 86400
        self._events = [t for t in self._events if t >= day_ago]
        # minute constraint implicitly handled in _can_proceed
        if self.max_per_minute is None:
            return
        self._events = [t for t in self._events if t >= minute_ago]

    def _can_proceed(self, now: float) -> bool:
        if self.max_per_minute is not None:
            minute_ago = now - 60
            recent_min = len([t for t in self._events if t >= minute_ago])
            if recent_min >= self.max_per_minute:
                return False
        if self.max_per_day is not None:
            day_ago = now - 86400
            recent_day = len([t for t in self._events if t >= day_ago])
            if recent_day >= self.max_per_day:
                return False
        return True


__all__ = ["RateLimiter"]
