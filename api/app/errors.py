"""WS09-08 — stable public error contract.

Every error the API emits is JSON of the shape
    {"error": {"code", "message", "details", "requestId"}}
- never a stack trace, SQL/provider payload, or credential material;
- full exception detail goes to server logs only (never the response body);
- `requestId` correlates a client-reported failure with server logs without
  exposing anything sensitive (it is a random or client-supplied opaque id).
"""
import re

from flask import g, jsonify, current_app, request

from werkzeug.exceptions import HTTPException

class ApiError(Exception):
    def __init__(self, code, message, status=400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or []

def error_response(err: ApiError):
    body = {"error": {
        "code": err.code,
        "message": err.message,
        "details": err.details,
        "requestId": request_id(),
    }}
    return jsonify(body), err.status

# Opaque correlation id: prefer the caller's X-Request-ID (sanitized), else a
# random short id. Anything non-conforming is discarded (never reflected raw).
_REQ_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

def request_id() -> str:
    rid = getattr(g, "request_id", None)
    if rid:
        return rid
    incoming = request.headers.get("X-Request-ID") or ""
    rid = incoming if _REQ_ID_RE.match(incoming) else ""
    if not rid:
        import uuid

        rid = uuid.uuid4().hex[:16]
    g.request_id = rid
    return rid

def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _handle(err):
        return error_response(err)

    @app.errorhandler(404)
    def _nf(_e):
        return error_response(ApiError("NOT_FOUND", "Resource not found", 404))

    @app.errorhandler(405)
    def _method(_e):
        return error_response(ApiError("METHOD_NOT_ALLOWED", "Method not allowed", 405))

    @app.errorhandler(413)
    def _too_large(_e):
        return error_response(ApiError("PAYLOAD_TOO_LARGE", "Request body is too large", 413))

    @app.errorhandler(400)
    def _bad_request(_e):
        # Malformed JSON / unparsable body (e.g. request.get_json raising).
        return error_response(ApiError("INVALID_JSON", "Malformed request body", 400))

    @app.errorhandler(Exception)
    def _unhandled(e):
        # WS09-08: the public body is a stable, detail-free JSON object. The
        # traceback goes to protected server logs only.
        current_app.logger.exception("unhandled error path=%s method=%s",
                                     request.path, request.method)
        if isinstance(e, HTTPException):
            # Any other HTTPException keeps its status but the safe JSON shape.
            return error_response(ApiError("REQUEST_ERROR", e.name, e.code or 500))
        return error_response(ApiError("INTERNAL", "Internal error", 500))
