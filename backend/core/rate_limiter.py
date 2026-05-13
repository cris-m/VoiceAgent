import asyncio
import time
from collections import OrderedDict, deque
from typing import Optional


class InMemoryRateLimiter:
    """Async-safe in-process sliding-window rate limiter with bounded LRU eviction."""

    def __init__(self, requests: int, window_seconds: int, max_keys: int = 10000):
        self.requests = requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self.requests_per_key: OrderedDict[str, deque] = OrderedDict()
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = window_seconds

    async def is_allowed(self, key: str) -> bool:
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired(window_start)
                self._last_cleanup = now

            queue = self.requests_per_key.get(key)
            if queue is None:
                # Bound memory: evict oldest tracked key before inserting a new one.
                self._evict_lru()
                queue = deque()
                self.requests_per_key[key] = queue
                self.requests_per_key.move_to_end(key)

            while queue and queue[0] < window_start:
                queue.popleft()

            if len(queue) < self.requests:
                queue.append(now)
                self.requests_per_key.move_to_end(key)
                return True

            return False

    def _cleanup_expired(self, window_start: float) -> None:
        """Remove empty deques. Must be called inside the lock."""
        expired_keys = [key for key, queue in self.requests_per_key.items() if len(queue) == 0]
        for key in expired_keys:
            del self.requests_per_key[key]

    def _evict_lru(self) -> None:
        """Evict oldest tracked key when at capacity. Must be called inside the lock."""
        if len(self.requests_per_key) >= self.max_keys:
            oldest_key = next(iter(self.requests_per_key))
            del self.requests_per_key[oldest_key]

    async def reset(self, key: Optional[str] = None) -> None:
        async with self._lock:
            if key:
                if key in self.requests_per_key:
                    self.requests_per_key[key].clear()
            else:
                self.requests_per_key.clear()
