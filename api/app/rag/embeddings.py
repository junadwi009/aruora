"""
WS28 — provider-neutral embedding gateway.

The domain layer NEVER hard-codes an embedding provider (28 §18). This module
defines the interface plus a deterministic LOCAL implementation used for dev,
test, and offline evaluation:

    local-hash-v1 — feature-hashing bag-of-tokens, L2-normalised, fixed dim.

Production swaps in a real provider behind the same interface; the stored
``embedding_model`` / ``embedding_version`` on every chunk keeps retrieval
reproducible and makes model migration (28 §12) a versioned backfill rather
than an in-place overwrite.

Every embed call records its usage into the WS27 ai_usage_ledger
(cost_center="rag", op=embedding_ingest|embedding_query) — local hashing
reports 0 tokens/0 cost, a real provider reports actuals.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.costguard import record_llm_usage

_WORD_RE = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


class LocalHashEmbedder:
    """Deterministic feature-hashing embedder (model id: local-hash-v1)."""

    model_id = "local-hash-v1"
    provider = "local"
    dim = 256

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        toks = _tokens(text)
        for i, tok in enumerate(toks):
            # two hashes per token reduce collision clumping
            h = hashlib.md5(tok.encode("utf-8")).digest()
            idx1 = int.from_bytes(h[:4], "little") % self.dim
            idx2 = int.from_bytes(h[4:8], "little") % self.dim
            sign = 1.0 if h[8] % 2 == 0 else -1.0
            vec[idx1] += sign * (1.0 + 0.05 * i)
            vec[idx2] += sign * 0.5
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    @staticmethod
    def estimate_tokens(texts: list[str]) -> int:
        return sum(len(_tokens(t)) for t in texts)


def cosine(a: list[float], b: list[float]) -> float:
    """Exact cosine similarity for dense float vectors (small-corpus baseline)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / math.sqrt(na * nb)


class EmbeddingGateway:
    """Interface facade — swaps provider implementations via config."""

    def __init__(self, cfg):
        name = str(getattr(cfg, "EMBEDDING_PROVIDER", "local"))
        if name == "local":
            self._impl = LocalHashEmbedder()
        else:  # pragma: no cover — provider impls land with measured need
            raise ValueError(f"unknown EMBEDDING_PROVIDER {name!r}")

    @property
    def model_id(self) -> str:
        return self._impl.model_id

    @property
    def dim(self) -> int:
        return self._impl.dim

    def embed(self, text: str) -> list[float]:
        return self._impl.embed(text)

    def embed_batch(self, texts: list[str], *, repo=None, op: str = "embedding_ingest",
                    cost_center: str = "rag", user_id: int | None = None) -> list[list[float]]:
        vecs = self._impl.embed_batch(texts)
        if repo is not None:
            toks = self._impl.estimate_tokens(texts)
            record_llm_usage(
                repo, cost_center=cost_center, op=op, user_id=user_id,
                meta={"provider": self._impl.provider,
                      "requestedModel": self.model_id,
                      "resolvedModel": self.model_id,
                      "promptTokens": toks, "completionTokens": None},
            )
        return vecs
