"""WS03-08 — tiny key/value abstraction for cross-process security counters.

The auth abuse throttles (login failures, registration/reset/resend bursts)
must be enforced across all API worker processes, so their counters live in a
shared store. When REDIS_URL is configured a real Redis client is used;
otherwise an in-process store is substituted for development and tests.

The in-process fallback is NOT distributed: production deployments must set
REDIS_URL (docker-compose provides the service) so the controls are global.
"""
from __future__ import annotations

import threading
import time


class MemoryKV:
    """Thread-safe in-memory counter store with monotonic expiry."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def _purge(self, now: float) -> None:
        dead = [k for k, (_, exp) in self._data.items() if exp <= now]
        for k in dead:
            self._data.pop(k, None)

    def incr(self, key: str, ttl_sec: float) -> int:
        """Atomically increment; the TTL restarts from the first increment."""
        now = time.monotonic()
        with self._lock:
            self._purge(now)
            entry = self._data.get(key)
            if entry is None or entry[1] <= now:
                self._data[key] = ("1", now + ttl_sec)
                return 1
            val = str(int(entry[0]) + 1)
            self._data[key] = (val, entry[1])
            return int(val)

    def get(self, key: str) -> str | None:
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None or entry[1] <= now:
                return None
            return entry[0]

    def set(self, key: str, val: str, ttl_sec: float) -> None:
        now = time.monotonic()
        with self._lock:
            self._data[key] = (str(val), now + ttl_sec)

    def ttl(self, key: str) -> float:
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if entry is None or entry[1] <= now:
                return 0.0
            return max(0.0, entry[1] - now)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class RedisKV:
    """Redis-backed counters (same interface). Degrades to fail-open ONLY if
    Redis itself is unreachable — throttles are defence-in-depth, and failing
    closed here would lock every learner out of the API during a Redis blip.
    The primary session security does not depend on this store."""

    def __init__(self, url: str) -> None:
        import redis  # lazy: optional dependency

        self._r = redis.Redis.from_url(url, decode_responses=True)

    def incr(self, key: str, ttl_sec: float) -> int:
        try:
            n = self._r.incr(key)
            if n == 1:
                self._r.expire(key, int(max(1, ttl_sec)))
            return int(n)
        except Exception:
            return 1  # fail open for counters

    def get(self, key: str) -> str | None:
        try:
            return self._r.get(key)
        except Exception:
            return None

    def set(self, key: str, val: str, ttl_sec: float) -> None:
        try:
            self._r.setex(key, int(max(1, ttl_sec)), str(val))
        except Exception:
            pass

    def ttl(self, key: str) -> float:
        try:
            return float(self._r.ttl(key))
        except Exception:
            return 0.0

    def delete(self, key: str) -> None:
        try:
            self._r.delete(key)
        except Exception:
            pass


def build_kv(redis_url: str = ""):
    return RedisKV(redis_url) if redis_url else MemoryKV()
