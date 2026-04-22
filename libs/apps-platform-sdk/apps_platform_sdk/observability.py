import json
import logging
import os
import sys
import time
import uuid
import traceback
from flask import request, current_app, g, session

# ── ANSI colour codes ──────────────────────────────────────────────────────────
_R   = "\033[0m"
_DIM = "\033[2m"
_RED = "\033[31m"
_YEL = "\033[33m"
_GRN = "\033[32m"
_CYN = "\033[36m"
_GRY = "\033[90m"

_LEVEL_FMT = {
    "DEBUG":    (_DIM,          "DEBUG  "),
    "INFO":     (_GRN,          "INFO   "),
    "WARNING":  (_YEL,          "WARNING"),
    "ERROR":    (_RED,          "ERROR  "),
    "CRITICAL": (_RED + "\033[1m", "CRITICAL"),
}


class TextFormatter(logging.Formatter):
    """Human-readable single-line formatter with optional ANSI colour.

    Output example:
      10:18:05.909  INFO   POST /exam-corrector/start             status=200 dur=45ms
      10:18:05.912  ERROR  Exception on /exam-corrector/start     status=500 dur=3ms
        sqlite3.OperationalError: no such column: needs_review
          File "/app/app/services/batch_service.py", line 243 ...
    """

    def __init__(self, use_color: bool = True):
        super().__init__()
        self._c = use_color

    def _col(self, text: str, code: str) -> str:
        return f"{code}{text}{_R}" if self._c else text

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp: HH:MM:SS.mmm
        ts = self.formatTime(record, "%H:%M:%S")
        timestamp = self._col(f"{ts}.{int(record.msecs):03d}", _GRY)

        color, label = _LEVEL_FMT.get(record.levelname, ("", record.levelname.ljust(7)))
        level = self._col(label, color)

        message = record.getMessage()

        # Key=value extras ─────────────────────────────────────────────────────
        kv: list[str] = []

        if hasattr(record, "extra_info"):
            for k, v in record.extra_info.items():
                if k == "duration_ms":
                    kv.append(f"dur={v}ms")
                elif k == "status":
                    kv.append(f"status={v}")
                elif v is not None:
                    kv.append(f"{k}={v}")

        try:
            if request:
                req_id = getattr(g, "request_id", None)
                if req_id:
                    kv.append(f"req={req_id[:8]}")
        except RuntimeError:
            pass

        kv_str = ("  " + "  ".join(self._col(k, _CYN) for k in kv)) if kv else ""
        line = f"{timestamp}  {level}  {message}{kv_str}"

        # Exception ────────────────────────────────────────────────────────────
        if record.exc_info:
            exc = self.formatException(record.exc_info)
            indented = "\n".join("  " + ln for ln in exc.splitlines())
            line = f"{line}\n{self._col(indented, _RED)}"

        return line


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "logger": record.name,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_info"):
            log_record.update(record.extra_info)
        try:
            if request:
                log_record.update({
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr,
                    "request_id": getattr(g, "request_id", None),
                    "user_id": session.get("user_id") if "user_id" in session else None,
                    "tenant_id": getattr(g, "tenant_id", None),
                })
                if hasattr(g, "start_time"):
                    log_record["duration_ms"] = int((time.time() - g.start_time) * 1000)
        except RuntimeError:
            pass
        return json.dumps(log_record, ensure_ascii=False)


def setup_logging(app):
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    fmt = os.environ.get("LOG_FORMAT", "text").lower()
    use_color = os.environ.get("LOG_COLOR", "true").lower() not in ("0", "false", "no")

    formatter = JsonFormatter() if fmt == "json" else TextFormatter(use_color=use_color)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # Also wire the root logger so background threads (batch workers, etc.)
    # that use logging.getLogger(__name__) appear in the same format.
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(formatter)
    root.addHandler(root_handler)
    root.setLevel(logging.INFO)

    @app.before_request
    def start_timer():
        g.start_time = time.time()
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        app.logger.info(f"Request started: {request.method} {request.path}")

    @app.after_request
    def log_response(response):
        duration = int((time.time() - g.start_time) * 1000)
        log_data = {"status": response.status_code, "duration_ms": duration}
        if response.status_code >= 500:
            app.logger.error(
                f"Request failed with {response.status_code}",
                extra={"extra_info": log_data},
            )
        elif response.status_code >= 400:
            app.logger.warning(
                f"Request warning with {response.status_code}",
                extra={"extra_info": log_data},
            )
        else:
            app.logger.info("Request finished", extra={"extra_info": log_data})
        return response


def log_exception(message: str = "An unexpected error occurred") -> None:
    current_app.logger.error(message, exc_info=True)
