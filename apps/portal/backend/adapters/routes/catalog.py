from flask import Blueprint, jsonify, request, session

import application.catalog as uc
from domain.errors import ForbiddenError, NotFoundError, ValidationError


def create_catalog_blueprint(plugin_repo, tenant_repo, audit):
    bp = Blueprint("catalog", __name__)

    @bp.before_request
    def _check_auth():
        if not session.get("user_id"):
            return jsonify({"error": "unauthorized"}), 401

    @bp.get("/api/catalog")
    def get_catalog():
        return jsonify(uc.get_catalog(session["user_id"], plugin_repo, tenant_repo))

    @bp.get("/api/audit")
    def get_audit_log():
        try:
            limit = min(int(request.args.get("limit", 20)), 100)
        except (TypeError, ValueError):
            limit = 20
        return jsonify(uc.get_audit_log(session["user_id"], limit, audit))

    @bp.get("/api/admin/audit")
    def get_admin_audit_log():
        try:
            return jsonify(uc.get_admin_audit_log(session["user_id"], request.args, audit, tenant_repo))
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403

    @bp.get("/api/tenants/<tenant_id>/installs")
    def list_installs(tenant_id: str):
        try:
            return jsonify(uc.list_installs(tenant_id, session["user_id"], plugin_repo, tenant_repo))
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403

    @bp.post("/api/tenants/<tenant_id>/installs")
    def install_plugin(tenant_id: str):
        body = request.get_json(force=True) or {}
        try:
            uc.install_plugin(tenant_id, session["user_id"], body, plugin_repo, tenant_repo, audit)
            return jsonify({"ok": True})
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403
        except ValidationError as e:
            return jsonify({"error": e.errors}), 400
        except NotFoundError as e:
            return jsonify({"error": e.code}), 404

    @bp.patch("/api/tenants/<tenant_id>/installs/<plugin_id>")
    def update_install(tenant_id: str, plugin_id: str):
        body = request.get_json(force=True) or {}
        try:
            uc.update_install_status(
                tenant_id, session["user_id"], plugin_id, body, plugin_repo, tenant_repo, audit
            )
            return jsonify({"ok": True})
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403
        except ValidationError as e:
            return jsonify({"error": e.errors}), 400
        except NotFoundError as e:
            return jsonify({"error": e.code}), 404

    @bp.delete("/api/tenants/<tenant_id>/installs/<plugin_id>")
    def uninstall_plugin(tenant_id: str, plugin_id: str):
        try:
            uc.uninstall_plugin(
                tenant_id, session["user_id"], plugin_id, plugin_repo, tenant_repo, audit
            )
            return jsonify({"ok": True})
        except ForbiddenError:
            return jsonify({"error": "forbidden"}), 403

    return bp
