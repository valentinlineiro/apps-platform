from dataclasses import asdict

from apps_platform_sdk import AuditActions
from domain.errors import ForbiddenError, NotFoundError, ValidationError
from domain.plugin import VALID_INSTALL_STATUSES
from domain.tenant import ADMIN_ROLES
from ports.audit_port import AuditPort
from ports.plugin_repository import PluginRepository
from ports.tenant_repository import TenantRepository


def list_installs(
    tenant_id: str,
    user_id: str,
    plugin_repo: PluginRepository,
    tenant_repo: TenantRepository,
) -> list[dict]:
    role = tenant_repo.get_caller_role(tenant_id, user_id)
    if role is None:
        raise ForbiddenError("forbidden")
    return [asdict(i) for i in plugin_repo.list_installs(tenant_id)]


def install_plugin(
    tenant_id: str,
    caller_id: str,
    body: dict,
    plugin_repo: PluginRepository,
    tenant_repo: TenantRepository,
    audit: AuditPort,
) -> None:
    role = tenant_repo.get_caller_role(tenant_id, caller_id)
    if not role or role not in ADMIN_ROLES:
        raise ForbiddenError("forbidden")

    plugin_id = (body.get("plugin_id") or "").strip()
    if not plugin_id:
        raise ValidationError("plugin_id is required")

    if not plugin_repo.plugin_registered(plugin_id):
        raise NotFoundError("plugin_not_found")

    plugin_repo.install(tenant_id, plugin_id, installed_by=caller_id)
    audit.log(caller_id, AuditActions.PLUGIN_INSTALLED, "plugin_install", plugin_id,
              {"tenant_id": tenant_id})


def update_install_status(
    tenant_id: str,
    caller_id: str,
    plugin_id: str,
    body: dict,
    plugin_repo: PluginRepository,
    tenant_repo: TenantRepository,
    audit: AuditPort,
) -> None:
    role = tenant_repo.get_caller_role(tenant_id, caller_id)
    if not role or role not in ADMIN_ROLES:
        raise ForbiddenError("forbidden")

    new_status = (body.get("status") or "").strip()
    if new_status not in VALID_INSTALL_STATUSES:
        raise ValidationError(
            f"status must be {', '.join(sorted(VALID_INSTALL_STATUSES))}"
        )

    updated = plugin_repo.update_status(tenant_id, plugin_id, new_status)
    if not updated:
        raise NotFoundError("install_not_found")

    audit.log(caller_id, AuditActions.PLUGIN_STATUS_UPDATED, "plugin_install", plugin_id,
              {"tenant_id": tenant_id, "status": new_status})


def uninstall_plugin(
    tenant_id: str,
    caller_id: str,
    plugin_id: str,
    plugin_repo: PluginRepository,
    tenant_repo: TenantRepository,
    audit: AuditPort,
) -> None:
    role = tenant_repo.get_caller_role(tenant_id, caller_id)
    if not role or role not in ADMIN_ROLES:
        raise ForbiddenError("forbidden")

    plugin_repo.uninstall(tenant_id, plugin_id)
    audit.log(caller_id, AuditActions.PLUGIN_UNINSTALLED, "plugin_install", plugin_id,
              {"tenant_id": tenant_id})


def get_catalog(
    user_id: str,
    plugin_repo: PluginRepository,
    tenant_repo: TenantRepository,
) -> list[dict]:
    membership = tenant_repo.get_membership_with_tenant(user_id)
    if not membership:
        return []
    return [asdict(e) for e in plugin_repo.get_catalog(membership["id"])]


def get_audit_log(user_id: str, limit: int, audit: AuditPort) -> list[dict]:
    return audit.list_user_entries(user_id, limit)


def get_admin_audit_log(
    caller_id: str,
    params: dict,
    audit: AuditPort,
    tenant_repo: TenantRepository,
) -> list[dict]:
    membership = tenant_repo.get_membership_with_tenant(caller_id)
    if not membership or membership["role"] not in ADMIN_ROLES:
        raise ForbiddenError("forbidden")
    try:
        limit = min(int(params.get("limit", 50)), 200)
        offset = max(int(params.get("offset", 0)), 0)
    except (TypeError, ValueError):
        limit, offset = 50, 0
    return audit.list_all_entries(limit, offset)
