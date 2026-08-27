"""WS09-03B — systematic server-side request contracts.

Every public route parses its body through ``parse_body`` (Pydantic model in,
validated object out). Client/TypeScript validation is never a security or
persistence boundary:

- malformed/missing JSON → stable 400 INVALID_JSON;
- schema violations (lengths, enums, ranges, cardinality) → 422 VALIDATION
  BEFORE any LLM, ASR, or database work;
- unknown fields are ignored (forward-compatible) but never forwarded into
  prompts, persistence, or analytics — routes read only model fields.
"""
from flask import request
from pydantic import BaseModel, ValidationError

from .errors import ApiError


def parse_body(model: type[BaseModel]):
    """Parse+validate the request JSON body against ``model`` (fail cheaply,
    before expensive work). Returns the validated model instance."""
    raw = request.get_json(force=True, silent=True)
    if not isinstance(raw, dict):
        raise ApiError("INVALID_JSON", "Expected a JSON object body", 400)
    try:
        return model.model_validate(raw)
    except ValidationError as e:
        raise ApiError("VALIDATION", "Invalid request", 422, _safe_details(e))


def _safe_details(e: ValidationError):
    """JSON-safe, payload-free validation details: field paths + machine
    types + messages only (raw ctx values may hold non-serializable objects,
    and echoing input would leak nothing but bloat error responses)."""
    details = []
    for err in e.errors(include_url=False, include_input=False):
        details.append({
            "field": ".".join(map(str, err.get("loc", ()))),
            "type": err.get("type"),
            "message": err.get("msg"),
        })
    return details
