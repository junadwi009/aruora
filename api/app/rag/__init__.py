"""
WS28 — Auto-RAG knowledge layer facade.

Stage-1/2 scope shipped here (28 §20):
  - allowlist-first source registry + staged/atomic versioned ingestion
  - content-hash change detection (unchanged source ⇒ zero cost)
  - structure-aware chunking + security quarantine
  - provider-neutral embeddings with WS27 ledger accounting
  - hybrid (keyword + exact-cosine vector) retrieval with RRF, authorization
    BEFORE similarity, provenance-aware context packs
  - privacy-safe retrieval telemetry (query hash only)

Normal Task Pool serving does NOT call RAG (28 §10/§14): retrieval happens at
background generation / help-answer time via ``Retriever.retrieve`` with an
explicit use_case. Calibrated scoring has no retrieval authorization at all.
"""

from app.rag.policy import RagPolicyError  # noqa: F401
from app.rag.retrieval import ContextPack, Retriever, RETRIEVAL_VERSION  # noqa: F401
from app.rag.ingestion import (  # noqa: F401
    RagIngestError,
    ingest_source,
    register_source,
    activate_source,
    validate_source_fields,
    validate_source_url,
    validate_source_payload_size,
)
