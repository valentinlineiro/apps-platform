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

_MANIFEST_A = {
    "manifestVersion": 1,
    "id": "exam-corrector",
    "name": "Exam Corrector",
    "description": "Corrección automática de exámenes",
    "route": "exam-corrector",
    "icon": "📝",
    "status": "stable",
    "scriptUrl": "/apps/exam-corrector/element/main.js",
    "elementTag": "exam-corrector-app",
    "backend": {"pathPrefix": "/exam-corrector/"},
}

_MANIFEST_B = {
    "manifestVersion": 1,
    "id": "second-app",
    "name": "Second App",
    "description": "Another tool",
    "route": "second-app",
    "icon": "🔧",
    "status": "stable",
    "scriptUrl": "/apps/second-app/element/main.js",
    "elementTag": "second-app-app",
    "backend": {"pathPrefix": "/second-app/"},
}


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


class PluginSyncTests(unittest.TestCase):
    """plugins + plugin_versions tables are populated on register."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("REGISTRY_DB_PATH", "PORTAL_SESSION_SECRET", "STATIC_APPS_FILE", "DATABASE_URL"):
            os.environ.pop(k, None)

    def _register(self, manifest=_MANIFEST_A):
        return _client(self.mod).post("/api/registry/register", json=manifest)

    def test_register_creates_plugin_record(self):
        self._register()
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        row = conn.execute("SELECT id, name, icon FROM plugins WHERE id='exam-corrector'").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "Exam Corrector")
        self.assertEqual(row[2], "📝")

    def test_register_creates_plugin_version(self):
        self._register()
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        row = conn.execute(
            "SELECT version, status FROM plugin_versions WHERE plugin_id='exam-corrector'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "1.0.0")
        self.assertEqual(row[1], "published")

    def test_register_updates_plugin_on_re_register(self):
        self._register()
        updated = {**_MANIFEST_A, "name": "Exam Corrector Updated", "icon": "✏️"}
        self._register(updated)
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        row = conn.execute("SELECT name, icon FROM plugins WHERE id='exam-corrector'").fetchone()
        conn.close()
        self.assertEqual(row[0], "Exam Corrector Updated")
        self.assertEqual(row[1], "✏️")

    def test_static_apps_sync_populates_plugins(self):
        db_path = str(Path(self.tmp.name) / "portal2.sqlite3")
        static_path = str(Path(self.tmp.name) / "static.json")
        with open(static_path, "w") as f:
            json.dump([_MANIFEST_A], f)
        os.environ["STATIC_APPS_FILE"] = static_path
        os.environ["REGISTRY_DB_PATH"] = db_path
        mod = importlib.reload(importlib.import_module("app"))
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT id FROM plugins WHERE id='exam-corrector'").fetchone()
        conn.close()
        self.assertIsNotNone(row)


class CatalogEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = _load_module(str(Path(self.tmp.name) / "portal.sqlite3"))
        self.owner_id = _make_owner(self.mod)
        self.member_id = self.mod._upsert_user("m@example.com", "M", "oidc", "sub-m")
        _client(self.mod).post("/api/registry/register", json=_MANIFEST_A)
        _client(self.mod).post("/api/registry/register", json=_MANIFEST_B)

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("REGISTRY_DB_PATH", "PORTAL_SESSION_SECRET", "STATIC_APPS_FILE", "DATABASE_URL"):
            os.environ.pop(k, None)

    def _owner(self):
        return _client(self.mod, self.owner_id)

    def _member(self):
        return _client(self.mod, self.member_id)

    def test_catalog_requires_auth(self):
        res = _client(self.mod).get("/api/catalog")
        self.assertEqual(res.status_code, 401)

    def test_catalog_returns_all_plugins(self):
        res = self._member().get("/api/catalog")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        ids = {e["plugin_id"] for e in data}
        self.assertIn("exam-corrector", ids)
        self.assertIn("second-app", ids)

    def test_catalog_includes_installed_flag(self):
        res = self._member().get("/api/catalog")
        data = json.loads(res.data)
        # Both are auto-installed on register
        for entry in data:
            self.assertIn("installed", entry)
            self.assertTrue(entry["installed"])

    def test_catalog_shows_uninstalled_after_removal(self):
        # Uninstall second-app
        self._owner().delete("/api/tenants/default/installs/second-app")
        res = self._member().get("/api/catalog")
        data = json.loads(res.data)
        by_id = {e["plugin_id"]: e for e in data}
        self.assertFalse(by_id["second-app"]["installed"])
        self.assertTrue(by_id["exam-corrector"]["installed"])

    def test_catalog_entry_has_expected_fields(self):
        res = self._member().get("/api/catalog")
        data = json.loads(res.data)
        entry = next(e for e in data if e["plugin_id"] == "exam-corrector")
        for field in ("plugin_id", "name", "description", "icon", "version", "installed", "manifest"):
            self.assertIn(field, entry, f"missing field: {field}")
        self.assertEqual(entry["name"], "Exam Corrector")
        self.assertEqual(entry["icon"], "📝")
        self.assertEqual(entry["version"], "1.0.0")

    def test_install_from_catalog_then_appears_installed(self):
        # Uninstall then re-install via catalog endpoint
        self._owner().delete("/api/tenants/default/installs/second-app")
        res = self._owner().post(
            "/api/tenants/default/installs",
            data=json.dumps({"plugin_id": "second-app"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        catalog = json.loads(self._member().get("/api/catalog").data)
        entry = next(e for e in catalog if e["plugin_id"] == "second-app")
        self.assertTrue(entry["installed"])

    def test_catalog_returns_empty_for_user_with_no_tenant(self):
        orphan_id = self.mod._upsert_user("orphan@x.com", "Orphan", "oidc", "sub-orphan")
        conn = sqlite3.connect(os.environ["REGISTRY_DB_PATH"])
        conn.execute(
            "DELETE FROM tenant_memberships WHERE tenant_id='default' AND user_id=?",
            (orphan_id,),
        )
        conn.commit()
        conn.close()
        res = _client(self.mod, orphan_id).get("/api/catalog")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [])


if __name__ == "__main__":
    unittest.main()
