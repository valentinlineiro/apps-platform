import json
import logging
import sys
import time
import uuid
import traceback
from flask import request, current_app, g, session

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "logger": record.name,
        }

        # Add trace info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Add extra fields passed in 'extra' parameter
        if hasattr(record, "extra_info"):
            log_record.update(record.extra_info)

        # Add context from Flask if available
        try:
            if request:
                log_record.update({
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr,
                    "request_id": getattr(g, "request_id", None),
                    "user_id": session.get("user_id") if "user_id" in session else None,
                })
                if hasattr(g, "start_time"):
                    log_record["duration_ms"] = int((time.time() - g.start_time) * 1000)
        except RuntimeError:
            # Not in a request context
            pass

        return json.dumps(log_record, ensure_ascii=False)

def setup_logging(app):
    # Remove default handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def start_timer():
        g.start_time = time.time()
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        app.logger.info(f"Request started: {request.method} {request.path}")

    @app.after_request
    def log_response(response):
        duration = int((time.time() - g.start_time) * 1000)
        log_data = {
            "status": response.status_code,
            "duration_ms": duration,
        }
        
        if response.status_code >= 500:
            app.logger.error(
                f"Request failed with {response.status_code}", 
                extra={"extra_info": log_data}
            )
        elif response.status_code >= 400:
            app.logger.warning(
                f"Request warning with {response.status_code}", 
                extra={"extra_info": log_data}
            )
        else:
            app.logger.info(
                f"Request finished", 
                extra={"extra_info": log_data}
            )
        return response

def log_exception(message="An unexpected error occurred"):
    """
    Logs an exception with a full traceback and current request context.
    """
    current_app.logger.error(message, exc_info=True)
