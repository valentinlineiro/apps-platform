from dataclasses import asdict
from domain.user import (
    UserProfile, Preferences, TenantPreferences,
    VALID_THEMES, VALID_DIGESTS, VALID_SCALES,
)
from ports.user_repository import UserRepository


def get_profile(user_id: str, repo: UserRepository) -> dict:
    return asdict(repo.get_profile(user_id))


_PROFILE_BOOL_FIELDS = {"show_activity", "show_email"}


def validate_profile(body: dict) -> dict:
    """Return fieldErrors dict; empty dict means valid."""
    errors: dict = {}
    for field in _PROFILE_BOOL_FIELDS:
        if field in body and not isinstance(body[field], bool):
            errors[field] = "must be a boolean"
    return errors


def update_profile(user_id: str, body: dict, repo: UserRepository) -> dict:
    allowed = {"avatar_url", "bio", "display_name", "show_activity", "show_email"}
    current = asdict(repo.get_profile(user_id))
    merged  = {**current, **{k: v for k, v in body.items() if k in allowed}}
    return asdict(repo.save_profile(user_id, UserProfile(**merged)))


def get_preferences(user_id: str, repo: UserRepository) -> dict:
    return asdict(repo.get_preferences(user_id))


def validate_preferences(body: dict) -> dict:
    """Return fieldErrors dict; empty dict means valid."""
    errors: dict = {}
    theme = body.get("theme")
    if theme is not None and theme not in VALID_THEMES:
        errors["theme"] = f"must be one of: {', '.join(sorted(VALID_THEMES))}"
    digest = body.get("notification_digest")
    if digest is not None and digest not in VALID_DIGESTS:
        errors["notification_digest"] = f"must be one of: {', '.join(sorted(VALID_DIGESTS))}"
    font_scale = body.get("font_scale")
    if font_scale is not None and font_scale not in VALID_SCALES:
        errors["font_scale"] = f"must be one of: {sorted(VALID_SCALES)}"
    return errors


def update_preferences(user_id: str, body: dict, repo: UserRepository) -> dict:
    current = asdict(repo.get_preferences(user_id))
    merged  = {**current, **{k: v for k, v in body.items() if k in current}}
    return asdict(repo.save_preferences(user_id, Preferences(**merged)))


def get_tenant_preferences(user_id: str, repo: UserRepository) -> dict | None:
    """Returns None when the user has no tenant."""
    tenant_id = repo.get_primary_tenant_id(user_id)
    if not tenant_id:
        return None
    tp = repo.get_tenant_preferences(user_id, tenant_id)
    return {"default_home_app": tp.default_home_app, "notify_app_ids": tp.notify_app_ids}


def update_tenant_preferences(
    user_id: str, body: dict, repo: UserRepository
) -> tuple[dict, str | None]:
    """Returns (result_dict, error_message). error_message is None on success."""
    tenant_id = repo.get_primary_tenant_id(user_id)
    if not tenant_id:
        return {}, "not_a_tenant_member"

    notify_ids = body.get("notify_app_ids")
    if notify_ids is not None and not isinstance(notify_ids, list):
        return {}, "notify_app_ids must be an array"

    current  = repo.get_tenant_preferences(user_id, tenant_id)
    new_home = body.get("default_home_app", current.default_home_app)
    new_ids  = notify_ids if notify_ids is not None else current.notify_app_ids

    result = repo.save_tenant_preferences(
        user_id, tenant_id,
        TenantPreferences(default_home_app=new_home, notify_app_ids=new_ids),
    )
    return {"default_home_app": result.default_home_app, "notify_app_ids": result.notify_app_ids}, None
