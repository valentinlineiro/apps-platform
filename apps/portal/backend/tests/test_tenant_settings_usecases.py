import sys
import time
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from domain.tenant import Membership, Tenant
from domain.errors import ForbiddenError, NotFoundError, ValidationError
import application.tenant_settings as uc
import application.catalog as cat_uc
from domain.plugin import CatalogEntry, PluginInstall


# ── Fakes ─────────────────────────────────────────────────────────────────────

class FakeTenantRepository:
    def __init__(self):
        self._tenants: dict[str, Tenant] = {
            "t1": Tenant(id="t1", name="Tenant One"),
        }
        # tenant_id -> {user_id -> role}
        self._memberships: dict[str, dict[str, str]] = {
            "t1": {"owner1": "owner", "admin1": "admin", "member1": "member"},
        }
        # email -> user_id
        self._users: dict[str, str] = {
            "owner@x.com": "owner1",
            "admin@x.com": "admin1",
            "member@x.com": "member1",
            "new@x.com": "new1",
        }

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def get_caller_role(self, tenant_id: str, user_id: str) -> str | None:
        return self._memberships.get(tenant_id, {}).get(user_id)

    def save_settings(self, tenant_id: str, updates: dict) -> Tenant | None:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return None
        for k, v in updates.items():
            setattr(tenant, k, v)
        return tenant

    def list_members(self, tenant_id: str) -> list[Membership]:
        roles = self._memberships.get(tenant_id, {})
        return [
            Membership(
                user_id=uid,
                email=f"{uid}@x.com",
                name=uid.capitalize(),
                role=role,
                joined_at=0.0,
            )
            for uid, role in roles.items()
        ]

    def find_user_by_email(self, email: str) -> str | None:
        return self._users.get(email)

    def upsert_member(self, tenant_id: str, user_id: str, role: str) -> None:
        self._memberships.setdefault(tenant_id, {})[user_id] = role

    def remove_member(self, tenant_id: str, user_id: str) -> None:
        self._memberships.get(tenant_id, {}).pop(user_id, None)

    def get_membership_with_tenant(self, user_id: str) -> dict | None:
        for tenant_id, roles in self._memberships.items():
            if user_id in roles:
                tenant = self._tenants.get(tenant_id)
                return {"id": tenant_id, "name": tenant.name if tenant else "", "role": roles[user_id]}
        return None


class FakePluginRepository:
    def __init__(self):
        # tenant_id -> {plugin_id -> PluginInstall}
        self._installs: dict[str, dict[str, PluginInstall]] = {}
        self._registered: set[str] = {"plugin-a", "plugin-b"}
        self._catalog: list[CatalogEntry] = [
            CatalogEntry(
                plugin_id="plugin-a",
                name="Plugin A",
                description="First plugin",
                icon="A",
                version="1.0.0",
                installed=False,
                install_status=None,
            ),
        ]

    def list_installs(self, tenant_id: str) -> list[PluginInstall]:
        return list(self._installs.get(tenant_id, {}).values())

    def install(self, tenant_id: str, plugin_id: str, installed_by: str | None) -> None:
        self._installs.setdefault(tenant_id, {}).setdefault(
            plugin_id,
            PluginInstall(
                plugin_id=plugin_id,
                status="active",
                installed_at=time.time(),
                installed_by=installed_by,
                alive=True,
            ),
        )

    def update_status(self, tenant_id: str, plugin_id: str, status: str) -> bool:
        install = self._installs.get(tenant_id, {}).get(plugin_id)
        if install is None:
            return False
        install.status = status
        return True

    def uninstall(self, tenant_id: str, plugin_id: str) -> None:
        self._installs.get(tenant_id, {}).pop(plugin_id, None)

    def get_catalog(self, tenant_id: str) -> list[CatalogEntry]:
        installed = self._installs.get(tenant_id, {})
        result = []
        for entry in self._catalog:
            install = installed.get(entry.plugin_id)
            result.append(CatalogEntry(
                plugin_id=entry.plugin_id,
                name=entry.name,
                description=entry.description,
                icon=entry.icon,
                version=entry.version,
                installed=install is not None,
                install_status=install.status if install else None,
            ))
        return result

    def plugin_registered(self, plugin_id: str) -> bool:
        return plugin_id in self._registered


class FakeAuditRepository:
    def __init__(self):
        self.entries: list[dict] = []

    def log(self, user_id, action, resource_type=None, resource_id=None, metadata=None):
        self.entries.append({
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
        })

    def list_user_entries(self, user_id: str, limit: int) -> list[dict]:
        return [e for e in self.entries if e["user_id"] == user_id][:limit]


# ── Tenant settings use-case tests ────────────────────────────────────────────

class GetCurrentTenantTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeTenantRepository()

    def test_returns_membership_for_known_member(self):
        result = uc.get_current_tenant("member1", self.repo)
        self.assertEqual(result["id"], "t1")
        self.assertEqual(result["role"], "member")

    def test_raises_forbidden_for_unknown_user(self):
        with self.assertRaises(ForbiddenError) as ctx:
            uc.get_current_tenant("nobody", self.repo)
        self.assertEqual(ctx.exception.code, "not_a_tenant_member")


class GetSettingsTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeTenantRepository()

    def test_member_can_read_settings(self):
        result = uc.get_settings("t1", "member1", self.repo)
        self.assertEqual(result["id"], "t1")
        self.assertEqual(result["name"], "Tenant One")

    def test_non_member_raises_forbidden(self):
        with self.assertRaises(ForbiddenError):
            uc.get_settings("t1", "nobody", self.repo)

    def test_missing_tenant_raises_not_found(self):
        self.repo._memberships["ghost"] = {"member1": "member"}
        with self.assertRaises(NotFoundError):
            uc.get_settings("ghost", "member1", self.repo)


class UpdateSettingsTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeTenantRepository()
        self.audit = FakeAuditRepository()

    def test_owner_can_update_name(self):
        result = uc.update_settings("t1", "owner1", {"name": "New Name"}, self.repo, self.audit)
        self.assertEqual(result["name"], "New Name")

    def test_admin_can_update_language(self):
        result = uc.update_settings("t1", "admin1", {"default_language": "en"}, self.repo, self.audit)
        self.assertEqual(result["default_language"], "en")

    def test_member_raises_forbidden(self):
        with self.assertRaises(ForbiddenError):
            uc.update_settings("t1", "member1", {"name": "x"}, self.repo, self.audit)

    def test_invalid_role_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            uc.update_settings("t1", "owner1", {"member_default_role": "superadmin"}, self.repo, self.audit)
        self.assertIn("member_default_role", ctx.exception.errors)

    def test_allowed_apps_must_be_list(self):
        with self.assertRaises(ValidationError) as ctx:
            uc.update_settings("t1", "owner1", {"allowed_apps": "not-a-list"}, self.repo, self.audit)
        self.assertIn("allowed_apps", ctx.exception.errors)

    def test_update_logs_audit_entry(self):
        uc.update_settings("t1", "owner1", {"name": "Renamed"}, self.repo, self.audit)
        self.assertEqual(len(self.audit.entries), 1)
        self.assertEqual(self.audit.entries[0]["action"], "tenant_settings_updated")


class ListMembersTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeTenantRepository()

    def test_returns_members_for_tenant_member(self):
        members = uc.list_members("t1", "member1", self.repo)
        user_ids = {m["user_id"] for m in members}
        self.assertIn("owner1", user_ids)
        self.assertIn("member1", user_ids)

    def test_non_member_raises_forbidden(self):
        with self.assertRaises(ForbiddenError):
            uc.list_members("t1", "nobody", self.repo)


class AddMemberTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeTenantRepository()
        self.audit = FakeAuditRepository()

    def test_owner_can_add_known_user(self):
        uc.add_member("t1", "owner1", {"email": "new@x.com", "role": "member"}, self.repo, self.audit)
        self.assertEqual(self.repo._memberships["t1"].get("new1"), "member")

    def test_member_cannot_add(self):
        with self.assertRaises(ForbiddenError):
            uc.add_member("t1", "member1", {"email": "new@x.com"}, self.repo, self.audit)

    def test_missing_email_raises_validation(self):
        with self.assertRaises(ValidationError):
            uc.add_member("t1", "owner1", {}, self.repo, self.audit)

    def test_invalid_role_raises_validation(self):
        with self.assertRaises(ValidationError):
            uc.add_member("t1", "owner1", {"email": "new@x.com", "role": "god"}, self.repo, self.audit)

    def test_unknown_email_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            uc.add_member("t1", "owner1", {"email": "ghost@x.com"}, self.repo, self.audit)

    def test_add_logs_audit_entry(self):
        uc.add_member("t1", "owner1", {"email": "new@x.com", "role": "viewer"}, self.repo, self.audit)
        self.assertEqual(self.audit.entries[0]["action"], "tenant_member_added")


class RemoveMemberTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeTenantRepository()
        self.audit = FakeAuditRepository()

    def test_owner_can_remove_member(self):
        uc.remove_member("t1", "member1", "owner1", self.repo, self.audit)
        self.assertNotIn("member1", self.repo._memberships["t1"])

    def test_cannot_remove_yourself(self):
        with self.assertRaises(ValidationError):
            uc.remove_member("t1", "owner1", "owner1", self.repo, self.audit)

    def test_non_admin_raises_forbidden(self):
        with self.assertRaises(ForbiddenError):
            uc.remove_member("t1", "owner1", "member1", self.repo, self.audit)

    def test_remove_logs_audit_entry(self):
        uc.remove_member("t1", "member1", "owner1", self.repo, self.audit)
        self.assertEqual(self.audit.entries[0]["action"], "tenant_member_removed")


# ── Catalog use-case tests ─────────────────────────────────────────────────────

class ListInstallsTests(unittest.TestCase):
    def setUp(self):
        self.tenant_repo = FakeTenantRepository()
        self.plugin_repo = FakePluginRepository()
        self.plugin_repo.install("t1", "plugin-a", "owner1")

    def test_member_can_list_installs(self):
        installs = cat_uc.list_installs("t1", "member1", self.plugin_repo, self.tenant_repo)
        self.assertEqual(len(installs), 1)
        self.assertEqual(installs[0]["plugin_id"], "plugin-a")

    def test_non_member_raises_forbidden(self):
        with self.assertRaises(ForbiddenError):
            cat_uc.list_installs("t1", "nobody", self.plugin_repo, self.tenant_repo)


class InstallPluginTests(unittest.TestCase):
    def setUp(self):
        self.tenant_repo = FakeTenantRepository()
        self.plugin_repo = FakePluginRepository()
        self.audit = FakeAuditRepository()

    def test_owner_can_install_registered_plugin(self):
        cat_uc.install_plugin("t1", "owner1", {"plugin_id": "plugin-a"}, self.plugin_repo, self.tenant_repo, self.audit)
        self.assertIn("plugin-a", self.plugin_repo._installs.get("t1", {}))

    def test_member_cannot_install(self):
        with self.assertRaises(ForbiddenError):
            cat_uc.install_plugin("t1", "member1", {"plugin_id": "plugin-a"}, self.plugin_repo, self.tenant_repo, self.audit)

    def test_missing_plugin_id_raises_validation(self):
        with self.assertRaises(ValidationError):
            cat_uc.install_plugin("t1", "owner1", {}, self.plugin_repo, self.tenant_repo, self.audit)

    def test_unregistered_plugin_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            cat_uc.install_plugin("t1", "owner1", {"plugin_id": "ghost"}, self.plugin_repo, self.tenant_repo, self.audit)

    def test_install_logs_audit_entry(self):
        cat_uc.install_plugin("t1", "owner1", {"plugin_id": "plugin-a"}, self.plugin_repo, self.tenant_repo, self.audit)
        self.assertEqual(self.audit.entries[0]["action"], "plugin_installed")


class UpdateInstallStatusTests(unittest.TestCase):
    def setUp(self):
        self.tenant_repo = FakeTenantRepository()
        self.plugin_repo = FakePluginRepository()
        self.plugin_repo.install("t1", "plugin-a", "owner1")
        self.audit = FakeAuditRepository()

    def test_owner_can_suspend(self):
        cat_uc.update_install_status("t1", "owner1", "plugin-a", {"status": "suspended"}, self.plugin_repo, self.tenant_repo, self.audit)
        self.assertEqual(self.plugin_repo._installs["t1"]["plugin-a"].status, "suspended")

    def test_invalid_status_raises_validation(self):
        with self.assertRaises(ValidationError):
            cat_uc.update_install_status("t1", "owner1", "plugin-a", {"status": "broken"}, self.plugin_repo, self.tenant_repo, self.audit)

    def test_missing_install_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            cat_uc.update_install_status("t1", "owner1", "ghost", {"status": "active"}, self.plugin_repo, self.tenant_repo, self.audit)


class UninstallPluginTests(unittest.TestCase):
    def setUp(self):
        self.tenant_repo = FakeTenantRepository()
        self.plugin_repo = FakePluginRepository()
        self.plugin_repo.install("t1", "plugin-a", "owner1")
        self.audit = FakeAuditRepository()

    def test_owner_can_uninstall(self):
        cat_uc.uninstall_plugin("t1", "owner1", "plugin-a", self.plugin_repo, self.tenant_repo, self.audit)
        self.assertNotIn("plugin-a", self.plugin_repo._installs.get("t1", {}))

    def test_member_cannot_uninstall(self):
        with self.assertRaises(ForbiddenError):
            cat_uc.uninstall_plugin("t1", "member1", "plugin-a", self.plugin_repo, self.tenant_repo, self.audit)

    def test_uninstall_logs_audit_entry(self):
        cat_uc.uninstall_plugin("t1", "owner1", "plugin-a", self.plugin_repo, self.tenant_repo, self.audit)
        self.assertEqual(self.audit.entries[0]["action"], "plugin_uninstalled")


class GetCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tenant_repo = FakeTenantRepository()
        self.plugin_repo = FakePluginRepository()

    def test_returns_catalog_for_known_user(self):
        entries = cat_uc.get_catalog("member1", self.plugin_repo, self.tenant_repo)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["plugin_id"], "plugin-a")

    def test_returns_empty_for_user_without_tenant(self):
        entries = cat_uc.get_catalog("nobody", self.plugin_repo, self.tenant_repo)
        self.assertEqual(entries, [])

    def test_installed_flag_reflects_installs(self):
        self.plugin_repo.install("t1", "plugin-a", "owner1")
        entries = cat_uc.get_catalog("member1", self.plugin_repo, self.tenant_repo)
        self.assertTrue(entries[0]["installed"])


class GetAuditLogTests(unittest.TestCase):
    def setUp(self):
        self.audit = FakeAuditRepository()
        self.audit.log("user1", "login")
        self.audit.log("user1", "logout")
        self.audit.log("user2", "login")

    def test_returns_only_user_entries(self):
        entries = cat_uc.get_audit_log("user1", 10, self.audit)
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(e["user_id"] == "user1" for e in entries))

    def test_respects_limit(self):
        entries = cat_uc.get_audit_log("user1", 1, self.audit)
        self.assertEqual(len(entries), 1)


if __name__ == "__main__":
    unittest.main()
