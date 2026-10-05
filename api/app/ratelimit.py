"""WS07-01/02/09 — distributed rate limiting with independent policy buckets.

Rate limits protect short-window abuse; concurrency and product/provider budgets
remain separate controls. Redis uses shared atomic fixed-window counters; the
in-process development backend uses sliding windows. Production security checks
fail closed on an unavailable configured Redis backend.

Each server-selected policy has independent IP/account dimensions. Public status
reads must not consume a registration or password-login quota. Raw URL IDs and
query strings never create new buckets. Credential rules check both IP and a
normalized email hash; authenticated heavy operations check the account ID.
Repeated denials tighten that policy's bucket, with expiring escalation state.
"""
from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass, replace
from collections import deque


@dataclass(frozen=True)
class Rule:
    limit: int
    window_sec: int
    kind: str  # "ip" | "credential" | "user"
    bucket: str = "custom"  # server-selected policy, never a raw caller URL


# The FIRST matching prefix wins, else the global default applies.
_RULES: tuple[tuple[str, Rule], ...] = (
    ("/api/account/login", Rule(10, 60, "credential")),
    ("/api/account/register", Rule(5, 60, "credential")),
    ("/api/account/forgot", Rule(5, 60, "credential")),
    ("/api/account/reset", Rule(10, 60, "credential")),
    ("/api/account/password", Rule(10, 60, "credential")),
    ("/api/auth/login", Rule(10, 60, "credential")),
    ("/api/writing/evaluate", Rule(20, 60, "user")),
    ("/api/placement/submit", Rule(10, 60, "user")),
    ("/api/speaking/evaluate", Rule(20, 60, "user")),
    ("/api/speaking/roleplay", Rule(30, 60, "user")),
    ("/api/speaking/transcribe", Rule(12, 60, "user")),
    ("/api/reading/generate", Rule(20, 60, "user")),
    ("/api/listening/generate", Rule(20, 60, "user")),
    ("/api/vocab", Rule(30, 60, "user")),
    ("/api/pronounce/", Rule(30, 60, "user")),
    ("/api/lesson/generate", Rule(15, 60, "user")),
)
_DEFAULT_RULE = Rule(300, 60, "ip", "global")


def rule_for(path: str) -> Rule:
    for prefix, rule in _RULES:
        if path.startswith(prefix):
            return replace(rule, bucket=prefix)
    return _DEFAULT_RULE


def client_key(remote_addr: str | None) -> str:
    """Use only the socket peer, after explicitly configured trusted ProxyFix.

    This function never reads client-supplied forwarded headers itself.
    """
    return remote_addr or "unknown"


def email_hash(email: str | None) -> str | None:
    """Normalized email hash; raw email never enters infrastructure keys."""
    if not email:
        return None
    norm = str(email).strip().lower()
    if not norm:
        return None
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def time_ms() -> int:
    return int(time.monotonic() * 1000)


class InProcessBackend:
    """Sliding-window counters in one process; not a production shared store."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[tuple[int, str]]] = {}
        self._esc: dict[str, tuple[int, int]] = {}
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
    """Shared fixed-window counters: atomic MULTI (INCR + EXPIRE NX).

    Product entitlement and financial budgets remain separate DB controls.
    """

    def __init__(self, client) -> None:
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


class Verdict:
    __slots__ = ("allowed", "retry_after", "unavailable")

    def __init__(self, allowed: bool, retry_after: int = 0,
                 unavailable: bool = False) -> None:
        self.allowed = allowed
        self.retry_after = retry_after
        self.unavailable = unavailable


class RateLimitService:
    """Dimension-aware limiter facade shared by all API workers."""

    MAX_ESCALATION_STEPS = 3

    def __init__(self, backend, fail_closed: bool = True,
                 escalate_after: int = 3) -> None:
        self._backend = backend
        self._fail_closed = fail_closed
        self._escalate_after = max(1, escalate_after)

    def _deny(self, key: str, window_sec: int) -> Verdict:
        self._backend.bump(key, window_sec * 4 * 1000)
        return Verdict(False, self._backend.retry_after(key, window_sec))

    def _check_dimension(self, key: str, rule: Rule) -> Verdict:
        try:
            steps = min(self._backend.escalations(key) // self._escalate_after,
                        self.MAX_ESCALATION_STEPS)
            effective = max(1, rule.limit >> steps)
            member = f"{time_ms()}:{time.monotonic_ns()}"
            if self._backend.check(key, effective, rule.window_sec * 1000, member):
                return Verdict(True)
            return self._deny(key, rule.window_sec)
        except Exception:
            # Every Redis operation, including escalation/TTL reads, is guarded.
            if self._fail_closed:
                return Verdict(False, retry_after=5, unavailable=True)
            return Verdict(True)

    def allow(self, rule: Rule, ip: str, user_id=None,
              email: str | None = None) -> Verdict:
        """Every applicable policy/dimension counter must allow the request.

        A health read must not consume a registration/login quota. Prefixes
        come from the finite rule table, not user-supplied URL IDs or queries.
        Counters for a given policy remain shared across API workers.
        """
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
            dimensions.append((f"ip:{ip}", rule))
        for key, r in dimensions:
            v = self._check_dimension(f"{rule.bucket}:{key}", r)
            if not v.allowed:
                return v
        return verdict


def build_redis_client(redis_url: str):
    """Small, bounded client: API threads must never hang on Redis."""
    import redis
    return redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
