from flask import Blueprint, jsonify, request

from app.services import settings_service

bp = Blueprint("settings", __name__)


@bp.route("/exam-corrector/api/settings", methods=["GET"])
def get_settings():
    return jsonify({"ok": True, **settings_service.get_status()})


@bp.route("/exam-corrector/api/settings/gemini-key", methods=["PUT"])
def set_key():
    body = request.get_json(silent=True) or {}
    key = (body.get("key") or "").strip()
    if not key:
        return jsonify({"ok": False, "error": "La clave no puede estar vacía."}), 400
    settings_service.set_gemini_api_key(key)
    return jsonify({"ok": True, **settings_service.get_status()})


@bp.route("/exam-corrector/api/settings/gemini-key", methods=["DELETE"])
def clear_key():
    settings_service.clear_gemini_api_key()
    return jsonify({"ok": True, **settings_service.get_status()})
