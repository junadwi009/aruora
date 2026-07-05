"""
Lightweight in-process rate limiter (no external dependency, works offline).

A sliding-window counter keyed by (client-ip, bucket). Intended as a
defence-in-depth control against credential brute-force and unauthenticated
LLM cost-abuse — NOT a distributed quota system. Notes/limits:

  - State lives in this process. Under gunicorn with N workers each worker
    holds its own window, so the effective limit is ~N× the configured value.
    That is acceptable for a small self-hosted app; front a shared store
    (Redis) if you need exact global limits.
  - The client key prefers the nginx-set X-Real-IP, falling back to the socket
    peer. In production only the web (nginx) port is published and the API is
    on the internal network, so X-Real-IP is trustworthy there.
"""
from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_sec: float, now: float | None = None) -> bool:
        """Return True if this hit is allowed, False if it exceeds `limit`
        within the trailing `window_sec`. Records the hit when allowed."""
        t = time.monotonic() if now is None else now
        cutoff = t - window_sec
        with self._lock:
            dq = self._hits.get(key)
            if dq is None:
                dq = deque()
                self._hits[key] = dq
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= limit:
                return False
            dq.append(t)
            return True


# Rule table: the FIRST matching prefix wins, else the global default applies.
# (limit, window_seconds)
_RULES: tuple[tuple[str, int, int], ...] = (
    # Credential surfaces — tight, to blunt brute-force + reset spam + enumeration.
    ("/api/account/login", 10, 60),
    ("/api/account/register", 5, 60),
    ("/api/account/forgot", 5, 60),
    ("/api/account/reset", 10, 60),
    ("/api/account/password", 10, 60),
    ("/api/auth/login", 10, 60),
    # Paid-LLM surfaces — cap cost-abuse from a single client.
    ("/api/writing/evaluate", 20, 60),
    ("/api/speaking/evaluate", 20, 60),
    ("/api/speaking/roleplay", 30, 60),
    ("/api/speaking/transcribe", 12, 60),   # local Whisper is CPU-heavy — tighter
    ("/api/reading/generate", 20, 60),
    ("/api/listening/generate", 20, 60),
    ("/api/vocab", 30, 60),
    ("/api/pronounce/", 30, 60),
    ("/api/lesson/generate", 15, 60),
)
_DEFAULT = (300, 60)  # generous global ceiling for everything else


def rule_for(path: str) -> tuple[int, int]:
    for prefix, limit, window in _RULES:
        if path.startswith(prefix):
            return limit, window
    return _DEFAULT


def client_key(headers, remote_addr: str | None) -> str:
    xri = (headers.get("X-Real-IP") or "").strip()
    return xri or (remote_addr or "unknown")
