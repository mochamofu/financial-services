"""Shared state backend — the seam that makes ToriiGate horizontally
scalable.

Rate-limit windows and repeat-offender memory are per-client counters.
In a single process an in-memory store is fine; behind a load balancer
with N gateway workers, each worker seeing only its slice of traffic
would let an attacker get N× the real limit. Routing that state through
a shared store (Redis) makes the limit hold across the whole fleet.

``MemoryStore`` is the zero-dependency default. ``RedisStore`` uses a
redis client (``redis`` package, optional) and is safe across workers
and restarts. Both satisfy the same :class:`StateStore` interface, so
the detector never knows which it is talking to.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque


class StateStore(ABC):
    """Sliding-window request counters + offender tallies."""

    @abstractmethod
    def hit(self, key: str, now: float) -> int:
        """Record one event for *key*; return the count in the window."""

    @abstractmethod
    def count(self, key: str, now: float) -> int:
        """Current count for *key* without recording a new event."""

    @abstractmethod
    def incr_offender(self, ip: str) -> int:
        """Increment and return the offense tally for *ip*."""

    @abstractmethod
    def get_offender(self, ip: str) -> int:
        """Current offense tally for *ip* (0 if none)."""


class MemoryStore(StateStore):
    """In-process store. Fast, but not shared across workers."""

    def __init__(self, window_seconds: float, offender_ttl: float = 86_400,
                 max_clients: int = 100_000):
        self.window = window_seconds
        self.offender_ttl = offender_ttl
        self.max_clients = max_clients
        self._hits: dict = defaultdict(deque)
        self._offenders: dict = {}   # ip -> (count, last_ts)
        self._lock = threading.Lock()

    def hit(self, key: str, now: float) -> int:
        cutoff = now - self.window
        with self._lock:
            dq = self._hits[key]
            dq.append(now)
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(self._hits) > self.max_clients:
                self._evict(cutoff)
            return len(dq)

    def count(self, key: str, now: float) -> int:
        cutoff = now - self.window
        with self._lock:
            dq = self._hits.get(key)
            if not dq:
                return 0
            while dq and dq[0] < cutoff:
                dq.popleft()
            return len(dq)

    def incr_offender(self, ip: str) -> int:
        now = time.time()
        with self._lock:
            count, last = self._offenders.get(ip, (0, now))
            if now - last > self.offender_ttl:
                count = 0
            count += 1
            self._offenders[ip] = (count, now)
            return count

    def get_offender(self, ip: str) -> int:
        with self._lock:
            entry = self._offenders.get(ip)
            if not entry:
                return 0
            count, last = entry
            if time.time() - last > self.offender_ttl:
                del self._offenders[ip]
                return 0
            return count

    def _evict(self, cutoff: float) -> None:
        stale = [c for c, dq in self._hits.items() if not dq or dq[-1] < cutoff]
        for c in stale:
            del self._hits[c]


class RedisStore(StateStore):
    """Fleet-wide store backed by Redis.

    Sliding windows use a sorted set per key (score = timestamp); the
    window is trimmed on every hit. Offenders use INCR + EXPIRE. Pass any
    object with the standard redis-py API (``redis.Redis`` or a cluster
    client). Times are milliseconds internally to keep set members unique.
    """

    def __init__(self, client, window_seconds: float,
                 offender_ttl: int = 86_400, prefix: str = "torii:"):
        self.r = client
        self.window_ms = int(window_seconds * 1000)
        self.offender_ttl = offender_ttl
        self.prefix = prefix

    def _rk(self, key: str) -> str:
        return f"{self.prefix}rl:{key}"

    def hit(self, key: str, now: float) -> int:
        rk = self._rk(key)
        now_ms = int(now * 1000)
        member = f"{now_ms}-{now_ms % 100000}"
        pipe = self.r.pipeline()
        pipe.zremrangebyscore(rk, 0, now_ms - self.window_ms)
        pipe.zadd(rk, {member: now_ms})
        pipe.zcard(rk)
        pipe.pexpire(rk, self.window_ms + 1000)
        return pipe.execute()[2]

    def count(self, key: str, now: float) -> int:
        rk = self._rk(key)
        now_ms = int(now * 1000)
        pipe = self.r.pipeline()
        pipe.zremrangebyscore(rk, 0, now_ms - self.window_ms)
        pipe.zcard(rk)
        return pipe.execute()[1]

    def incr_offender(self, ip: str) -> int:
        ok = f"{self.prefix}off:{ip}"
        pipe = self.r.pipeline()
        pipe.incr(ok)
        pipe.expire(ok, self.offender_ttl)
        return pipe.execute()[0]

    def get_offender(self, ip: str) -> int:
        val = self.r.get(f"{self.prefix}off:{ip}")
        return int(val) if val else 0


def store_from_env(window_seconds: float) -> StateStore:
    """Build a store from ``TORII_REDIS_URL`` if set, else in-memory.

    Keeps the fleet-wide path opt-in and dependency-free by default: no
    Redis URL, no redis import.
    """
    import os
    url = os.environ.get("TORII_REDIS_URL", "").strip()
    if not url:
        return MemoryStore(window_seconds)
    try:
        import redis  # optional dependency
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "TORII_REDIS_URL is set but the 'redis' package is not "
            "installed (pip install toriigate[redis]).") from e
    return RedisStore(redis.Redis.from_url(url), window_seconds)
