import os


def _truthy(val):
    return str(val).strip().lower() in ("1", "true", "yes", "on")


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
