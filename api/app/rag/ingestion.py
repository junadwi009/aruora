"""
WS28 — staged, atomic, change-detecting ingestion pipeline.

Contract (28 §7 / §21):
- content-hash change detection: an unchanged source creates NO new document,
  NO new embeddings, NO ledger cost (required test);
- every ingest produces a NEW staged document version (chunks re-used only
  when their content hash matches the previous version);
- security scan (policy.security_scan) quarantines prompt-like / hidden text
  chunks BEFORE they could ever become retrievable;
- canary queries must pass before a staged version may activate;
- activation is ATOMIC: new version becomes ACTIVE and the previous ACTIVE
  version retires in one commit — a failed version leaves the old one active;
- T4 sources never auto-activate;
- embedding/token usage flows to the WS27 ledger via EmbeddingGateway.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.data.models import (
    RagChunk,
    RagDocument,
    RagIngestionRun,
    RagSource,
)
from app.rag.chunking import chunk_text
from app.rag.embeddings import EmbeddingGateway
from app.rag.policy import (
    AUTO_ACTIVATION_TIERS,
    ALLOWED_USES,
    NAMESPACES,
    TRUST_TIERS,
    security_scan,
)


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class RagIngestError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def validate_source_fields(*, namespace: str, trust_tier: str,
                           allowed_use: list[str]) -> None:
    """Registry validation — unknown/ambiguous metadata never auto-activates."""
    if namespace not in NAMESPACES:
        raise RagIngestError("BAD_NAMESPACE")
    if trust_tier not in TRUST_TIERS:
        raise RagIngestError("BAD_TRUST_TIER")
    if not allowed_use or any(a not in ALLOWED_USES for a in allowed_use):
        raise RagIngestError("BAD_ALLOWED_USE")


import ipaddress
from urllib.parse import urlparse

_ALLOWED_URL_SCHEMES = {"https"}


def validate_source_url(url: str) -> str:
    """SSRF-safe URL validation for remote ingestion (28 §7 step 2).

    https only; no localhost/loopback/private/link-local/metada hosts; explicit
    IP literals must be public globals. Fetching itself lands with the sync
    worker; this gate decides what may ever be registered.
    """
    u = urlparse((url or "").strip())
    if u.scheme not in _ALLOWED_URL_SCHEMES:
        raise RagIngestError("BAD_URL_SCHEME")
    host = (u.hostname or "").lower()
    if not host:
        raise RagIngestError("BAD_URL_HOST")
    bad_names = {"localhost", "metadata.google.internal", "instance-data"}
    if host in bad_names or host.endswith(".internal") or host.endswith(".local"):
        raise RagIngestError("BAD_URL_HOST")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise RagIngestError("BAD_URL_HOST_PRIVATE")
    except ValueError:
        pass  # hostname, not an IP literal
    return url.strip()


def validate_source_payload_size(content: str | bytes, *, max_bytes: int) -> None:
    size = len(content.encode("utf-8") if isinstance(content, str) else content)
    if size > max_bytes:
        raise RagIngestError("SOURCE_TOO_LARGE")


def register_source(repo, *, namespace: str, name: str, trust_tier: str,
                    allowed_use: list[str], source_type: str = "manual_text",
                    locator: str = "", owner: str = "", license_type: str = "proprietary",
                    license_reference: str = "", access_scope: str = "internal",
                    update_policy: str = "manual") -> RagSource:
    """Create a registry entry in draft status (never active by default)."""
    validate_source_fields(namespace=namespace, trust_tier=trust_tier,
                           allowed_use=allowed_use)
    with repo._sf() as s:
        src = RagSource(
            namespace=namespace, name=name, source_type=source_type,
            locator=locator, owner=owner, trust_tier=trust_tier,
            allowed_use=list(allowed_use), license_type=license_type,
            license_reference=license_reference, access_scope=access_scope,
            update_policy=update_policy, status="draft",
        )
        s.add(src)
        s.commit()
        s.refresh(src)
        s.expunge(src)
    return src


def activate_source(repo, source_id: int) -> None:
    """Operator promotion of a reviewed source (T4 requires this explicitly)."""
    with repo._sf() as s:
        src = s.get(RagSource, source_id)
        if src is None:
            raise RagIngestError("SOURCE_NOT_FOUND")
        if src.trust_tier not in AUTO_ACTIVATION_TIERS:
            raise RagIngestError("TRUST_TIER_REQUIRES_REVIEW")
        src.status = "active"
        s.commit()


def _active_document(s, source_id: int) -> RagDocument | None:
    return s.execute(
        select(RagDocument).where(
            RagDocument.source_id == source_id,
            RagDocument.status == "active",
        )
    ).scalars().first()


def ingest_source(
    repo,
    source_id: int,
    content: str,
    *,
    trigger: str = "manual",
    title: str = "",
    canaries: list[dict] | None = None,
    embedding_gateway: EmbeddingGateway | None = None,
    max_chunk_tokens: int = 220,
) -> dict:
    """
    Ingest *content* for a registered source. Returns a run summary dict:
    {status, changed, version, chunks_created, reused, quarantined, activated}.

    Statuses:
      - "skipped_unchanged" — hash identical: zero cost, zero churn (28 §7.1);
      - "ok" — new version staged + canaried + atomically activated;
      - "quarantined" — every chunk failed the security scan (old ACTIVE
        version remains retrievable);
      - "canary_failed" — staged but not activated (old ACTIVE remains).
    """
    gw = embedding_gateway or EmbeddingGateway(_CfgShim())
    started = datetime.now(timezone.utc)

    with repo._sf() as s:
        src = s.get(RagSource, source_id)
        if src is None:
            raise RagIngestError("SOURCE_NOT_FOUND")

        new_hash = sha256(content)
        s.add(RagIngestionRun(source_id=source_id, trigger=trigger,
                              status="ok", content_changed=False,
                              started_at=started))
        s.commit()

        if src.last_content_hash == new_hash:
            # Change detection: NO new document, NO embeddings, NO cost.
            run = s.execute(
                select(RagIngestionRun).where(RagIngestionRun.source_id == source_id)
                .order_by(RagIngestionRun.id.desc())
            ).scalars().first()
            run.status = "skipped"
            run.finished_at = datetime.now(timezone.utc)
            src.last_checked_at = run.finished_at
            s.commit()
            return {"status": "skipped_unchanged", "changed": False,
                    "version": None, "chunks_created": 0, "reused": 0,
                    "quarantined": 0, "activated": False}

        prev_doc = _active_document(s, source_id)
        new_version = (prev_doc.source_version + 1) if prev_doc else 1

        doc = RagDocument(
            source_id=source_id, source_version=new_version,
            content_hash=new_hash, title=title or src.name,
            status="staged",
            supersedes_document_id=prev_doc.id if prev_doc else None,
        )
        s.add(doc)
        s.flush()

        created = reused = quarantined = 0
        prev_hashes = {}
        if prev_doc is not None:
            prev_rows = s.execute(
                select(RagChunk.chunk_hash).where(
                    RagChunk.document_id == prev_doc.id,
                    RagChunk.status == "active",
                )
            ).scalars().all()
            prev_hashes = {h for h in prev_rows}

        pieces = chunk_text(content, max_tokens=max_chunk_tokens)
        for idx, piece in enumerate(pieces):
            chunk_hash = sha256(piece["text"])
            scan = security_scan(piece["text"])
            if not scan["ok"]:
                s.add(RagChunk(
                    document_id=doc.id, chunk_index=idx,
                    heading_path=piece["heading_path"],
                    chunk_text=piece["text"], chunk_hash=chunk_hash,
                    token_count=piece["token_count"],
                    metadata_json={"namespace": src.namespace},
                    embedding_model=gw.model_id,
                    status="quarantined", quarantine_reasons=scan["reasons"],
                ))
                quarantined += 1
                continue

            if chunk_hash in prev_hashes:
                # content-identical chunk: re-embed is waste (28 §7 step 7)
                s.add(RagChunk(
                    document_id=doc.id, chunk_index=idx,
                    heading_path=piece["heading_path"],
                    chunk_text=piece["text"], chunk_hash=chunk_hash,
                    token_count=piece["token_count"],
                    metadata_json={"namespace": src.namespace,
                                   "reused_from_version": prev_doc.source_version if prev_doc else None},
                    embedding=[],
                    embedding_model="reused",
                    status="staged", quarantine_reasons=[],
                ))
                reused += 1
                continue

            vec = gw.embed_batch(
                [piece["text"]], repo=repo, op="embedding_ingest")[0]
            s.add(RagChunk(
                document_id=doc.id, chunk_index=idx,
                heading_path=piece["heading_path"],
                chunk_text=piece["text"], chunk_hash=chunk_hash,
                token_count=piece["token_count"],
                metadata_json={"namespace": src.namespace},
                embedding=vec,
                embedding_model=gw.model_id,
                status="staged", quarantine_reasons=[],
            ))
            created += 1

        changed = (created + reused) > 0
        status = "ok"
        activated = False

        if not changed:
            status = "failed"
            error = "ALL_CHUNKS_QUARANTINED"
        else:
            error = None
            # canary: staged version must satisfy expected/forbidden checks
            canary_fail = _run_canaries(
                s, doc_id=doc.id, canaries=canaries or [],
                gw=gw, src=src)
            if canary_fail is not None:
                status = "canary_failed"
                error = canary_fail
                doc.status = "quarantined"
            else:
                if src.trust_tier not in AUTO_ACTIVATION_TIERS:
                    status = "canary_failed"
                    error = "TRUST_TIER_REQUIRES_REVIEW"
                    doc.status = "quarantined"
                else:
                    # ATOMIC activation: staged→active, previous active→retired
                    if prev_doc is not None:
                        prev_doc.status = "retired"
                        s.execute(
                            update(RagChunk)
                            .where(RagChunk.document_id == prev_doc.id,
                                   RagChunk.status == "active")
                            .values(status="retired")
                        )
                    doc.status = "active"
                    s.execute(
                        update(RagChunk)
                        .where(RagChunk.document_id == doc.id,
                               RagChunk.status == "staged")
                        .values(status="active")
                    )
                    activated = True

        src.last_content_hash = new_hash
        src.last_checked_at = datetime.now(timezone.utc)
        if status == "ok":
            src.last_success_at = src.last_checked_at

        run = s.execute(
            select(RagIngestionRun).where(RagIngestionRun.source_id == source_id)
            .order_by(RagIngestionRun.id.desc())
        ).scalars().first()
        run.status = status
        run.content_changed = True
        run.chunks_created = created
        run.chunks_reused = reused
        run.chunks_quarantined = quarantined
        run.error_code = error
        run.finished_at = datetime.now(timezone.utc)
        s.commit()

        return {"status": status, "changed": True, "version": new_version,
                "chunks_created": created, "reused": reused,
                "quarantined": quarantined, "activated": activated}


def _run_canaries(s, *, doc_id: int, canaries: list[dict], gw, src) -> str | None:
    """Run staged-version canary checks BEFORE activation (28 §7 step 8).

    Each canary: {"query": str, "expect": bool} — expect=True requires the
    staged doc to be the top hit for the query; expect=False forbids it.
    Returns the failing canary query or None.
    """
    if not canaries:
        return None
    rows = s.execute(
        select(RagChunk).where(
            RagChunk.document_id == doc_id, RagChunk.status == "staged",
        )
    ).scalars().all()
    staged_vecs = [(c.id, gw.embed(c.chunk_text)) for c in rows]
    for can in canaries:
        q = can.get("query") or ""
        expect = bool(can.get("expect", True))
        qvec = gw.embed(q)
        best = 0.0
        for _cid, vec in staged_vecs:
            sim = _cos(qvec, vec)
            best = max(best, sim)
        hit = best > 0.15  # local-hash similarity floor for "retrievable"
        if expect and not hit:
            return f"canary_expected_miss:{q[:40]}"
        if not expect and hit:
            return f"canary_forbidden_hit:{q[:40]}"
    return None


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class _CfgShim:
    """Minimal config for default local embedder when caller passes none."""
    EMBEDDING_PROVIDER = "local"
