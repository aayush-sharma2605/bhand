from __future__ import annotations

import asyncio
import time


class AsyncRateLimiter:
    def __init__(self, rate_per_second: int) -> None:
        self.rate_per_second = max(rate_per_second, 1)
        self._lock = asyncio.Lock()
        self._last_called = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            min_interval = 1 / self.rate_per_second
            delta = now - self._last_called
            if delta < min_interval:
                await asyncio.sleep(min_interval - delta)
            self._last_called = time.monotonic()
