"""
WS28 — RAG policy: namespaces, trust tiers, allowed use, and the
authorization-before-retrieval contract.

The policy layer is the ONLY place that decides which namespaces a use case
may query. Retrieval code receives validated namespaces — it can never be
handed an arbitrary collection selector by a client (28 §8.1/§4).

Key invariants enforced here:
- allowlist-first source registry semantics (no auto-activation of unknown
  sources — T4 candidates never auto-activate);
- a source approved for one use is NOT automatically approved for another
  (help_answer ≠ task_generation_reference);
- calibrated scoring never performs open-ended dynamic retrieval;
- retrieved content is UNTRUSTED data: the security scan flags instruction-
  like and hidden text so chunks can be quarantined before indexing.
"""

from __future__ import annotations

import re

# ── Namespaces ────────────────────────────────────────────────────────────────

NAMESPACES = {
    "aruora_product",
    "aruora_help",
    "ielts_rules",
    "pedagogy",
    "content_reference",
    "brand_voice",
    "legal_policy",
    "operations_internal",
    # Future, explicitly disabled until a validated feature needs them:
    # "user_private", "institution_private", "mentor_private",
}

FORBIDDEN_NAMESPACES = {
    "user_private",
    "institution_private",
    "mentor_private",
}

# ── Trust tiers (21... 28 §5) ────────────────────────────────────────────────

TRUST_TIERS = {"T0", "T1", "T2", "T3", "T4"}
# T4 = untrusted candidate; never auto-activates into production retrieval.
AUTO_ACTIVATION_TIERS = {"T0", "T1", "T2", "T3"}

ALLOWED_USES = {
    "policy_grounding",
    "help_answer",
    "pedagogy_guidance",
    "factual_grounding",
    "task_generation_reference",
    "validation_reference",
    "internal_only",
}

# ── Use-case → authorized namespace sets ─────────────────────────────────────
# Each use case declares EXACTLY the namespaces it may see. "Scoring" has NO
# dynamic retrieval namespace set at all (28 §1.5): calibrated scoring must
# never depend on changing retrieval results.

USE_CASE_NAMESPACES: dict[str, frozenset[str]] = {
    "task_generation": frozenset({"pedagogy", "content_reference", "ielts_rules"}),
    "help_answer": frozenset({"aruora_help", "aruora_product", "ielts_rules"}),
    "aura_advice": frozenset({"pedagogy", "aruora_help"}),
    "content_validation": frozenset({"ielts_rules", "content_reference"}),
    # Scoring: no open-namespace retrieval. Frozen exemplar packs bypass RAG.
    "scoring": frozenset(),
}

# Every retrieval within a use case may additionally require a specific
# allowed_use classification on the source.
USE_CASE_ALLOWED_USE: dict[str, frozenset[str]] = {
    "task_generation": frozenset({"task_generation_reference", "factual_grounding"}),
    "help_answer": frozenset({"help_answer", "policy_grounding"}),
    "aura_advice": frozenset({"pedagogy_guidance", "help_answer"}),
    "content_validation": frozenset({"validation_reference", "policy_grounding"}),
    "scoring": frozenset(),
}


class RagPolicyError(Exception):
    """Raised when a retrieval request violates the authorization policy."""


def authorize_use_case(use_case: str, requested_namespaces=None) -> frozenset[str]:
    """
    Resolve + authorize namespaces for a use case. Called BEFORE any
    similarity search happens (pre-filter, never post-filter).

    Raises RagPolicyError for unknown use cases, forbidden namespaces, or any
    namespace outside the use case's authorization set.
    """
    allowed = USE_CASE_NAMESPACES.get(use_case)
    if allowed is None:
        raise RagPolicyError(f"unknown use_case {use_case!r}")
    if use_case == "scoring":
        raise RagPolicyError("dynamic RAG is not part of calibrated scoring")
    if not requested_namespaces:
        return allowed
    requested = frozenset(requested_namespaces)
    if requested & FORBIDDEN_NAMESPACES:
        raise RagPolicyError("private namespaces are not retrievable")
    if not requested <= allowed:
        raise RagPolicyError(
            f"namespaces {sorted(requested - allowed)} not authorized for {use_case!r}"
        )
    return requested


def authorized_allowed_use(use_case: str) -> frozenset[str]:
    return USE_CASE_ALLOWED_USE.get(use_case, frozenset())


# ── Content security scan (28 §7 step 6) ─────────────────────────────────────

# Detection ≠ solved injection: quarantining keeps poisoned text out of the
# ACTIVE index; runtime isolation in the LLM gateway remains the real defence.
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*[:=]", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(instructions|prompt|rubric|rules)", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(system|assistant|developer)\s*>", re.IGNORECASE),
]
_HIDDEN_TEXT_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")


def security_scan(text: str) -> dict:
    """Scan untrusted source text for poisoning indicators.

    Returns {"ok": bool, "reasons": [..]} — a failing scan sends the chunk to
    quarantine instead of the ACTIVE index. Detection is best-effort; source
    governance + gateway isolation remain required (spec §9).
    """
    reasons: list[str] = []
    for rx in _INJECTION_PATTERNS:
        if rx.search(text or ""):
            reasons.append(f"prompt_like:{rx.pattern[:24]}")
    if _HIDDEN_TEXT_RE.search(text or ""):
        reasons.append("hidden_text")
    return {"ok": not reasons, "reasons": reasons}


# ── Copyright originality guard (28 §15) ─────────────────────────────────────

def _token_set(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) > 2}


def near_duplicate_ratio(source_text: str, generated_text: str) -> float:
    """
    Long-word-copy ratio between retrieved source and generated task text.
    Used to reject outputs that reproduce long source wording instead of
    creating original ARUORA content. Pure lexical guard — semantic
    near-duplicate checks land with measured evaluation data.
    """
    src = _token_set(source_text)
    if not src:
        return 0.0
    gen = _token_set(generated_text)
    if not gen:
        return 0.0
    overlap = len(src & gen)
    return overlap / min(len(src), len(gen))