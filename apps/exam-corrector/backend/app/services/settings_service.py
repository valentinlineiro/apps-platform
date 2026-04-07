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


def get_gemini_api_key() -> str:
    """Return the effective API key: stored value takes precedence over env var."""
    with _lock:
        stored = _load().get("gemini_api_key", "").strip()
    return stored or config.GEMINI_API_KEY


def set_gemini_api_key(key: str) -> None:
    with _lock:
        data = _load()
        data["gemini_api_key"] = key.strip()
        _save(data)


def clear_gemini_api_key() -> None:
    with _lock:
        data = _load()
        data.pop("gemini_api_key", None)
        _save(data)


def get_status() -> dict:
    """Return key status safe for the frontend (masked, never the raw value)."""
    with _lock:
        stored = _load().get("gemini_api_key", "").strip()
    env_key = config.GEMINI_API_KEY

    if stored:
        source = "custom"
        masked = _mask(stored)
    elif env_key:
        source = "env"
        masked = _mask(env_key)
    else:
        source = "none"
        masked = ""

    return {"source": source, "masked": masked}


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "••••••••"
    return "••••••••" + key[-4:]
