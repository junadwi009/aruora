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
        self.CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:5173")
        self.TESTING = o.get("TESTING", False)
        # Optional app-level passcode gate. Empty = open (offline dev default).
        self.APP_PASSCODE = o.get("APP_PASSCODE", os.getenv("APP_PASSCODE", ""))
        self.SESSION_SECRET = o.get("SESSION_SECRET", os.getenv("SESSION_SECRET", "dev-secret-change-me"))
        self.SESSION_TIMEOUT_MIN = int(o.get("SESSION_TIMEOUT_MIN", os.getenv("SESSION_TIMEOUT_MIN", "30")))
        # "Remember me": a remembered session survives browser restarts and is
        # forgotten only after this many days of inactivity (sliding).
        self.REMEMBER_DAYS = int(o.get("REMEMBER_DAYS", os.getenv("REMEMBER_DAYS", "7")))
        # Master-admin allow-list. Designation is env-only (never self-service): a
        # signed-in account is admin iff its email is in this set. No is_admin DB
        # column, so admin can't be granted by a DB write — only by deployment config.
        self.ADMIN_EMAILS = _email_set(o.get("ADMIN_EMAILS", os.getenv("ADMIN_EMAILS", "")))
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
        self.MODEL_SCORE = o.get("MODEL_SCORE", os.getenv("MODEL_SCORE", "anthropic/claude-sonnet-4-6"))
        # Speaking ASR (faster-whisper, fully local/offline). Phase 2b-2.
        self.ASR_ENABLED = o.get("ASR_ENABLED", _truthy(os.getenv("ASR_ENABLED", "1")))
        self.ASR_MODEL = o.get("ASR_MODEL", os.getenv("ASR_MODEL", "base"))
        self.ASR_DEVICE = o.get("ASR_DEVICE", os.getenv("ASR_DEVICE", "cpu"))
        self.ASR_COMPUTE_TYPE = o.get("ASR_COMPUTE_TYPE", os.getenv("ASR_COMPUTE_TYPE", "int8"))

    @property
    def provider_configured(self):
        if self.LLM_MODE == "stub":
            return False
        key = self.OPENROUTER_API_KEY if self.LLM_PROVIDER == "openrouter" else self.ANTHROPIC_API_KEY
        return bool(key)
