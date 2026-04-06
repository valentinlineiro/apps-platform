from flask import Blueprint, jsonify

from app.services import template_service

bp = Blueprint("templates", __name__)


@bp.route("/exam-corrector/api/templates", methods=["GET"])
def api_templates():
    return jsonify({"ok": True, "templates": template_service.listar_templates_guardadas()})
