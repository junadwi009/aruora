"""Runtime gateway boundary: emergency/provider-budget guard on every call."""
from app.costguard import ensure_ai_available


class GuardedGateway:
    def __init__(self, gateway, cfg, repo):
        self._gateway, self._cfg, self._repo = gateway, cfg, repo

    def __getattr__(self, name):
        return getattr(self._gateway, name)

    def score(self, *args, **kwargs):
        ensure_ai_available(self._cfg, self._repo)
        return self._gateway.score(*args, **kwargs)

    def generate(self, *args, **kwargs):
        ensure_ai_available(self._cfg, self._repo)
        return self._gateway.generate(*args, **kwargs)
