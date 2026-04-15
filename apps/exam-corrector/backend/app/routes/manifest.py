import os
from flask import Blueprint, jsonify, send_from_directory

bp = Blueprint("manifest", __name__)

ELEMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "element")


@bp.route("/apps/exam-corrector/manifest.json")
def manifest():
    return jsonify({
        "manifestVersion": 1,
        "id": "exam-corrector",
        "name": "exam-corrector",
        "description": "Corrección automática de exámenes tipo test con detección óptica de marcas",
        "route": "exam-corrector",
        "icon": "📝",
        "status": "stable",
        "scriptUrl": "/apps/exam-corrector/element/main.js",
        "elementTag": "exam-corrector-app",
        "backend": {"pathPrefix": "/exam-corrector/"}
    })


@bp.route("/apps/exam-corrector/element/<path:filename>")
def serve_element(filename: str):
    return send_from_directory(os.path.abspath(ELEMENT_DIR), filename)
