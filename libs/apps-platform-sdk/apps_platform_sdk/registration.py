import os
import threading
import time
import requests
import logging

logger = logging.getLogger(__name__)

class RegistrationService:
    def __init__(self, manifest, portal_url=None, heartbeat_interval=30, retry_interval=5):
        self.manifest = manifest
        self.portal_url = portal_url or os.environ.get("PORTAL_BACKEND_URL", "http://portal-backend:5000")
        self.heartbeat_interval = heartbeat_interval
        self.retry_interval = retry_interval
        self.app_id = manifest.get("id")
        self._stop_event = threading.Event()

    def _try_register(self) -> bool:
        try:
            r = requests.post(
                f"{self.portal_url}/api/registry/register",
                json=self.manifest,
                timeout=5,
            )
            return r.ok
        except Exception as e:
            logger.debug(f"Registration failed: {e}")
            return False

    def _try_heartbeat(self) -> bool:
        try:
            r = requests.post(
                f"{self.portal_url}/api/registry/heartbeat/{self.app_id}",
                timeout=5,
            )
            return r.ok
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")
            return False

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._try_register():
                time.sleep(self.retry_interval)
                continue
            
            logger.info(f"Registered {self.app_id} successfully")
            
            while not self._stop_event.is_set():
                time.sleep(self.heartbeat_interval)
                if not self._try_heartbeat():
                    logger.warning(f"Heartbeat failed for {self.app_id}, re-registering...")
                    break

    def start(self) -> None:
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop_event.set()

def start_registration(manifest):
    service = RegistrationService(manifest)
    service.start()
    return service
