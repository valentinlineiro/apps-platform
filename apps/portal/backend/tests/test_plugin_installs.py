import importlib
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_MANIFEST = {
    "manifestVersion": 1,
    "id": "exam-corrector",
    "name": "Exam Corrector",
    "description": "Corrección automática",
    "route": "exam-corrector",
    "icon": "📝",
    "status": "stable",
    "scriptUrl": "/apps/exam-corrector/element/main.js",
    "elementTag": "exam-corrector-app",
    "backend": {"pathPrefix": "/exam-corrector/"},
}


def _load_module(db_path: str):
    os.environ["REGISTRY_DB_PATH"] = db_path
    os.environ["PORTAL_SESSION_SECRET"] = "test-secret"
    os.environ.pop("DATABASE_URL", None)
    # Point to an empty static apps file so tests aren't polluted by real entries
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


class RegistryTenantFilterTests(unittest.TestCase):
    """GET /api/registry returns only installed+alive apps for the caller's tenant."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.user_id = self.mod._upsert_user("u@example.com", "U", "oidc", "sub-u")

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("REGISTRY_DB_PATH", "PORTAL_SESSION_SECRET", "STATIC_APPS_FILE", "DATABASE_URL"):
            os.environ.pop(k, None)

    def _register(self):
        return _client(self.mod).post("/api/registry/register", json=_MANIFEST)

    def test_register_auto_installs_into_default_tenant(self):
        res = self._register()
        self.assertEqual(res.status_code, 200)
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        row = conn.execute(
            "SELECT status FROM plugin_installs WHERE tenant_id='default' AND plugin_id='exam-corrector'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "active")

    def test_registry_returns_installed_app_for_member(self):
        self._register()
        res = _client(self.mod, self.user_id).get("/api/registry")
        self.assertEqual(res.status_code, 200)
        apps = json.loads(res.data)
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["id"], "exam-corrector")

    def test_registry_excludes_suspended_app(self):
        self._register()
        # Suspend the install
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute(
            "UPDATE plugin_installs SET status='suspended' WHERE tenant_id='default' AND plugin_id='exam-corrector'"
        )
        conn.commit()
        conn.close()

        res = _client(self.mod, self.user_id).get("/api/registry")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [])

    def test_registry_excludes_stale_heartbeat(self):
        self._register()
        # Wind back the heartbeat so the app appears dead
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute("UPDATE registry SET last_heartbeat=0 WHERE id='exam-corrector'")
        conn.commit()
        conn.close()

        res = _client(self.mod, self.user_id).get("/api/registry")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [])

    def test_registry_excludes_uninstalled_app(self):
        self._register()
        # Remove the install record entirely
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute(
            "DELETE FROM plugin_installs WHERE tenant_id='default' AND plugin_id='exam-corrector'"
        )
        conn.commit()
        conn.close()

        res = _client(self.mod, self.user_id).get("/api/registry")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [])

    def test_registry_returns_empty_for_user_with_no_tenant(self):
        self._register()
        orphan_id = self.mod._upsert_user("orphan@x.com", "Orphan", "oidc", "sub-orphan")
        # Remove from default tenant
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute(
            "DELETE FROM tenant_memberships WHERE tenant_id='default' AND user_id=?",
            (orphan_id,),
        )
        conn.commit()
        conn.close()

        res = _client(self.mod, orphan_id).get("/api/registry")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [])


class InstallManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.owner_id = _make_owner(self.mod)
        self.member_id = self.mod._upsert_user("m@example.com", "M", "oidc", "sub-m")
        # Register the app so it exists in the registry
        _client(self.mod).post("/api/registry/register", json=_MANIFEST)

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("REGISTRY_DB_PATH", "PORTAL_SESSION_SECRET", "STATIC_APPS_FILE", "DATABASE_URL"):
            os.environ.pop(k, None)

    def _owner(self):
        return _client(self.mod, self.owner_id)

    def _member(self):
        return _client(self.mod, self.member_id)

    def test_list_installs_shows_installed_app(self):
        res = self._owner().get("/api/tenants/default/installs")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["plugin_id"], "exam-corrector")
        self.assertEqual(data[0]["status"], "active")

    def test_member_can_list_installs(self):
        res = self._member().get("/api/tenants/default/installs")
        self.assertEqual(res.status_code, 200)

    def test_owner_can_suspend_install(self):
        res = self._owner().patch(
            "/api/tenants/default/installs/exam-corrector",
            data=json.dumps({"status": "suspended"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        # Should now be absent from registry
        registry = json.loads(_client(self.mod, self.member_id).get("/api/registry").data)
        self.assertEqual(registry, [])

    def test_owner_can_reactivate_install(self):
        # Suspend then reactivate
        self._owner().patch(
            "/api/tenants/default/installs/exam-corrector",
            data=json.dumps({"status": "suspended"}),
            content_type="application/json",
        )
        self._owner().patch(
            "/api/tenants/default/installs/exam-corrector",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
        )
        registry = json.loads(_client(self.mod, self.member_id).get("/api/registry").data)
        self.assertEqual(len(registry), 1)

    def test_member_cannot_suspend_install(self):
        res = self._member().patch(
            "/api/tenants/default/installs/exam-corrector",
            data=json.dumps({"status": "suspended"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)

    def test_owner_can_uninstall(self):
        res = self._owner().delete("/api/tenants/default/installs/exam-corrector")
        self.assertEqual(res.status_code, 200)
        registry = json.loads(_client(self.mod, self.member_id).get("/api/registry").data)
        self.assertEqual(registry, [])

    def test_member_cannot_uninstall(self):
        res = self._member().delete("/api/tenants/default/installs/exam-corrector")
        self.assertEqual(res.status_code, 403)

    def test_install_unknown_plugin_returns_404(self):
        res = self._owner().post(
            "/api/tenants/default/installs",
            data=json.dumps({"plugin_id": "nonexistent-app"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_install_already_installed_is_idempotent(self):
        res = self._owner().post(
            "/api/tenants/default/installs",
            data=json.dumps({"plugin_id": "exam-corrector"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        # Still only one record
        installs = json.loads(self._owner().get("/api/tenants/default/installs").data)
        self.assertEqual(len(installs), 1)

    def test_patch_invalid_status_returns_400(self):
        res = self._owner().patch(
            "/api/tenants/default/installs/exam-corrector",
            data=json.dumps({"status": "broken"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_list_installs_includes_alive_flag(self):
        res = self._owner().get("/api/tenants/default/installs")
        data = json.loads(res.data)
        self.assertIn("alive", data[0])
        self.assertTrue(data[0]["alive"])  # heartbeat just sent during register


if __name__ == "__main__":
    unittest.main()
