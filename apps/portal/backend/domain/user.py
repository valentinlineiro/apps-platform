from dataclasses import dataclass, field

VALID_THEMES  = frozenset({"dark", "light", "system"})
VALID_DIGESTS = frozenset({"none", "daily", "weekly"})
VALID_SCALES  = frozenset({0.8, 1.0, 1.2, 1.5})


@dataclass
class UserProfile:
    avatar_url:    str | None = None
    bio:           str | None = None
    display_name:  str | None = None
    show_activity: bool = True
    show_email:    bool = False


@dataclass
class Preferences:
    theme:               str   = "dark"
    language:            str   = "es"
    timezone:            str   = "UTC"
    reduced_motion:      bool  = False
    font_scale:          float = 1.0
    notification_email:  bool  = True
    notification_digest: str   = "weekly"


@dataclass
class TenantPreferences:
    default_home_app: str | None = None
    notify_app_ids:   list = field(default_factory=list)
