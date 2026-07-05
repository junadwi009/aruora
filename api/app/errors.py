from flask import jsonify

class ApiError(Exception):
    def __init__(self, code, message, status=400, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or []

def error_response(err: ApiError):
    return jsonify({"error": {"code": err.code, "message": err.message, "details": err.details}}), err.status

def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _handle(err):
        return error_response(err)

    @app.errorhandler(404)
    def _nf(_e):
        return error_response(ApiError("NOT_FOUND", "Resource not found", 404))

    @app.errorhandler(413)
    def _too_large(_e):
        return error_response(ApiError("PAYLOAD_TOO_LARGE", "Request body is too large", 413))

    @app.errorhandler(500)
    def _ise(_e):
        return error_response(ApiError("INTERNAL", "Internal error", 500))
