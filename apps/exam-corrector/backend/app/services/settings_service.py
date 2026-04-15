import json
import os
import threading

from app import config

_SETTINGS_PATH = os.path.join(config.UPLOAD_FOLDER, "settings.json")
_lock = threading.Lock()


def _load() -> dict:
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    tmp = _SETTINGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _SETTINGS_PATH)


def get_status() -> dict:
    return {"engine": "omr-cv"}
