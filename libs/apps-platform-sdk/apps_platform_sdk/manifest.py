from flask import Blueprint, jsonify


def create_manifest_blueprint(manifest: dict) -> Blueprint:
    """Return a Blueprint that serves GET /manifest with the given manifest dict."""
    bp = Blueprint("manifest", __name__)

    @bp.get("/manifest")
    def _manifest():
        return jsonify(manifest)

    return bp
