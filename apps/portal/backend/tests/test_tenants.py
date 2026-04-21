"""Tenant and member management integration tests.

These tests require a live Postgres connection (DATABASE_URL must be set).
Run with docker compose or point DATABASE_URL at a test Postgres instance.
They are skipped automatically in unit-test-only environments.
"""
import json
import os
import sys
import importlib
import unittest
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DATABASE_URL = os.environ.get("DATABASE_URL", "")
# Only run against a real Postgres, not the placeholder mock URL
_REAL_DB = DATABASE_URL and "localhost/test" not in DATABASE_URL

_psycopg2_mock = MagicMock()
sys.modules.setdefault("psycopg2", _psycopg2_mock)
sys.modules.setdefault("psycopg2.extras", _psycopg2_mock.extras)

import app as app_module  # noqa: E402


def _make_client(user_id=None):
    c = app_module.app.test_client()
    if user_id:
        with c.session_transaction() as sess:
            sess["user_id"] = user_id
    return c


@unittest.skipUnless(_REAL_DB, "DATABASE_URL not set — skipping Postgres integration tests")
class DefaultTenantTests(unittest.TestCase):
    def test_default_tenant_exists(self):
        user_id = app_module._upsert_user("alice@example.com", "Alice", "oidc", "sub-alice-t")
        res = _make_client(user_id).get("/api/tenants/current")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["id"], "default")

    def test_new_user_auto_enrolled(self):
        user_id = app_module._upsert_user("bob@example.com", "Bob", "oidc", "sub-bob-t")
        membership = app_module._get_tenant_membership(user_id)
        self.assertIsNotNone(membership)
        self.assertEqual(membership["id"], "default")
        self.assertEqual(membership["role"], "member")

    def test_current_tenant_requires_auth(self):
        res = _make_client().get("/api/tenants/current")
        self.assertEqual(res.status_code, 401)


@unittest.skipUnless(_REAL_DB, "DATABASE_URL not set — skipping Postgres integration tests")
class TenantMemberManagementTests(unittest.TestCase):
    def setUp(self):
        import time
        suffix = str(int(time.time() * 1000))
        self.owner_id = app_module._upsert_user(
            f"owner-{suffix}@example.com", "Owner", "oidc", f"sub-owner-{suffix}"
        )
        self.member_id = app_module._upsert_user(
            f"member-{suffix}@example.com", "Member", "oidc", f"sub-member-{suffix}"
        )
        # Promote owner in default tenant
        with app_module._db() as conn:
            conn.execute(
                "UPDATE tenant_memberships SET role='owner' WHERE tenant_id='default' AND user_id=?",
                (self.owner_id,),
            )

    def _owner(self):
        return _make_client(self.owner_id)

    def _member(self):
        return _make_client(self.member_id)

    def test_owner_can_list_members(self):
        res = self._owner().get("/api/tenants/default/members")
        self.assertEqual(res.status_code, 200)
        ids = [m["id"] for m in res.get_json()]
        self.assertIn(self.owner_id, ids)
        self.assertIn(self.member_id, ids)

    def test_member_can_list_members(self):
        res = self._member().get("/api/tenants/default/members")
        self.assertEqual(res.status_code, 200)

    def test_member_cannot_add_member(self):
        res = self._member().post(
            "/api/tenants/default/members",
            data=json.dumps({"email": "new@example.com", "role": "viewer"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)

    def test_owner_cannot_remove_themselves(self):
        res = self._owner().delete(f"/api/tenants/default/members/{self.owner_id}")
        self.assertEqual(res.status_code, 400)

    def test_add_nonexistent_user_returns_404(self):
        res = self._owner().post(
            "/api/tenants/default/members",
            data=json.dumps({"email": "ghost-nobody@example.com", "role": "member"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
