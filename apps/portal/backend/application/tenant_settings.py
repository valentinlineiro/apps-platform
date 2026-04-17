from dataclasses import asdict

from domain.errors import ForbiddenError, NotFoundError, ValidationError
from domain.tenant import ADMIN_ROLES, VALID_ROLES
from ports.audit_port import AuditPort
from ports.tenant_repository import TenantRepository


def get_current_tenant(user_id: str, repo: TenantRepository) -> dict:
    membership = repo.get_membership_with_tenant(user_id)
    if not membership:
        raise ForbiddenError("not_a_tenant_member")
    return membership


def get_settings(tenant_id: str, user_id: str, repo: TenantRepository) -> dict:
    role = repo.get_caller_role(tenant_id, user_id)
    if role is None:
        raise ForbiddenError("forbidden")
    tenant = repo.get_tenant(tenant_id)
    if tenant is None:
        raise NotFoundError("tenant_not_found")
    return asdict(tenant)


def validate_settings_update(body: dict) -> dict:
    errors: dict[str, str] = {}
    member_default_role = body.get("member_default_role")
    if member_default_role is not None and member_default_role not in VALID_ROLES:
        errors["member_default_role"] = f"must be one of: {', '.join(sorted(VALID_ROLES))}"
    allowed_apps = body.get("allowed_apps")
    if allowed_apps is not None and not isinstance(allowed_apps, list):
        errors["allowed_apps"] = "must be an array or null"
    return errors


def update_settings(
    tenant_id: str,
    user_id: str,
    body: dict,
    repo: TenantRepository,
    audit: AuditPort,
) -> dict:
    role = repo.get_caller_role(tenant_id, user_id)
    if not role or role not in ADMIN_ROLES:
        raise ForbiddenError("forbidden")

    errors = validate_settings_update(body)
    if errors:
        raise ValidationError(errors)

    updates: dict = {}
    if "name" in body and isinstance(body["name"], str) and body["name"].strip():
        updates["name"] = body["name"]
    if "default_language" in body:
        updates["default_language"] = body["default_language"]
    member_default_role = body.get("member_default_role")
    if member_default_role is not None:
        updates["member_default_role"] = member_default_role
    if "allowed_apps" in body:
        updates["allowed_apps"] = body["allowed_apps"]  # list | None
    if "notification_defaults" in body and isinstance(body["notification_defaults"], dict):
        updates["notification_defaults"] = body["notification_defaults"]

    tenant = repo.save_settings(tenant_id, updates)
    if tenant is None:
        raise NotFoundError("tenant_not_found")

    if updates:
        audit.log(user_id, "tenant_settings_updated", "tenant", tenant_id,
                  {"fields": list(updates.keys())})
    return asdict(tenant)


def list_members(tenant_id: str, user_id: str, repo: TenantRepository) -> list[dict]:
    role = repo.get_caller_role(tenant_id, user_id)
    if role is None:
        raise ForbiddenError("forbidden")
    return [asdict(m) for m in repo.list_members(tenant_id)]


def add_member(
    tenant_id: str,
    caller_id: str,
    body: dict,
    repo: TenantRepository,
    audit: AuditPort,
) -> None:
    role = repo.get_caller_role(tenant_id, caller_id)
    if not role or role not in ADMIN_ROLES:
        raise ForbiddenError("forbidden")

    email = (body.get("email") or "").strip()
    member_role = body.get("role", "member")

    if not email:
        raise ValidationError("email is required")
    if member_role not in VALID_ROLES:
        raise ValidationError("invalid role")

    user_id = repo.find_user_by_email(email)
    if user_id is None:
        raise NotFoundError("user_not_found")

    repo.upsert_member(tenant_id, user_id, member_role)
    audit.log(caller_id, "tenant_member_added", "tenant", tenant_id,
              {"email": email, "role": member_role})


def remove_member(
    tenant_id: str,
    target_user_id: str,
    caller_id: str,
    repo: TenantRepository,
    audit: AuditPort,
) -> None:
    role = repo.get_caller_role(tenant_id, caller_id)
    if not role or role not in ADMIN_ROLES:
        raise ForbiddenError("forbidden")
    if caller_id == target_user_id:
        raise ValidationError("cannot remove yourself")

    repo.remove_member(tenant_id, target_user_id)
    audit.log(caller_id, "tenant_member_removed", "tenant", tenant_id,
              {"user_id": target_user_id})
