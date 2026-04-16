"""Tests for profile, preferences, tenant-preferences, and tenant-settings endpoints."""
import importlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _load_module(db_path: str):
    os.environ["REGISTRY_DB_PATH"] = db_path
    os.environ["PORTAL_SESSION_SECRET"] = "test-secret"
    os.environ.pop("DATABASE_URL", None)
    empty_static = str(Path(db_path).parent / "empty_static.json")
    with open(empty_static, "w") as f:
        f.write("[]")
    os.environ["STATIC_APPS_FILE"] = empty_static
    mod = importlib.import_module("app")
    return importlib.reload(mod)


def _client(mod, user_id: str | None = None):
    c = mod.app.test_client()
    if user_id:
        with c.session_transaction() as sess:
            sess["user_id"] = user_id
    return c


def _make_user(mod, email="user@example.com", name="Test User"):
    return mod._upsert_user(email, name, "oidc", f"sub-{email}")


def _make_owner(mod, email="owner@example.com"):
    uid = mod._upsert_user(email, "Owner", "oidc", f"sub-{email}")
    conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
    conn.execute(
        "UPDATE tenant_memberships SET role='owner' WHERE tenant_id='default' AND user_id=?",
        (uid,),
    )
    conn.commit()
    conn.close()
    return uid


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.uid = _make_user(self.mod)
        self.client = _client(self.mod, self.uid)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_preferences_returns_defaults(self):
        r = self.client.get("/auth/me/preferences")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["language"], "es")
        self.assertEqual(data["font_scale"], 1.0)
        self.assertTrue(data["notification_email"])
        self.assertEqual(data["notification_digest"], "weekly")

    def test_patch_preferences_updates_fields(self):
        r = self.client.patch(
            "/auth/me/preferences",
            json={"theme": "light", "language": "en", "font_scale": 1.2},
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["theme"], "light")
        self.assertEqual(data["language"], "en")
        self.assertEqual(data["font_scale"], 1.2)

    def test_patch_preferences_ignores_unknown_fields(self):
        r = self.client.patch("/auth/me/preferences", json={"theme": "dark", "hack": "x"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("hack", r.get_json())

    def test_patch_preferences_rejects_invalid_theme(self):
        r = self.client.patch("/auth/me/preferences", json={"theme": "pink"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("theme", r.get_json().get("fieldErrors", {}))

    def test_patch_preferences_rejects_invalid_font_scale(self):
        r = self.client.patch("/auth/me/preferences", json={"font_scale": 999})
        self.assertEqual(r.status_code, 400)

    def test_patch_preferences_rejects_invalid_digest(self):
        r = self.client.patch("/auth/me/preferences", json={"notification_digest": "hourly"})
        self.assertEqual(r.status_code, 400)

    def test_get_preferences_requires_auth(self):
        c = _client(self.mod)
        self.assertEqual(c.get("/auth/me/preferences").status_code, 401)

    def test_patch_preferences_is_idempotent(self):
        self.client.patch("/auth/me/preferences", json={"theme": "light"})
        r = self.client.patch("/auth/me/preferences", json={"theme": "system"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["theme"], "system")


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.uid = _make_user(self.mod)
        self.client = _client(self.mod, self.uid)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_profile_returns_defaults(self):
        r = self.client.get("/auth/me/profile")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsNone(data["avatar_url"])
        self.assertIsNone(data["bio"])
        self.assertIsNone(data["display_name"])
        self.assertTrue(data["show_activity"])
        self.assertFalse(data["show_email"])

    def test_patch_profile_updates_fields(self):
        r = self.client.patch(
            "/auth/me/profile",
            json={"display_name": "Ada", "bio": "Mathematician", "show_email": True},
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["display_name"], "Ada")
        self.assertEqual(data["bio"], "Mathematician")
        self.assertTrue(data["show_email"])

    def test_patch_profile_persists_across_requests(self):
        self.client.patch("/auth/me/profile", json={"display_name": "Persisted"})
        r = self.client.get("/auth/me/profile")
        self.assertEqual(r.get_json()["display_name"], "Persisted")

    def test_patch_profile_partial_update_preserves_other_fields(self):
        self.client.patch("/auth/me/profile", json={"bio": "Initial bio"})
        self.client.patch("/auth/me/profile", json={"display_name": "New Name"})
        r = self.client.get("/auth/me/profile")
        data = r.get_json()
        self.assertEqual(data["bio"], "Initial bio")
        self.assertEqual(data["display_name"], "New Name")

    def test_get_profile_requires_auth(self):
        c = _client(self.mod)
        self.assertEqual(c.get("/auth/me/profile").status_code, 401)


class TenantPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.uid = _make_user(self.mod)
        self.client = _client(self.mod, self.uid)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_tenant_preferences_returns_defaults(self):
        r = self.client.get("/auth/me/tenant-preferences")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsNone(data["default_home_app"])
        self.assertEqual(data["notify_app_ids"], [])

    def test_patch_tenant_preferences_sets_home_app(self):
        r = self.client.patch(
            "/auth/me/tenant-preferences",
            json={"default_home_app": "exam-corrector"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["default_home_app"], "exam-corrector")

    def test_patch_tenant_preferences_persists(self):
        self.client.patch("/auth/me/tenant-preferences", json={"default_home_app": "app-x"})
        r = self.client.get("/auth/me/tenant-preferences")
        self.assertEqual(r.get_json()["default_home_app"], "app-x")

    def test_patch_tenant_preferences_rejects_bad_notify_ids(self):
        r = self.client.patch(
            "/auth/me/tenant-preferences",
            json={"notify_app_ids": "not-a-list"},
        )
        self.assertEqual(r.status_code, 400)


class TenantSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.owner_uid = _make_owner(self.mod)
        self.member_uid = _make_user(self.mod, "member@example.com", "Member")
        self.owner_client = _client(self.mod, self.owner_uid)
        self.member_client = _client(self.mod, self.member_uid)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_settings_accessible_to_member(self):
        r = self.member_client.get("/api/tenants/default/settings")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("name", data)
        self.assertIn("default_language", data)

    def test_patch_settings_allowed_for_owner(self):
        r = self.owner_client.patch(
            "/api/tenants/default/settings",
            json={"default_language": "en", "member_default_role": "viewer"},
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["default_language"], "en")
        self.assertEqual(data["member_default_role"], "viewer")

    def test_patch_settings_forbidden_for_member(self):
        r = self.member_client.patch(
            "/api/tenants/default/settings",
            json={"default_language": "en"},
        )
        self.assertEqual(r.status_code, 403)

    def test_get_settings_requires_auth(self):
        c = _client(self.mod)
        self.assertEqual(c.get("/api/tenants/default/settings").status_code, 401)

    def test_patch_settings_updates_name(self):
        r = self.owner_client.patch(
            "/api/tenants/default/settings",
            json={"name": "Nuevo nombre"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["name"], "Nuevo nombre")


class AuditEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.uid = _make_user(self.mod)
        self.client = _client(self.mod, self.uid)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_audit_returns_empty_for_new_user(self):
        r = self.client.get("/api/audit")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), [])

    def test_get_audit_returns_own_entries_only(self):
        other_uid = _make_user(self.mod, "other@example.com", "Other")
        self.mod._log_audit(self.uid, "test.action", "resource", "r-1")
        self.mod._log_audit(other_uid, "other.action", "resource", "r-2")
        r = self.client.get("/api/audit")
        entries = r.get_json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "test.action")

    def test_get_audit_respects_limit(self):
        for i in range(10):
            self.mod._log_audit(self.uid, f"action.{i}")
        r = self.client.get("/api/audit?limit=3")
        self.assertEqual(len(r.get_json()), 3)

    def test_get_audit_requires_auth(self):
        c = _client(self.mod)
        self.assertEqual(c.get("/api/audit").status_code, 401)

    def test_get_audit_entry_shape(self):
        self.mod._log_audit(self.uid, "login", "session", "s-1")
        entries = self.client.get("/api/audit").get_json()
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertIn("id", e)
        self.assertEqual(e["action"], "login")
        self.assertEqual(e["resource_type"], "session")
        self.assertEqual(e["resource_id"], "s-1")
        self.assertIn("created_at", e)


if __name__ == "__main__":
    unittest.main()
