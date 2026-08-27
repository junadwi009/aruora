import os


def _truthy(val):
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _email_set(val):
    """Parse a comma-separated string (or any iterable) into a lowercased email set."""
    if isinstance(val, (set, frozenset, list, tuple)):
        items = val
    else:
        items = str(val).split(",")
    return frozenset(e.strip().lower() for e in items if e and e.strip())


class Config:
    def __init__(self, overrides=None):
        o = overrides or {}
        self.LLM_MODE = o.get("LLM_MODE", os.getenv("LLM_MODE", "stub"))
        self.LLM_PROVIDER = o.get("LLM_PROVIDER", os.getenv("LLM_PROVIDER", "openrouter"))
        self.OPENROUTER_API_KEY = o.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
        self.OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.DATABASE_URL = o.get("DATABASE_URL", os.getenv("DATABASE_URL", ""))
        # WS09-04 same-origin policy: comma-separated browser origins allowed to
        # call the API cross-origin (with credentials). Empty = CORS is fully
        # disabled — the production same-origin deployment (nginx serves the SPA
        # and proxies /api) needs NO cross-origin browser access at all, so the
        # secure default is "no CORS headers are ever emitted".
        _cors = o.get("CORS_ORIGIN", os.getenv("CORS_ORIGIN", ""))
        self.CORS_ORIGINS = tuple(
            origin.strip() for origin in _cors.split(",") if origin.strip()
        ) if _cors else ()
        # WS09-02: explicit Host allow-list (comma-separated, e.g.
        # "aruora.app,api.aruora.app"). When set, requests whose Host header is
        # not on the list are rejected (421) before any work — this stops
        # host-header injection (cache poisoning, password-reset link rewrite).
        # Empty = no Host restriction (offline dev / IP-based self-hosting).
        self.TRUSTED_HOSTS = _email_set(o.get("TRUSTED_HOSTS", os.getenv("TRUSTED_HOSTS", "")))
        # WS09-03: number of trusted reverse proxies in front of Flask (0 =
        # none; the docker prod topology is nginx → gunicorn, so 1). Only when
        # > 0 is Werkzeug ProxyFix applied, and only for the exact headers the
        # proxy sets: X-Forwarded-For (client IP) and, when TRUSTED_PROXY_PROTO,
        # X-Forwarded-Proto. Forwarded headers from direct clients are NEVER
        # trusted (they cannot bypass the proxy path to spoof their IP).
        self.TRUSTED_PROXIES = int(o.get("TRUSTED_PROXIES", os.getenv("TRUSTED_PROXIES", "0")))
        self.TRUSTED_PROXY_PROTO = _truthy(o.get(
            "TRUSTED_PROXY_PROTO", os.getenv("TRUSTED_PROXY_PROTO", "0")))
        self.TESTING = o.get("TESTING", False)
        # WS08-04B: deployment environment marker. Any public deployment must
        # set APP_ENV=production; startup validation then fails closed on
        # development defaults (dev session secret, default DB credentials).
        self.APP_ENV = o.get("APP_ENV", os.getenv("APP_ENV", "development"))
        # Optional app-level passcode gate. Empty = open (offline dev default).
        self.APP_PASSCODE = o.get("APP_PASSCODE", os.getenv("APP_PASSCODE", ""))
        self.SESSION_SECRET = o.get("SESSION_SECRET", os.getenv("SESSION_SECRET", "dev-secret-change-me"))
        self.SESSION_TIMEOUT_MIN = int(o.get("SESSION_TIMEOUT_MIN", os.getenv("SESSION_TIMEOUT_MIN", "30")))
        # WS03-01: absolute cap on a non-remembered server-side session (hours),
        # enforced regardless of activity. Remembered sessions cap at REMEMBER_DAYS.
        self.SESSION_ABSOLUTE_HOURS = int(o.get("SESSION_ABSOLUTE_HOURS", os.getenv("SESSION_ABSOLUTE_HOURS", "12")))
        # Session-cookie hardening. COOKIE_SECURE must be true in any HTTPS
        # deployment (the cookie is then never sent over plain HTTP); leave false
        # for local http dev. SameSite=Lax is our primary CSRF defence — browsers
        # withhold the cookie on cross-site POST/DELETE/PATCH.
        self.COOKIE_SECURE = _truthy(o.get("COOKIE_SECURE", os.getenv("COOKIE_SECURE", "0")))
        self.COOKIE_SAMESITE = o.get("COOKIE_SAMESITE", os.getenv("COOKIE_SAMESITE", "Lax"))
        # Max request body (bytes). Caps memory-exhaustion via huge JSON/uploads.
        # 26 MB matches the nginx client_max_body_size (speech-audio uploads).
        self.MAX_CONTENT_BYTES = int(o.get("MAX_CONTENT_BYTES", os.getenv("MAX_CONTENT_BYTES", str(26 * 1024 * 1024))))
        # In-process rate limiting (brute-force + LLM cost-abuse defence).
        # Always disabled under TESTING so the suite can hammer endpoints.
        self.RATE_LIMIT_ENABLED = _truthy(o.get("RATE_LIMIT_ENABLED", os.getenv("RATE_LIMIT_ENABLED", "1")))
        # "Remember me": a remembered session survives browser restarts and is
        # forgotten only after this many days of inactivity (sliding).
        self.REMEMBER_DAYS = int(o.get("REMEMBER_DAYS", os.getenv("REMEMBER_DAYS", "7")))
        # Master-admin allow-list. Designation is env-only (never self-service): a
        # signed-in account is admin iff its email is in this set. No is_admin DB
        # column, so admin can't be granted by a DB write — only by deployment config.
        # (WS03-07: acceptable for beta with documented residual risk; GA requires
        # the normalized RBAC/role model + mandatory MFA below.)
        self.ADMIN_EMAILS = _email_set(o.get("ADMIN_EMAILS", os.getenv("ADMIN_EMAILS", "")))
        # WS03-07: shared base32 TOTP secret for admin accounts. When set, admin
        # logins and destructive-admin reauthentication must present a valid code.
        self.ADMIN_TOTP_SECRET = o.get("ADMIN_TOTP_SECRET", os.getenv("ADMIN_TOTP_SECRET", ""))
        # WS03-07: window (seconds) after a successful password reauthentication
        # during which destructive admin actions are permitted.
        self.ADMIN_REAUTH_SECONDS = int(o.get("ADMIN_REAUTH_SECONDS", os.getenv("ADMIN_REAUTH_SECONDS", "300")))
        # WS03-04: NIST-aligned new-password minimum (single-factor auth).
        self.MIN_PASSWORD_CHARS = int(o.get("MIN_PASSWORD_CHARS", os.getenv("MIN_PASSWORD_CHARS", "15")))
        # WS03-08: shared store for cross-process abuse counters (login throttle,
        # register/forgot/reset/verify-resend bursts). Empty = in-process fallback
        # (dev/test only — production must set REDIS_URL for global enforcement).
        self.REDIS_URL = o.get("REDIS_URL", os.getenv("REDIS_URL", ""))
        # WS03-05: when true, accounts created via local registration must verify
        # email ownership before using expensive/persistent features (LLM routes).
        # Google accounts inherit the provider's email_verified claim.
        self.EMAIL_VERIFICATION_REQUIRED = _truthy(o.get(
            "EMAIL_VERIFICATION_REQUIRED", os.getenv("EMAIL_VERIFICATION_REQUIRED", "0")))
        # WS03-06B: fail startup (readiness) when email-dependent account flows are
        # enabled but mail delivery is not configured. Set to 1 in production.
        self.FAIL_CLOSED_ON_MAIL = _truthy(o.get("FAIL_CLOSED_ON_MAIL", os.getenv("FAIL_CLOSED_ON_MAIL", "0")))
        # WS03-05: lifetime (minutes) of single-use email-verification tokens.
        self.VERIFY_TOKEN_MIN = int(o.get("VERIFY_TOKEN_MIN", os.getenv("VERIFY_TOKEN_MIN", "1440")))
        # Google Sign-In: the OAuth Web-client ID. Public (embedded in the frontend);
        # the backend verifies ID tokens against it. Empty = Google sign-in disabled.
        self.GOOGLE_CLIENT_ID = o.get("GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID", ""))
        # SMTP (optional) for password reset + reminders. Empty SMTP_HOST = dev (log only).
        self.SMTP_HOST = os.getenv("SMTP_HOST", "")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM = os.getenv("SMTP_FROM", "")
        self.APP_BASE_URL = o.get("APP_BASE_URL", os.getenv("APP_BASE_URL", "http://localhost:5173"))
        # Shared secret for the cron-triggered reminder endpoint. Empty = disabled.
        self.REMINDER_TOKEN = o.get("REMINDER_TOKEN", os.getenv("REMINDER_TOKEN", ""))
        # Fallback timezone for users who haven't set a reminder timezone.
        self.REMINDER_DEFAULT_TZ = o.get("REMINDER_DEFAULT_TZ", os.getenv("REMINDER_DEFAULT_TZ", "Asia/Jakarta"))
        self.MODEL_GENERATE = o.get("MODEL_GENERATE", os.getenv("MODEL_GENERATE", "anthropic/claude-haiku-4-5"))
        self.MODEL_SCORE = o.get("MODEL_SCORE", os.getenv("MODEL_SCORE", "deepseek/deepseek-chat-v3.1:free"))
        # Test-phase feedback gate (Feature A).
        self.GATE_ENABLED = _truthy(o.get("GATE_ENABLED", os.getenv("GATE_ENABLED", "1")))
        self.GATE_LOCK_SECONDS = int(o.get("GATE_LOCK_SECONDS", os.getenv("GATE_LOCK_SECONDS", "25200")))
        self.GATE_HEARTBEAT_SEC = int(o.get("GATE_HEARTBEAT_SEC", os.getenv("GATE_HEARTBEAT_SEC", "60")))
        # Token efficiency (Feature B). POOL_TARGET sets per (skill,band) before
        # generation freezes; DAILY_GEN_CAP=0 means unlimited.
        self.POOL_TARGET = int(o.get("POOL_TARGET", os.getenv("POOL_TARGET", "7")))
        self.DAILY_GEN_CAP = int(o.get("DAILY_GEN_CAP", os.getenv("DAILY_GEN_CAP", "20")))
        # Speaking ASR (faster-whisper, fully local/offline). Phase 2b-2.
        self.ASR_ENABLED = o.get("ASR_ENABLED", _truthy(os.getenv("ASR_ENABLED", "1")))
        self.ASR_MODEL = o.get("ASR_MODEL", os.getenv("ASR_MODEL", "base"))
        self.ASR_DEVICE = o.get("ASR_DEVICE", os.getenv("ASR_DEVICE", "cpu"))
        self.ASR_COMPUTE_TYPE = o.get("ASR_COMPUTE_TYPE", os.getenv("ASR_COMPUTE_TYPE", "int8"))
        # ASR-specific upload cap (bytes). Tighter than MAX_CONTENT_BYTES so a huge
        # audio decode can't tie up the CPU. Default 10 MB.
        self.ASR_MAX_UPLOAD_BYTES = int(o.get("ASR_MAX_UPLOAD_BYTES", os.getenv("ASR_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))))
        # ── WS06: audio evidence pipeline ─────────────────────────────────────
        # Voice-activity filtering before decode (WS06-04 quality gate input).
        self.ASR_VAD = o.get("ASR_VAD", _truthy(os.getenv("ASR_VAD", "1")))
        # Hard duration cap for a single recording (seconds, WS06-04).
        self.ASR_MAX_DURATION_SEC = int(o.get("ASR_MAX_DURATION_SEC", os.getenv("ASR_MAX_DURATION_SEC", "300")))
        # Recordings below this much actual speech are rejected as near-silence
        # ("insufficient audio quality") instead of being scored (WS06-04).
        self.ASR_MIN_SPEECH_SEC = float(o.get("ASR_MIN_SPEECH_SEC", os.getenv("ASR_MIN_SPEECH_SEC", "1.0")))
        # Allowed audio MIME types for the transcribe upload (WS06-04).
        self.ASR_ALLOWED_MIME = _email_set(o.get(
            "ASR_ALLOWED_MIME", os.getenv(
                "ASR_ALLOWED_MIME",
                "audio/webm,audio/webm;codecs=opus,audio/ogg,audio/wav,audio/x-wav,audio/wave,audio/mpeg,audio/mp3,audio/mp4,audio/m4a,audio/aac,audio/flac",
            )))
        # WS06-02: when 1, /api/speaking/transcribe ALWAYS answers 202 + jobId
        # (real queue or eager dispatcher); default follows REDIS_URL topology.
        self.ASR_FORCE_QUEUE = _truthy(o.get("ASR_FORCE_QUEUE", os.getenv("ASR_FORCE_QUEUE", "0")))
        # WS06-07: ephemeral audio location + TTL. Files are deleted right
        # after processing; the TTL janitor reaps crashed-run leftovers.
        self.ASR_AUDIO_DIR = o.get("ASR_AUDIO_DIR", os.getenv("ASR_AUDIO_DIR", "data/audio_tmp"))
        self.ASR_AUDIO_TTL_MIN = int(o.get("ASR_AUDIO_TTL_MIN", os.getenv("ASR_AUDIO_TTL_MIN", "30")))
        # WS06-05: pronunciation evidence is FAIL-CLOSED. Both a validated
        # estimator key AND its frozen calibration-pack version must be set
        # before any pronunciation score can exist. Empty (default) = off.
        self.PRONUNCIATION_ESTIMATOR = o.get("PRONUNCIATION_ESTIMATOR", os.getenv("PRONUNCIATION_ESTIMATOR", ""))
        self.PRONUNCIATION_CALIBRATION_VERSION = o.get(
            "PRONUNCIATION_CALIBRATION_VERSION", os.getenv("PRONUNCIATION_CALIBRATION_VERSION", ""))
        # ── WS05-05/06: LLM input/cost bounds and retry policy ────────────────
        # An authenticated account is not permission for unlimited paid inference.
        self.LLM_TIMEOUT_S = int(o.get("LLM_TIMEOUT_S", os.getenv("LLM_TIMEOUT_S", "60")))
        self.LLM_MAX_RETRIES = int(o.get("LLM_MAX_RETRIES", os.getenv("LLM_MAX_RETRIES", "2")))
        self.LLM_MAX_OUTPUT_TOKENS_SCORE = int(o.get("LLM_MAX_OUTPUT_TOKENS_SCORE", os.getenv("LLM_MAX_OUTPUT_TOKENS_SCORE", "2000")))
        self.LLM_MAX_OUTPUT_TOKENS_GEN = int(o.get("LLM_MAX_OUTPUT_TOKENS_GEN", os.getenv("LLM_MAX_OUTPUT_TOKENS_GEN", "2000")))
        # Per-task untrusted-input caps (characters). Routes enforce 422 earlier;
        # the gateway truncates as defence-in-depth so no code path can bypass.
        self.MAX_ESSAY_CHARS = int(o.get("MAX_ESSAY_CHARS", os.getenv("MAX_ESSAY_CHARS", "30000")))
        self.MAX_TRANSCRIPT_CHARS = int(o.get("MAX_TRANSCRIPT_CHARS", os.getenv("MAX_TRANSCRIPT_CHARS", "12000")))
        self.MAX_TOPIC_CHARS = int(o.get("MAX_TOPIC_CHARS", os.getenv("MAX_TOPIC_CHARS", "160")))
        self.MAX_SCENARIO_CHARS = int(o.get("MAX_SCENARIO_CHARS", os.getenv("MAX_SCENARIO_CHARS", "160")))
        self.MAX_ROLEPLAY_HISTORY_CHARS = int(o.get("MAX_ROLEPLAY_HISTORY_CHARS", os.getenv("MAX_ROLEPLAY_HISTORY_CHARS", "4000")))
        self.MAX_ROLEPLAY_TURN_CHARS = int(o.get("MAX_ROLEPLAY_TURN_CHARS", os.getenv("MAX_ROLEPLAY_TURN_CHARS", "1200")))
        self.MAX_LESSON_FIELD_CHARS = int(o.get("MAX_LESSON_FIELD_CHARS", os.getenv("MAX_LESSON_FIELD_CHARS", "160")))
        # ── WS28: Auto-RAG knowledge layer ────────────────────────────────────
        # Provider-neutral: the domain layer never hard-codes an embedding
        # provider; "local" = deterministic hashing embedder for dev/test.
        self.RAG_ENABLED = _truthy(o.get("RAG_ENABLED", os.getenv("RAG_ENABLED", "1")))
        self.RAG_DEFAULT_TOP_K = int(o.get("RAG_DEFAULT_TOP_K", os.getenv("RAG_DEFAULT_TOP_K", "8")))
        self.RAG_VECTOR_CANDIDATES = int(o.get("RAG_VECTOR_CANDIDATES", os.getenv("RAG_VECTOR_CANDIDATES", "30")))
        self.RAG_TEXT_CANDIDATES = int(o.get("RAG_TEXT_CANDIDATES", os.getenv("RAG_TEXT_CANDIDATES", "30")))
        self.RAG_RERANK_ENABLED = _truthy(o.get("RAG_RERANK_ENABLED", os.getenv("RAG_RERANK_ENABLED", "0")))
        self.RAG_MAX_CONTEXT_TOKENS = int(o.get("RAG_MAX_CONTEXT_TOKENS", os.getenv("RAG_MAX_CONTEXT_TOKENS", "1600")))
        self.RAG_SOURCE_MAX_BYTES = int(o.get("RAG_SOURCE_MAX_BYTES", os.getenv("RAG_SOURCE_MAX_BYTES", str(2 * 1024 * 1024))))
        self.EMBEDDING_PROVIDER = o.get("EMBEDDING_PROVIDER", os.getenv("EMBEDDING_PROVIDER", "local"))
        self.EMBEDDING_MODEL = o.get("EMBEDDING_MODEL", os.getenv("EMBEDDING_MODEL", "local-hash-v1"))
        self.EMBEDDING_DIM = int(o.get("EMBEDDING_DIM", os.getenv("EMBEDDING_DIM", "256")))
        # ── WS07: jobs / distributed rate limits / cost control ────────────────
        # (REDIS_URL itself is declared in the WS03-08 section above and shared:
        # it turns on the distributed limiter, queued jobs and shared counters.)
        # When Redis is configured but unreachable: deny heavy/credential /api
        # calls (503) instead of silently running per-worker limits (fail closed).
        self.RATE_LIMIT_FAIL_CLOSED = _truthy(o.get("RATE_LIMIT_FAIL_CLOSED", os.getenv("RATE_LIMIT_FAIL_CLOSED", "1")))
        # Repeated rejections tighten the bucket: after this many denials the
        # effective limit halves (bounded). Abuse-escalation ladder step 1-2.
        self.RATE_LIMIT_ESCALATE_AFTER = int(o.get("RATE_LIMIT_ESCALATE_AFTER", os.getenv("RATE_LIMIT_ESCALATE_AFTER", "3")))
        # Test-only escape hatch: force the limiter ON inside the pytest suite.
        self.RATE_LIMIT_TEST_FORCE = _truthy(o.get("RATE_LIMIT_TEST_FORCE", os.getenv("RATE_LIMIT_TEST_FORCE", "0")))
        # Concurrent heavy/paid AI operations per authenticated user.
        self.AI_CONCURRENCY_PER_USER = int(o.get("AI_CONCURRENCY_PER_USER", os.getenv("AI_CONCURRENCY_PER_USER", "2")))
        # Global provider budget. AI_DAILY_BUDGET_MICROS > 0 auto-halts paid AI
        # calls for the UTC day once the usage ledger reaches the ceiling.
        # AI_BUDGET_KILL=1 is the hard emergency switch (env-only, fail closed).
        self.AI_DAILY_BUDGET_MICROS = int(o.get("AI_DAILY_BUDGET_MICROS", os.getenv("AI_DAILY_BUDGET_MICROS", "0")))
        self.AI_BUDGET_KILL = _truthy(o.get("AI_BUDGET_KILL", os.getenv("AI_BUDGET_KILL", "0")))
        # Background pool-replenishment cost centre: max generations per UTC day
        # (system-wide, separate from any learner entitlement).
        self.REPLENISH_DAILY_BUDGET = int(o.get("REPLENISH_DAILY_BUDGET", os.getenv("REPLENISH_DAILY_BUDGET", "200")))
        # Backpressure: refuse to enqueue when a queue already holds this many
        # pending jobs (protects the broker and provider spend).
        self.QUEUE_MAX_DEPTH = int(o.get("QUEUE_MAX_DEPTH", os.getenv("QUEUE_MAX_DEPTH", "100")))
        # Idempotency keys / finished jobs are retained (and deduplicated) for
        # this long, then purgeable; expired jobs answer status with EXPIRED.
        self.JOB_RETENTION_HOURS = int(o.get("JOB_RETENTION_HOURS", os.getenv("JOB_RETENTION_HOURS", "24")))
        # WS27 §9.4: anti-repeat horizon — a pooled task served to a user
        # within this window is deprioritised (unseen items are preferred).
        self.POOL_REPEAT_COOLDOWN_HOURS = int(o.get("POOL_REPEAT_COOLDOWN_HOURS", os.getenv("POOL_REPEAT_COOLDOWN_HOURS", "24")))
        # WS10: structured JSON logs in production ("json" | "text") + level.
        self.LOG_FORMAT = o.get("LOG_FORMAT", os.getenv("LOG_FORMAT", "text"))
        self.LOG_LEVEL = o.get("LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO"))
        # ── WS08: database operations / data lifecycle ────────────────────────
        # Maintenance purge windows for DEAD security/operational state only.
        # Learning history is NEVER purged by these (app/jobs/maintenance.py).
        self.SESSION_RETENTION_HOURS = int(o.get("SESSION_RETENTION_HOURS", os.getenv("SESSION_RETENTION_HOURS", "72")))
        self.OTT_RETENTION_HOURS = int(o.get("OTT_RETENTION_HOURS", os.getenv("OTT_RETENTION_HOURS", "168")))
        self.ANALYTICS_RETENTION_DAYS = int(o.get("ANALYTICS_RETENTION_DAYS", os.getenv("ANALYTICS_RETENTION_DAYS", "180")))
        # Beat interval (seconds) for the maintenance sweep.
        self.MAINTENANCE_INTERVAL_S = int(o.get("MAINTENANCE_INTERVAL_S", os.getenv("MAINTENANCE_INTERVAL_S", "3600")))
        # Shared secret for the cron-triggered maintenance endpoint. Empty = disabled.
        self.MAINTENANCE_TOKEN = o.get("MAINTENANCE_TOKEN", os.getenv("MAINTENANCE_TOKEN", ""))

    @property
    def jobs_queued(self):
        """True → heavy work goes through the Redis/Celery queues."""
        return bool(self.REDIS_URL)

    @property
    def provider_configured(self):
        if self.LLM_MODE == "stub":
            return False
        key = self.OPENROUTER_API_KEY if self.LLM_PROVIDER == "openrouter" else self.ANTHROPIC_API_KEY
        return bool(key)
