from flask import Blueprint, jsonify, request, session
from application.profile import (
    get_profile,
    validate_profile,
    update_profile,
    get_preferences,
    validate_preferences,
    update_preferences,
    get_tenant_preferences,
    update_tenant_preferences,
)


def create_profile_blueprint(user_repo):
    """Return a Blueprint with profile/preferences routes wired to user_repo."""
    bp = Blueprint("profile", __name__)

    @bp.before_request
    def _check_auth():
        if not session.get("user_id"):
            return jsonify({"error": "unauthorized"}), 401

    @bp.get("/auth/me/profile")
    def _get_profile():
        return jsonify(get_profile(session["user_id"], user_repo))

    @bp.patch("/auth/me/profile")
    def _update_profile():
        body = request.get_json(force=True) or {}
        errors = validate_profile(body)
        if errors:
            return jsonify({"error": "invalid_fields", "fieldErrors": errors}), 400
        return jsonify(update_profile(session["user_id"], body, user_repo))

    @bp.get("/auth/me/preferences")
    def _get_preferences():
        return jsonify(get_preferences(session["user_id"], user_repo))

    @bp.patch("/auth/me/preferences")
    def _update_preferences():
        user_id = session["user_id"]
        body = request.get_json(force=True) or {}
        errors = validate_preferences(body)
        if errors:
            return jsonify({"error": "invalid_fields", "fieldErrors": errors}), 400
        return jsonify(update_preferences(user_id, body, user_repo))

    @bp.get("/auth/me/tenant-preferences")
    def _get_tenant_preferences():
        result = get_tenant_preferences(session["user_id"], user_repo)
        if result is None:
            return jsonify({"default_home_app": None, "notify_app_ids": []})
        return jsonify(result)

    @bp.patch("/auth/me/tenant-preferences")
    def _update_tenant_preferences():
        user_id = session["user_id"]
        body = request.get_json(force=True) or {}
        result, error = update_tenant_preferences(user_id, body, user_repo)
        if error == "not_a_tenant_member":
            return jsonify({"error": "not_a_tenant_member"}), 403
        if error:
            return jsonify({"error": error}), 400
        return jsonify(result)

    return bp
