"""
Registers this app with the portal's registry backend on startup
and sends periodic heartbeats so it stays visible in the directory.
"""
import os
import threading
import time

import requests

PORTAL_BACKEND_URL = os.environ.get("PORTAL_BACKEND_URL", "http://portal-backend:5000")
HEARTBEAT_INTERVAL = 30  # seconds between heartbeats
RETRY_INTERVAL = 5       # seconds between registration retries

MANIFEST = {
    "manifestVersion": 1,
    "id": "exam-corrector",
    "name": "exam-corrector",
    "description": "Corrección automática de exámenes con Gemini Vision",
    "route": "exam-corrector",
    "icon": "📝",
    "status": "stable",
    "scriptUrl": "/apps/exam-corrector/element/main.js",
    "elementTag": "exam-corrector-app",
    "backend": {"pathPrefix": "/exam-corrector/"},
}


def _try_register() -> bool:
    try:
        r = requests.post(
            f"{PORTAL_BACKEND_URL}/api/registry/register",
            json=MANIFEST,
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _try_heartbeat() -> bool:
    try:
        r = requests.post(
            f"{PORTAL_BACKEND_URL}/api/registry/heartbeat/exam-corrector",
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _loop() -> None:
    # Retry until registered
    while not _try_register():
        time.sleep(RETRY_INTERVAL)

    # Heartbeat loop — re-register if heartbeat fails
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        if not _try_heartbeat():
            while not _try_register():
                time.sleep(RETRY_INTERVAL)


def start() -> None:
    threading.Thread(target=_loop, daemon=True).start()
