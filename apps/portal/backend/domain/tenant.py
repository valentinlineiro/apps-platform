from dataclasses import dataclass, field

VALID_ROLES = frozenset({"owner", "admin", "member", "viewer"})
ADMIN_ROLES = frozenset({"owner", "admin"})


@dataclass
class Tenant:
    id: str
    name: str
    default_language: str = "es"
    member_default_role: str = "member"
    allowed_apps: list | None = None
    notification_defaults: dict = field(default_factory=dict)


@dataclass
class Membership:
    user_id: str
    email: str
    name: str
    role: str
    joined_at: float
