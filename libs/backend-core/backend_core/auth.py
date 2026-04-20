"""Auth helpers shared across app backends.

require_session — decorator that guards a route behind an active portal session.
                  Returns the unified 401 error contract when the session is absent.
"""
from __future__ import annotations

import functools
from flask import session, jsonify, g


def require_session(fn):
    """Decorator: require an active portal session (session['user_id'] must be set)."""
    @functools.wraps(fn)
    def _wrapper(*args, **kwargs):
        if not session.get("user_id"):
            body = {"error": "unauthorized", "message": "Authentication required."}
            trace_id = getattr(g, "trace_id", None)
            if trace_id:
                body["traceId"] = trace_id
            return jsonify(body), 401
        return fn(*args, **kwargs)
    return _wrapper
