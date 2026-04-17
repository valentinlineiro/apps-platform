from flask import Blueprint, jsonify, request, session

import application.tenant_settings as uc
from domain.errors import ForbiddenError, NotFoundError, ValidationError


def create_tenant_settings_blueprint(tenant_repo, audit):
    bp = Blueprint("tenant_settings", __name__)

    @bp.before_request
    def _check_auth():
        if not session.get("user_id"):
            return jsonify({"error": "unauthorized"}), 401

    @bp.get("/api/tenants/current")
    def get_current_tenant():
        try:
            return jsonify(uc.get_current_tenant(session["user_id"], tenant_repo))
        except ForbiddenError as e:
            return jsonify({"error": e.code}), 403

    @bp.get("/api/tenants/<tenant_id>/settings")
    def get_settings(tenant_id: str):
        try:
            return jsonify(uc.get_settings(tenant_id, session["user_id"], tenant_repo))
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403
        except NotFoundError:
            return jsonify({"error": "not_found"}), 404

    @bp.patch("/api/tenants/<tenant_id>/settings")
    def update_settings(tenant_id: str):
        body = request.get_json(force=True) or {}
        try:
            return jsonify(
                uc.update_settings(tenant_id, session["user_id"], body, tenant_repo, audit)
            )
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403
        except ValidationError as e:
            return jsonify({"error": "invalid_fields", "fieldErrors": e.errors}), 400
        except NotFoundError:
            return jsonify({"error": "not_found"}), 404

    @bp.get("/api/tenants/<tenant_id>/members")
    def list_members(tenant_id: str):
        try:
            return jsonify(uc.list_members(tenant_id, session["user_id"], tenant_repo))
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403

    @bp.post("/api/tenants/<tenant_id>/members")
    def add_member(tenant_id: str):
        body = request.get_json(force=True) or {}
        try:
            uc.add_member(tenant_id, session["user_id"], body, tenant_repo, audit)
            return jsonify({"ok": True})
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403
        except ValidationError as e:
            return jsonify({"error": e.errors}), 400
        except NotFoundError as e:
            return jsonify({"error": e.code}), 404

    @bp.delete("/api/tenants/<tenant_id>/members/<user_id>")
    def remove_member(tenant_id: str, user_id: str):
        try:
            uc.remove_member(tenant_id, user_id, session["user_id"], tenant_repo, audit)
            return jsonify({"ok": True})
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403
        except ValidationError as e:
            return jsonify({"error": e.errors}), 400

    return bp
