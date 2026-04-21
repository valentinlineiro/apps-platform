import importlib
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

import app as app_module  # noqa: E402  (must be after mock injection)

_EXAM_MANIFEST = {
    "manifestVersion": 1,
    "id": "exam-corrector",
    "name": "exam-corrector",
    "description": "Corrección automática de exámenes",
    "route": "exam-corrector",
    "icon": "📝",
    "status": "stable",
    "scriptUrl": "/apps/exam-corrector/element/main.js",
    "elementTag": "exam-corrector-app",
    "backend": {"pathPrefix": "/exam-corrector/"},
}

_STATIC_MANIFEST = {
    "manifestVersion": 1,
    "id": "attendance-checker",
    "name": "attendance-checker",
    "description": "Registro de asistencia",
    "route": "attendance-checker",
    "icon": "📋",
    "status": "stable",
    "scriptUrl": "/apps/attendance-checker/element/main.js",
    "elementTag": "attendance-checker-app",
    "backend": None,
}


class RegistryApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as sess:
            sess["user_id"] = "oidc:test-user"

    def _membership(self, tenant_id="default"):
        return {"id": tenant_id, "role": "member"}

    def test_registry_returns_available_apps_with_reachable_url(self):
        """Apps whose app_url responds HTTP 200 appear in the registry."""
        with (
            patch.object(app_module, "_get_tenant_membership", return_value=self._membership()),
            patch.object(app_module, "_available", return_value=[_EXAM_MANIFEST]) as mock_avail,
        ):
            res = self.client.get("/api/registry")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], "exam-corrector")
        mock_avail.assert_called_once_with("default")

    def test_registry_excludes_unreachable_apps(self):
        """Apps whose app_url is unreachable are excluded."""
        with (
            patch.object(app_module, "_get_tenant_membership", return_value=self._membership()),
            patch.object(app_module, "_available", return_value=[]),
        ):
            res = self.client.get("/api/registry")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

    def test_registry_includes_static_apps_without_url(self):
        """Apps with no app_url (frontend-only) are always included."""
        with (
            patch.object(app_module, "_get_tenant_membership", return_value=self._membership()),
            patch.object(app_module, "_available", return_value=[_STATIC_MANIFEST]),
        ):
            res = self.client.get("/api/registry")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(payload[0]["id"], "attendance-checker")

    def test_registry_returns_empty_for_unknown_user(self):
        """Users with no tenant membership get an empty registry."""
        with patch.object(app_module, "_get_tenant_membership", return_value=None):
            res = self.client.get("/api/registry")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

    def test_registry_requires_session(self):
        """Unauthenticated requests are rejected."""
        client = app_module.app.test_client()  # fresh client, no session
        res = client.get("/api/registry")
        self.assertIn(res.status_code, (401, 302))


class AvailabilityCheckTests(unittest.TestCase):
    """Unit tests for _available() — verifies HTTP liveness logic."""

    def _make_row(self, manifest, app_url):
        return {"manifest_json": __import__("json").dumps(manifest), "app_url": app_url}

    def test_available_includes_reachable_app(self):
        rows = [self._make_row(_EXAM_MANIFEST, "http://exam-corrector-backend:5000")]
        ok_response = MagicMock(status_code=200)
        with (
            patch.object(app_module, "_db") as mock_db,
            patch("app.http_requests.get", return_value=ok_response),
        ):
            mock_conn = MagicMock()
            mock_conn.__enter__ = lambda s: mock_conn
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = rows
            mock_db.return_value = mock_conn

            result = app_module._available("default")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "exam-corrector")

    def test_available_excludes_unreachable_app(self):
        rows = [self._make_row(_EXAM_MANIFEST, "http://exam-corrector-backend:5000")]
        with (
            patch.object(app_module, "_db") as mock_db,
            patch("app.http_requests.get", side_effect=ConnectionError("refused")),
        ):
            mock_conn = MagicMock()
            mock_conn.__enter__ = lambda s: mock_conn
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = rows
            mock_db.return_value = mock_conn

            result = app_module._available("default")

        self.assertEqual(result, [])

    def test_available_always_includes_app_without_url(self):
        rows = [self._make_row(_STATIC_MANIFEST, None)]
        with patch.object(app_module, "_db") as mock_db:
            mock_conn = MagicMock()
            mock_conn.__enter__ = lambda s: mock_conn
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = rows
            mock_db.return_value = mock_conn

            result = app_module._available("default")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "attendance-checker")


if __name__ == "__main__":
    unittest.main()
