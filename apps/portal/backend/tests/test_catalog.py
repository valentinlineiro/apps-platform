"""Catalog and install management HTTP route tests.

These tests mock the application (use-case) layer and verify HTTP behaviour:
auth enforcement, status codes, and response schema. SQL repo logic is an
integration concern that requires DATABASE_URL — run docker compose for that.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

_psycopg2_mock = MagicMock()
sys.modules.setdefault("psycopg2", _psycopg2_mock)
sys.modules.setdefault("psycopg2.extras", _psycopg2_mock.extras)

import app as app_module  # noqa: E402
import application.catalog as uc  # noqa: E402
from domain.plugin import CatalogEntry, PluginInstall  # noqa: E402

_EXAM_ENTRY = CatalogEntry(
    plugin_id="exam-corrector",
    name="Exam Corrector",
    description="Corrección automática",
    icon="📝",
    version="1.0.0",
    installed=True,
    install_status="active",
    manifest={"id": "exam-corrector"},
)

_SECOND_ENTRY = CatalogEntry(
    plugin_id="second-app",
    name="Second App",
    description="Another tool",
    icon="🔧",
    version="1.0.0",
    installed=False,
    install_status=None,
    manifest={"id": "second-app"},
)

_EXAM_INSTALL = PluginInstall(
    plugin_id="exam-corrector",
    status="active",
    installed_at=0.0,
    installed_by=None,
    alive=True,
    manifest={"id": "exam-corrector"},
)


def _authed_client(user_id="oidc:test-user"):
    c = app_module.app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = user_id
    return c


class CatalogRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()

    def test_catalog_requires_auth(self):
        res = app_module.app.test_client().get("/api/catalog")
        self.assertEqual(res.status_code, 401)

    def test_catalog_returns_entries(self):
        with patch.object(uc, "get_catalog", return_value=[_EXAM_ENTRY, _SECOND_ENTRY]):
            res = self.client.get("/api/catalog")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        ids = {e["plugin_id"] for e in data}
        self.assertIn("exam-corrector", ids)
        self.assertIn("second-app", ids)

    def test_catalog_entry_has_expected_fields(self):
        with patch.object(uc, "get_catalog", return_value=[_EXAM_ENTRY]):
            res = self.client.get("/api/catalog")
        entry = res.get_json()[0]
        for field in ("plugin_id", "name", "description", "icon", "version", "installed", "manifest"):
            self.assertIn(field, entry, f"missing field: {field}")

    def test_catalog_installed_flag(self):
        with patch.object(uc, "get_catalog", return_value=[_EXAM_ENTRY, _SECOND_ENTRY]):
            res = self.client.get("/api/catalog")
        by_id = {e["plugin_id"]: e for e in res.get_json()}
        self.assertTrue(by_id["exam-corrector"]["installed"])
        self.assertFalse(by_id["second-app"]["installed"])


class InstallRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()

    def test_list_installs_requires_auth(self):
        res = app_module.app.test_client().get("/api/tenants/default/installs")
        self.assertEqual(res.status_code, 401)

    def test_list_installs_returns_list(self):
        with patch.object(uc, "list_installs", return_value=[_EXAM_INSTALL]):
            res = self.client.get("/api/tenants/default/installs")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["plugin_id"], "exam-corrector")
        self.assertEqual(data[0]["status"], "active")
        self.assertTrue(data[0]["alive"])

    def test_install_plugin_success(self):
        with patch.object(uc, "install_plugin", return_value=None):
            res = self.client.post(
                "/api/tenants/default/installs",
                data=json.dumps({"plugin_id": "exam-corrector"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)

    def test_install_unknown_plugin_returns_404(self):
        from domain.errors import NotFoundError
        with patch.object(uc, "install_plugin", side_effect=NotFoundError("plugin not found")):
            res = self.client.post(
                "/api/tenants/default/installs",
                data=json.dumps({"plugin_id": "nonexistent"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 404)

    def test_patch_status_success(self):
        with patch.object(uc, "update_install_status", return_value=None):
            res = self.client.patch(
                "/api/tenants/default/installs/exam-corrector",
                data=json.dumps({"status": "suspended"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)

    def test_patch_invalid_status_returns_400(self):
        from domain.errors import ValidationError
        with patch.object(uc, "update_install_status", side_effect=ValidationError("bad status")):
            res = self.client.patch(
                "/api/tenants/default/installs/exam-corrector",
                data=json.dumps({"status": "broken"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 400)

    def test_uninstall_success(self):
        with patch.object(uc, "uninstall_plugin", return_value=None):
            res = self.client.delete("/api/tenants/default/installs/exam-corrector")
        self.assertEqual(res.status_code, 200)

    def test_member_forbidden_to_install(self):
        from domain.errors import ForbiddenError
        with patch.object(uc, "install_plugin", side_effect=ForbiddenError("admin only")):
            res = self.client.post(
                "/api/tenants/default/installs",
                data=json.dumps({"plugin_id": "exam-corrector"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
