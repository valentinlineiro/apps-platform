import importlib
import json
import os
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
    # Unset DATABASE_URL so tests use SQLite
    os.environ.pop("DATABASE_URL", None)
    mod = importlib.import_module("app")
    return importlib.reload(mod)


def _make_client(mod, user_id: str | None = None):
    client = mod.app.test_client()
    if user_id:
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
    return client


class DefaultTenantTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = str(Path(self.temp_dir.name) / "portal.sqlite3")
        self.mod = _load_module(db_path)

    def tearDown(self):
        self.temp_dir.cleanup()
        for key in ("REGISTRY_DB_PATH", "PORTAL_SESSION_SECRET"):
            os.environ.pop(key, None)

    def test_default_tenant_exists(self):
        """Default tenant is seeded at startup."""
        client = _make_client(self.mod)
        # Seed a user and log them in
        user_id = self.mod._upsert_user("alice@example.com", "Alice", "oidc", "sub-alice")
        client = _make_client(self.mod, user_id)
        res = client.get("/api/tenants/current")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["id"], "default")
        self.assertEqual(data["name"], "Default")

    def test_new_user_auto_enrolled(self):
        """New users are automatically added to the default tenant as 'member'."""
        user_id = self.mod._upsert_user("bob@example.com", "Bob", "oidc", "sub-bob")
        membership = self.mod._get_tenant_membership(user_id)
        self.assertIsNotNone(membership)
        self.assertEqual(membership["id"], "default")
        self.assertEqual(membership["role"], "member")

    def test_auth_me_includes_tenant(self):
        """/auth/me includes tenant context."""
        user_id = self.mod._upsert_user("carol@example.com", "Carol", "oidc", "sub-carol")
        client = _make_client(self.mod, user_id)
        res = client.get("/auth/me")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("tenant", data)
        self.assertEqual(data["tenant"]["id"], "default")

    def test_current_tenant_requires_auth(self):
        client = _make_client(self.mod)
        res = client.get("/api/tenants/current")
        self.assertEqual(res.status_code, 401)


class TenantMemberManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = str(Path(self.temp_dir.name) / "portal.sqlite3")
        self.mod = _load_module(db_path)
        # Create two users: one owner, one regular member
        self.owner_id = self.mod._upsert_user("owner@example.com", "Owner", "oidc", "sub-owner")
        self.member_id = self.mod._upsert_user("member@example.com", "Member", "oidc", "sub-member")
        # Promote owner within the tenant
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute(
            "UPDATE tenant_memberships SET role='owner' WHERE tenant_id='default' AND user_id=?",
            (self.owner_id,),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()
        for key in ("REGISTRY_DB_PATH", "PORTAL_SESSION_SECRET"):
            os.environ.pop(key, None)

    def _owner_client(self):
        return _make_client(self.mod, self.owner_id)

    def _member_client(self):
        return _make_client(self.mod, self.member_id)

    def test_owner_can_list_members(self):
        res = self._owner_client().get("/api/tenants/default/members")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        ids = [m["id"] for m in data]
        self.assertIn(self.owner_id, ids)
        self.assertIn(self.member_id, ids)

    def test_member_can_list_members(self):
        """Any tenant member (not just owners) can list members."""
        res = self._member_client().get("/api/tenants/default/members")
        self.assertEqual(res.status_code, 200)

    def test_outsider_cannot_list_members(self):
        outsider_id = self.mod._upsert_user("out@example.com", "Out", "oidc", "sub-out")
        # Remove outsider from default tenant
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute(
            "DELETE FROM tenant_memberships WHERE tenant_id='default' AND user_id=?",
            (outsider_id,),
        )
        conn.commit()
        conn.close()
        client = _make_client(self.mod, outsider_id)
        res = client.get("/api/tenants/default/members")
        self.assertEqual(res.status_code, 403)

    def test_owner_can_add_member(self):
        new_id = self.mod._upsert_user("new@example.com", "New", "oidc", "sub-new")
        # Remove auto-enrollment so we can test explicit add
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute(
            "DELETE FROM tenant_memberships WHERE tenant_id='default' AND user_id=?",
            (new_id,),
        )
        conn.commit()
        conn.close()

        res = self._owner_client().post(
            "/api/tenants/default/members",
            data=json.dumps({"email": "new@example.com", "role": "viewer"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        membership = self.mod._get_tenant_membership(new_id)
        self.assertIsNotNone(membership)
        self.assertEqual(membership["role"], "viewer")

    def test_member_cannot_add_member(self):
        res = self._member_client().post(
            "/api/tenants/default/members",
            data=json.dumps({"email": "owner@example.com", "role": "viewer"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)

    def test_owner_can_remove_member(self):
        res = self._owner_client().delete(
            f"/api/tenants/default/members/{self.member_id}"
        )
        self.assertEqual(res.status_code, 200)
        membership = self.mod._get_tenant_membership(self.member_id)
        self.assertIsNone(membership)

    def test_owner_cannot_remove_themselves(self):
        res = self._owner_client().delete(
            f"/api/tenants/default/members/{self.owner_id}"
        )
        self.assertEqual(res.status_code, 400)

    def test_add_nonexistent_user_returns_404(self):
        res = self._owner_client().post(
            "/api/tenants/default/members",
            data=json.dumps({"email": "ghost@example.com", "role": "member"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
