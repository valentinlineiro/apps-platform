"""Install management and registry filter tests.

These tests mock the application (use-case) layer to verify HTTP behaviour
without requiring a live database. See test_registry.py for _available()
unit tests.
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
from domain.plugin import PluginInstall  # noqa: E402

_EXAM_INSTALL = PluginInstall(
    plugin_id="exam-corrector",
    status="active",
    installed_at=0.0,
    installed_by=None,
    alive=True,
    manifest={
        "manifestVersion": 1,
        "id": "exam-corrector",
        "name": "exam-corrector",
        "route": "exam-corrector",
        "icon": "📝",
        "status": "stable",
    },
)

_SUSPENDED_INSTALL = PluginInstall(
    plugin_id="exam-corrector",
    status="suspended",
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


class RegistryTenantFilterTests(unittest.TestCase):
    """GET /api/registry returns only active+available apps for the caller's tenant."""

    def setUp(self):
        self.client = _authed_client()

    def test_registry_returns_installed_active_app(self):
        manifest = {"id": "exam-corrector", "name": "exam-corrector"}
        with (
            patch.object(app_module, "_get_tenant_membership", return_value={"id": "default"}),
            patch.object(app_module, "_available", return_value=[manifest]),
        ):
            res = self.client.get("/api/registry")
        self.assertEqual(res.status_code, 200)
        apps = res.get_json()
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["id"], "exam-corrector")

    def test_registry_returns_empty_for_suspended_app(self):
        # Suspended apps are excluded from _available() query (status != 'active')
        with (
            patch.object(app_module, "_get_tenant_membership", return_value={"id": "default"}),
            patch.object(app_module, "_available", return_value=[]),
        ):
            res = self.client.get("/api/registry")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

    def test_registry_returns_empty_for_user_with_no_tenant(self):
        with patch.object(app_module, "_get_tenant_membership", return_value=None):
            res = self.client.get("/api/registry")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

    def test_registry_requires_session(self):
        res = app_module.app.test_client().get("/api/registry")
        self.assertIn(res.status_code, (401, 302))


class InstallManagementTests(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()

    def test_list_installs_shows_installed_app(self):
        with patch.object(uc, "list_installs", return_value=[_EXAM_INSTALL]):
            res = self.client.get("/api/tenants/default/installs")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["plugin_id"], "exam-corrector")
        self.assertEqual(data[0]["status"], "active")

    def test_list_installs_includes_alive_flag(self):
        with patch.object(uc, "list_installs", return_value=[_EXAM_INSTALL]):
            res = self.client.get("/api/tenants/default/installs")
        data = res.get_json()
        self.assertIn("alive", data[0])
        self.assertTrue(data[0]["alive"])

    def test_owner_can_suspend_install(self):
        with patch.object(uc, "update_install_status", return_value=None):
            res = self.client.patch(
                "/api/tenants/default/installs/exam-corrector",
                data=json.dumps({"status": "suspended"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)

    def test_owner_can_uninstall(self):
        with patch.object(uc, "uninstall_plugin", return_value=None):
            res = self.client.delete("/api/tenants/default/installs/exam-corrector")
        self.assertEqual(res.status_code, 200)

    def test_member_forbidden_to_suspend(self):
        from domain.errors import ForbiddenError
        with patch.object(uc, "update_install_status", side_effect=ForbiddenError("admin only")):
            res = self.client.patch(
                "/api/tenants/default/installs/exam-corrector",
                data=json.dumps({"status": "suspended"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 403)

    def test_member_forbidden_to_uninstall(self):
        from domain.errors import ForbiddenError
        with patch.object(uc, "uninstall_plugin", side_effect=ForbiddenError("admin only")):
            res = self.client.delete("/api/tenants/default/installs/exam-corrector")
        self.assertEqual(res.status_code, 403)

    def test_install_unknown_plugin_returns_404(self):
        from domain.errors import NotFoundError
        with patch.object(uc, "install_plugin", side_effect=NotFoundError("plugin not found")):
            res = self.client.post(
                "/api/tenants/default/installs",
                data=json.dumps({"plugin_id": "nonexistent-app"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 404)

    def test_patch_invalid_status_returns_400(self):
        from domain.errors import ValidationError
        with patch.object(uc, "update_install_status", side_effect=ValidationError("bad status")):
            res = self.client.patch(
                "/api/tenants/default/installs/exam-corrector",
                data=json.dumps({"status": "broken"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 400)

    def test_install_already_installed_is_idempotent(self):
        with patch.object(uc, "install_plugin", return_value=None):
            res = self.client.post(
                "/api/tenants/default/installs",
                data=json.dumps({"plugin_id": "exam-corrector"}),
                content_type="application/json",
            )
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
