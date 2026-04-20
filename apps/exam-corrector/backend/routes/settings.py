from flask import Blueprint, jsonify

from services import settings_service

bp = Blueprint("settings", __name__)


@bp.route("/exam-corrector/api/settings", methods=["GET"])
def get_settings():
    return jsonify({"ok": True, **settings_service.get_status()})
