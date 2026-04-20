"""Unified error contract for all app backends.

Every error response has the shape:
    {
        "error":       "<machine_readable_code>",
        "message":     "<human_readable_description>",
        "fieldErrors": {"field": "reason", ...},  # omitted when empty
        "traceId":     "<uuid>"                   # omitted when not set
    }
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from flask import Flask, jsonify, g


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status: int = 400
    field_errors: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        body: dict = {"error": self.code, "message": self.message}
        if self.field_errors:
            body["fieldErrors"] = self.field_errors
        trace_id = getattr(g, "trace_id", None)
        if trace_id:
            body["traceId"] = trace_id
        return body


def error_response(
    code: str,
    message: str,
    status: int = 400,
    field_errors: dict[str, str] | None = None,
):
    """Return a Flask JSON response conforming to the unified error contract."""
    body: dict = {"error": code, "message": message}
    if field_errors:
        body["fieldErrors"] = field_errors
    trace_id = getattr(g, "trace_id", None)
    if trace_id:
        body["traceId"] = trace_id
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    """Register unified error handlers on a Flask app."""

    @app.before_request
    def _set_trace_id():
        g.trace_id = str(uuid.uuid4())

    @app.errorhandler(ApiError)
    def _handle_api_error(exc: ApiError):
        return jsonify(exc.to_dict()), exc.status

    @app.errorhandler(404)
    def _not_found(_e):
        return error_response("not_found", "Resource not found.", 404)

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return error_response("method_not_allowed", "Method not allowed.", 405)

    @app.errorhandler(500)
    def _internal_error(_e):
        return error_response("internal_error", "An unexpected error occurred.", 500)
