"""Per-client sliding-window request counters (thread-safe)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindow:
    """Counts requests per client over a rolling window of seconds."""

    def __init__(self, window_seconds: float = 10.0, max_clients: int = 50_000):
        self.window = window_seconds
        self.max_clients = max_clients
        self._hits: dict = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, client: str, now: float | None = None) -> int:
        """Record one request; return the count within the window."""
        now = time.time() if now is None else now
        cutoff = now - self.window
        with self._lock:
            dq = self._hits[client]
            dq.append(now)
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(self._hits) > self.max_clients:
                self._evict(cutoff)
            return len(dq)

    def count(self, client: str, now: float | None = None) -> int:
        now = time.time() if now is None else now
        cutoff = now - self.window
        with self._lock:
            dq = self._hits.get(client)
            if not dq:
                return 0
            while dq and dq[0] < cutoff:
                dq.popleft()
            return len(dq)

    def _evict(self, cutoff: float) -> None:
        # Called with the lock held. Drop clients with no recent hits.
        stale = [c for c, dq in self._hits.items() if not dq or dq[-1] < cutoff]
        for c in stale:
            del self._hits[c]
