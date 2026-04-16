from flask import Blueprint, jsonify

from app.services import template_service

bp = Blueprint("templates", __name__)


@bp.route("/exam-corrector/api/templates", methods=["GET"])
def api_templates():
    return jsonify({"ok": True, "templates": template_service.listar_templates_guardadas()})


@bp.route("/exam-corrector/api/templates/<template_id>", methods=["DELETE"])
def delete_template(template_id: str):
    deleted = template_service.eliminar_template(template_id)
    if not deleted:
        return jsonify({"ok": False, "error": "template_not_found"}), 404
    return jsonify({"ok": True})
