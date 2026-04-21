"""Tests for profile, preferences, tenant-preferences, and tenant-settings endpoints.

Integration test classes (PreferencesTests, ProfileTests, etc.) require a live
Postgres connection and are skipped unless DATABASE_URL is set.
ProfileUseCaseTests runs in any environment — it uses an in-memory fake repo.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("PORTAL_SESSION_SECRET", "test-secret")

_psycopg2_mock = MagicMock()
sys.modules.setdefault("psycopg2", _psycopg2_mock)
sys.modules.setdefault("psycopg2.extras", _psycopg2_mock.extras)

import app as _app_mod  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_REAL_DB = DATABASE_URL and "localhost/test" not in DATABASE_URL


def _client(user_id=None):
    c = _app_mod.app.test_client()
    if user_id:
        with c.session_transaction() as sess:
            sess["user_id"] = user_id
    return c


def _make_user(email="user@example.com", name="Test User"):
    return _app_mod._upsert_user(email, name, "oidc", f"sub-{email}")


def _make_owner(email="owner@example.com"):
    uid = _app_mod._upsert_user(email, "Owner", "oidc", f"sub-{email}")
    with _app_mod._db() as conn:
        conn.execute(
            "UPDATE tenant_memberships SET role='owner' WHERE tenant_id='default' AND user_id=?",
            (uid,),
        )
    return uid


@unittest.skipUnless(_REAL_DB, "DATABASE_URL not set — skipping Postgres integration tests")
class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.uid = _make_user()
        self.client = _client(self.uid)

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
        c = _client()
        self.assertEqual(c.get("/auth/me/preferences").status_code, 401)

    def test_patch_preferences_is_idempotent(self):
        self.client.patch("/auth/me/preferences", json={"theme": "light"})
        r = self.client.patch("/auth/me/preferences", json={"theme": "system"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["theme"], "system")


@unittest.skipUnless(_REAL_DB, "DATABASE_URL not set — skipping Postgres integration tests")
class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.uid = _make_user()
        self.client = _client(self.uid)

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
        c = _client()
        self.assertEqual(c.get("/auth/me/profile").status_code, 401)


@unittest.skipUnless(_REAL_DB, "DATABASE_URL not set — skipping Postgres integration tests")
class TenantPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.uid = _make_user()
        self.client = _client(self.uid)

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


@unittest.skipUnless(_REAL_DB, "DATABASE_URL not set — skipping Postgres integration tests")
class TenantSettingsTests(unittest.TestCase):
    def setUp(self):
        self.owner_uid = _make_owner()
        self.member_uid = _make_user("member@example.com", "Member")
        self.owner_client = _client(self.owner_uid)
        self.member_client = _client(self.member_uid)

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
        c = _client()
        self.assertEqual(c.get("/api/tenants/default/settings").status_code, 401)

    def test_patch_settings_updates_name(self):
        r = self.owner_client.patch(
            "/api/tenants/default/settings",
            json={"name": "Nuevo nombre"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["name"], "Nuevo nombre")


@unittest.skipUnless(_REAL_DB, "DATABASE_URL not set — skipping Postgres integration tests")
class AuditEndpointTests(unittest.TestCase):
    def setUp(self):
        self.uid = _make_user()
        self.client = _client(self.uid)

    def test_get_audit_returns_empty_for_new_user(self):
        r = self.client.get("/api/audit")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), [])

    def test_get_audit_returns_own_entries_only(self):
        other_uid = _make_user("other@example.com", "Other")
        _app_mod._log_audit(self.uid, "test.action", "resource", "r-1")
        _app_mod._log_audit(other_uid, "other.action", "resource", "r-2")
        r = self.client.get("/api/audit")
        entries = r.get_json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"], "test.action")

    def test_get_audit_respects_limit(self):
        for i in range(10):
            _app_mod._log_audit(self.uid, f"action.{i}")
        r = self.client.get("/api/audit?limit=3")
        self.assertEqual(len(r.get_json()), 3)

    def test_get_audit_requires_auth(self):
        self.assertEqual(_client().get("/api/audit").status_code, 401)

    def test_get_audit_entry_shape(self):
        _app_mod._log_audit(self.uid, "login", "session", "s-1")
        entries = self.client.get("/api/audit").get_json()
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertIn("id", e)
        self.assertEqual(e["action"], "login")
        self.assertEqual(e["resource_type"], "session")
        self.assertEqual(e["resource_id"], "s-1")
        self.assertIn("created_at", e)


class FakeUserRepository:
    """In-memory UserRepository for use-case tests — no HTTP, no database."""

    def __init__(self, primary_tenant_id: str | None = "default"):
        self._profiles: dict = {}
        self._prefs: dict = {}
        self._tenant_prefs: dict = {}
        self._primary_tenant_id = primary_tenant_id

    def get_profile(self, user_id):
        from domain.user import UserProfile
        return self._profiles.get(user_id, UserProfile())

    def save_profile(self, user_id, profile):
        self._profiles[user_id] = profile
        return profile

    def get_preferences(self, user_id):
        from domain.user import Preferences
        return self._prefs.get(user_id, Preferences())

    def save_preferences(self, user_id, prefs):
        self._prefs[user_id] = prefs
        return prefs

    def get_primary_tenant_id(self, user_id):
        return self._primary_tenant_id

    def get_tenant_preferences(self, user_id, tenant_id):
        from domain.user import TenantPreferences
        return self._tenant_prefs.get((user_id, tenant_id), TenantPreferences())

    def save_tenant_preferences(self, user_id, tenant_id, prefs):
        self._tenant_prefs[(user_id, tenant_id)] = prefs
        return prefs


class ProfileUseCaseTests(unittest.TestCase):
    """Exercises use cases directly — no Flask, no HTTP, no database."""

    def setUp(self):
        self.repo = FakeUserRepository()

    def test_get_profile_defaults(self):
        from application.profile import get_profile
        data = get_profile("u1", self.repo)
        self.assertIsNone(data["avatar_url"])
        self.assertIsNone(data["bio"])
        self.assertTrue(data["show_activity"])
        self.assertFalse(data["show_email"])

    def test_update_profile_merges_fields(self):
        from application.profile import get_profile, update_profile
        update_profile("u1", {"display_name": "Ada", "bio": "Mathematician"}, self.repo)
        data = get_profile("u1", self.repo)
        self.assertEqual(data["display_name"], "Ada")
        self.assertEqual(data["bio"], "Mathematician")

    def test_update_profile_ignores_unknown_keys(self):
        from application.profile import update_profile, get_profile
        update_profile("u1", {"display_name": "X", "hack": "injected"}, self.repo)
        self.assertNotIn("hack", get_profile("u1", self.repo))

    def test_update_profile_partial_preserves_other_fields(self):
        from application.profile import update_profile, get_profile
        update_profile("u1", {"bio": "Initial"}, self.repo)
        update_profile("u1", {"display_name": "New"}, self.repo)
        data = get_profile("u1", self.repo)
        self.assertEqual(data["bio"], "Initial")
        self.assertEqual(data["display_name"], "New")

    def test_preferences_defaults(self):
        from application.profile import get_preferences
        data = get_preferences("u1", self.repo)
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["font_scale"], 1.0)
        self.assertEqual(data["notification_digest"], "weekly")
        self.assertTrue(data["notification_email"])

    def test_update_preferences_merges(self):
        from application.profile import update_preferences, get_preferences
        update_preferences("u1", {"theme": "light", "language": "en"}, self.repo)
        data = get_preferences("u1", self.repo)
        self.assertEqual(data["theme"], "light")
        self.assertEqual(data["language"], "en")
        self.assertEqual(data["timezone"], "UTC")  # unchanged default

    def test_validate_preferences_rejects_bad_theme(self):
        from application.profile import validate_preferences
        self.assertIn("theme", validate_preferences({"theme": "pink"}))

    def test_validate_preferences_rejects_bad_digest(self):
        from application.profile import validate_preferences
        self.assertIn("notification_digest", validate_preferences({"notification_digest": "hourly"}))

    def test_validate_preferences_rejects_bad_font_scale(self):
        from application.profile import validate_preferences
        self.assertIn("font_scale", validate_preferences({"font_scale": 99.9}))

    def test_validate_preferences_accepts_valid_payload(self):
        from application.profile import validate_preferences
        errors = validate_preferences({"theme": "light", "font_scale": 1.2, "notification_digest": "daily"})
        self.assertEqual(errors, {})

    def test_tenant_preferences_defaults(self):
        from application.profile import get_tenant_preferences
        data = get_tenant_preferences("u1", self.repo)
        self.assertIsNone(data["default_home_app"])
        self.assertEqual(data["notify_app_ids"], [])

    def test_tenant_preferences_returns_none_without_tenant(self):
        from application.profile import get_tenant_preferences
        repo = FakeUserRepository(primary_tenant_id=None)
        self.assertIsNone(get_tenant_preferences("u1", repo))

    def test_update_tenant_preferences_sets_home_app(self):
        from application.profile import update_tenant_preferences
        result, error = update_tenant_preferences("u1", {"default_home_app": "exam-corrector"}, self.repo)
        self.assertIsNone(error)
        self.assertEqual(result["default_home_app"], "exam-corrector")

    def test_update_tenant_preferences_rejects_bad_notify_ids(self):
        from application.profile import update_tenant_preferences
        _, error = update_tenant_preferences("u1", {"notify_app_ids": "not-a-list"}, self.repo)
        self.assertIsNotNone(error)

    def test_update_tenant_preferences_no_tenant_returns_error(self):
        from application.profile import update_tenant_preferences
        repo = FakeUserRepository(primary_tenant_id=None)
        _, error = update_tenant_preferences("u1", {}, repo)
        self.assertEqual(error, "not_a_tenant_member")


if __name__ == "__main__":
    unittest.main()
