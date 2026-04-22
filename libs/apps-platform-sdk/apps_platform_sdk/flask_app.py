from __future__ import annotations

import os

from flask import Flask
from flask_cors import CORS

from .observability import setup_logging
from .errors import register_error_handlers


def configure_app(
    app: Flask,
    *,
    cors_resources: dict | None = None,
    configure_session: bool = True,
) -> Flask:
    """Apply platform-standard configuration to a Flask app.

    Wires up structured logging, unified error handlers, optional CORS, and
    secure session-cookie defaults. Returns the same app for chaining.
    """
    setup_logging(app)
    register_error_handlers(app)

    if cors_resources is not None:
        CORS(app, resources=cors_resources)

    if configure_session:
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
        app.config["SESSION_COOKIE_SECURE"] = (
            os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
        )

    return app
