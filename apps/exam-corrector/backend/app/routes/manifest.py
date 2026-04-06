from flask import Blueprint, jsonify

bp = Blueprint("manifest", __name__)


@bp.route("/apps/exam-corrector/manifest.json")
def manifest():
    return jsonify({
        "id": "exam-corrector",
        "name": "exam-corrector",
        "description": "Corrección automática de exámenes con Gemini Vision",
        "route": "exam-corrector",
        "icon": "📝",
        "status": "stable",
        "backend": {"pathPrefix": "/exam-corrector/"}
    })
