"""WS07-01/02/09 — Rate limiting with distributed (Redis) + in-process backends.

Concept separation (WS07-02):
  - **rate limit** (this module): short-window abuse/DoS protection;
  - **concurrency / daily quota / provider budget**: app.costguard + app.jobs.

Backends
--------
``InProcessBackend``  sliding-window counters held in this process. Under
gunicorn with N workers the effective limit is ~N× the configured value —
acceptable for small self-hosting, documented, and the default when REDIS_URL
is unset (offline dev / single-worker deployments).

``RedisBackend``      shared sliding window (sorted set + small Lua script) so
every API replica enforces the SAME effective limit. This is the public
production backend (REDIS_URL set).

Fail behaviour
--------------
Security controls fail closed: when Redis is configured but unreachable and
``fail_closed`` is true, ``allow()`` reports an *unavailable* verdict and the
caller must reject heavy/credential API calls with a retryable 503 — never
silently continue with unshared limits.

Keying dimensions (WS07-01)
---------------------------
- credential surfaces (login/register/recovery): client IP **and** normalized
  account/email hash — two independent counters that must both allow, so
  distributed attacks from many IPs can't rotate around an IP limit and a
  victim account can't be locked out by one abusive IP;
- authenticated heavy features: user id (never IP alone — NAT users share
  addresses and attackers distribute IPs);
- everything else: client IP.

Abuse escalation (WS07-09 ladder steps 1-2): repeated denials tighten the
bucket — after ``escalate_after`` denials the effective limit halves (bounded
at 1/8). Escalation counters decay with a TTL; CAPTCHA/risk-hold/admin review
are later ladder steps and are intentionally not here.
"""
from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass
from collections import deque


# ── Rule table ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Rule:
    limit: int
    window_sec: int
    kind: str  # "ip" | "credential" | "user"


# The FIRST matching prefix wins, else the global default applies.
_RULES: tuple[tuple[str, Rule], ...] = (
    # Credential surfaces — tight, to blunt brute-force + reset spam + enumeration.
    ("/api/account/login", Rule(10, 60, "credential")),
    ("/api/account/register", Rule(5, 60, "credential")),
    ("/api/account/forgot", Rule(5, 60, "credential")),
    ("/api/account/reset", Rule(10, 60, "credential")),
    ("/api/account/password", Rule(10, 60, "credential")),
    ("/api/auth/login", Rule(10, 60, "credential")),
    # Paid-LLM surfaces — cap cost-abuse, keyed by ACCOUNT when signed in.
    ("/api/writing/evaluate", Rule(20, 60, "user")),
    ("/api/speaking/evaluate", Rule(20, 60, "user")),
    ("/api/speaking/roleplay", Rule(30, 60, "user")),
    ("/api/speaking/transcribe", Rule(12, 60, "user")),  # ASR is CPU-heavy — tighter
    ("/api/reading/generate", Rule(20, 60, "user")),
    ("/api/listening/generate", Rule(20, 60, "user")),
    ("/api/vocab", Rule(30, 60, "user")),
    ("/api/pronounce/", Rule(30, 60, "user")),
    ("/api/lesson/generate", Rule(15, 60, "user")),
)
_DEFAULT_RULE = Rule(300, 60, "ip")


def rule_for(path: str) -> Rule:
    for prefix, rule in _RULES:
        if path.startswith(prefix):
            return rule
    return _DEFAULT_RULE


def client_key(remote_addr: str | None) -> str:
    """Rate-limit client key: the socket peer address ONLY.

    Forwarded headers (X-Forwarded-For / X-Real-IP) are NEVER read here — a
    direct client could set them to arbitrary values and rotate the limiter
    key (WS09 required test). In production Flask sits behind exactly one
    trusted nginx proxy: when TRUSTED_PROXIES=1, werkzeug ProxyFix has already
    rewritten remote_addr to the proxy-observed client IP before this runs;
    direct connections that bypass the proxy keep the raw peer address and
    cannot forge a different key."""
    return remote_addr or "unknown"


def email_hash(email: str | None) -> str | None:
    """Normalized account/email hash for credential-abuse keying. The raw
    email never enters the limiter key (no PII in infrastructure state)."""
    if not email:
        return None
    norm = str(email).strip().lower()
    if not norm:
        return None
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def time_ms() -> int:
    return int(time.monotonic() * 1000)


# ── Backends ──────────────────────────────────────────────────────────────────

class InProcessBackend:
    """Sliding-window counters in this process (documented N-worker caveat)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[tuple[int, str]]] = {}
        self._esc: dict[str, tuple[int, int]] = {}  # key -> (count, expires_ms)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_ms: int, member: str) -> bool:
        now = time_ms()
        cutoff = now - window_ms
        with self._lock:
            dq = self._hits.get(key)
            if dq is None:
                dq = deque()
                self._hits[key] = dq
            while dq and dq[0][0] <= cutoff:
                dq.popleft()
            if len(dq) >= limit:
                return False
            dq.append((now, member))
            return True

    def bump(self, key: str, ttl_ms: int) -> int:
        now = time_ms()
        with self._lock:
            count, expires = self._esc.get(key, (0, 0))
            if expires <= now:
                count = 0
            count += 1
            self._esc[key] = (count, now + ttl_ms)
            return count

    def escalations(self, key: str) -> int:
        now = time_ms()
        with self._lock:
            count, expires = self._esc.get(key, (0, 0))
            return count if expires > now else 0

    def oldest(self, key: str) -> int | None:
        with self._lock:
            dq = self._hits.get(key)
            return dq[0][0] if dq else None

    def retry_after(self, key: str, window_sec: int) -> int:
        oldest = self.oldest(key)
        if oldest is None:
            return max(1, window_sec // 2)
        return max(1, int(math.ceil((oldest + window_sec * 1000 - time_ms()) / 1000)))


class RedisBackend:
    """Shared fixed-window counters for all API replicas (WS07-01 required
    test). Fixed windows are the standard, scripting-free choice for abuse
    control: one atomic MULTI pipeline (INCR + EXPIRE NX), no Lua dependency,
    and at most one boundary burst per window — acceptable for this control
    plane (product quota remains exact, and lives in the DB/ledger)."""

    def __init__(self, client) -> None:
        # client: a redis-py client (decode_responses=True recommended).
        self._r = client

    def check(self, key: str, limit: int, window_ms: int, member: str) -> bool:
        full = f"rl:w:{key}"
        ttl_s = max(1, int(math.ceil(window_ms / 1000)))
        pipe = self._r.pipeline()
        pipe.incr(full)
        pipe.expire(full, ttl_s, nx=True)
        n = int(pipe.execute()[0])
        return n <= max(1, limit)

    def bump(self, key: str, ttl_ms: int) -> int:
        esc = f"rl:esc:{key}"
        pipe = self._r.pipeline()
        pipe.incr(esc)
        pipe.expire(esc, max(1, int(math.ceil(ttl_ms / 1000))), nx=True)
        return int(pipe.execute()[0])

    def escalations(self, key: str) -> int:
        v = self._r.get(f"rl:esc:{key}")
        return int(v or 0)

    def retry_after(self, key: str, window_sec: int) -> int:
        ttl = self._r.ttl(f"rl:w:{key}")
        if ttl and ttl > 0:
            return max(1, int(ttl))
        return max(1, window_sec // 2)


# ── Service facade ────────────────────────────────────────────────────────────

class Verdict:
    __slots__ = ("allowed", "retry_after", "unavailable")

    def __init__(self, allowed: bool, retry_after: int = 0,
                 unavailable: bool = False) -> None:
        self.allowed = allowed
        self.retry_after = retry_after
        self.unavailable = unavailable


class RateLimitService:
    """Dimension-aware limiter facade shared by all API workers."""

    MAX_ESCALATION_STEPS = 3  # effective limit floor: limit >> 3 (1/8)

    def __init__(self, backend, fail_closed: bool = True,
                 escalate_after: int = 3) -> None:
        self._backend = backend
        self._fail_closed = fail_closed
        self._escalate_after = max(1, escalate_after)

    def _deny(self, key: str, window_sec: int) -> Verdict:
        self._backend.bump(key, window_sec * 4 * 1000)
        return Verdict(False, self._backend.retry_after(key, window_sec))

    def _check_dimension(self, key: str, rule: Rule) -> Verdict:
        steps = min(self._backend.escalations(key) // self._escalate_after,
                    self.MAX_ESCALATION_STEPS)
        effective = max(1, rule.limit >> steps)
        member = f"{time_ms()}:{time.monotonic_ns()}"
        try:
            if self._backend.check(key, effective, rule.window_sec * 1000, member):
                return Verdict(True)
        except Exception:
            # Redis configured but unreachable: fail closed for rate limiting
            # (a retryable 503 — brute-force protection never silently opens).
            if self._fail_closed:
                return Verdict(False, retry_after=5, unavailable=True)
            return Verdict(True)
        return self._deny(key, rule.window_sec)

    def allow(self, rule: Rule, ip: str, user_id=None,
              email: str | None = None) -> Verdict:
        """Check all applicable dimension counters; every one must allow."""
        verdict = Verdict(True)
        dimensions: list[tuple[str, Rule]] = []
        if rule.kind == "credential":
            dimensions.append((f"ip:{ip}", rule))
            eh = email_hash(email)
            if eh:
                dimensions.append((f"em:{eh}", rule))
        elif rule.kind == "user" and user_id is not None:
            dimensions.append((f"u:{user_id}", rule))
        else:
            # Anonymous hit on a user-kind rule falls back to IP (still never
            # keyed by IP ALONE for authenticated usage: signed-in callers are
            # always keyed by user id).
            dimensions.append((f"ip:{ip}", rule))
        for key, r in dimensions:
            v = self._check_dimension(key, r)
            if not v.allowed:
                return v
        return verdict


def build_redis_client(redis_url: str):
    """Small, bounded client: API threads must never hang on Redis."""
    import redis  # lazy: offline dev never needs the dependency
    return redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
