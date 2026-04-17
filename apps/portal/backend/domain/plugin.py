from dataclasses import dataclass, field

VALID_INSTALL_STATUSES = frozenset({"active", "suspended", "trial"})


@dataclass
class PluginInstall:
    plugin_id: str
    status: str
    installed_at: float
    installed_by: str | None
    alive: bool
    manifest: dict = field(default_factory=dict)


@dataclass
class CatalogEntry:
    plugin_id: str
    name: str
    description: str
    icon: str
    version: str
    installed: bool
    install_status: str | None
    manifest: dict = field(default_factory=dict)
