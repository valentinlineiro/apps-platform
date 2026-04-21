import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("PORTAL_SESSION_SECRET", "test-secret")
os.environ.setdefault("OAUTH_CLIENT_ID", "client-id")
os.environ.setdefault("OAUTH_CLIENT_SECRET", "client-secret")
os.environ.setdefault("OAUTH_AUTHORIZE_URL", "https://idp.example.com/authorize")
os.environ.setdefault("OAUTH_TOKEN_URL", "https://idp.example.com/token")
os.environ.setdefault("OAUTH_USERINFO_URL", "https://idp.example.com/userinfo")
os.environ.setdefault("OAUTH_REDIRECT_URI", "http://localhost:5000/auth/callback")
os.environ.setdefault("OAUTH_PROVIDER", "oidc")

_psycopg2_mock = MagicMock()
sys.modules.setdefault("psycopg2", _psycopg2_mock)
sys.modules.setdefault("psycopg2.extras", _psycopg2_mock.extras)

import app as app_module  # noqa: E402


_OAUTH_PATCHES = {
    "OAUTH_CLIENT_ID": "client-id",
    "OAUTH_CLIENT_SECRET": "client-secret",
    "OAUTH_AUTHORIZE_URL": "https://idp.example.com/authorize",
    "OAUTH_TOKEN_URL": "https://idp.example.com/token",
    "OAUTH_USERINFO_URL": "https://idp.example.com/userinfo",
    "OAUTH_REDIRECT_URI": "http://localhost:5000/auth/callback",
    "OAUTH_PROVIDER": "oidc",
}


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch.object(app_module, k, v) for k, v in _OAUTH_PATCHES.items()
        ]
        for p in self.patches:
            p.start()
        self.client = app_module.app.test_client()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_auth_login_redirects_to_provider(self):
        res = self.client.get("/auth/login")
        self.assertEqual(res.status_code, 302)
        location = res.headers.get("Location", "")
        self.assertIn("https://idp.example.com/authorize", location)
        self.assertIn("client_id=client-id", location)
        self.assertIn("state=", location)

    def test_auth_callback_invalid_state(self):
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "expected"
        res = self.client.get("/auth/callback?code=abc&state=wrong")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error"], "invalid_state")

    def test_auth_callback_creates_session(self):
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-123"
            sess["oauth_next"] = "/"
            sess["oauth_code_verifier"] = "test-verifier"

        token_res = Mock(ok=True)
        token_res.json.return_value = {"access_token": "token123"}

        userinfo_res = Mock(ok=True)
        userinfo_res.json.return_value = {
            "sub": "abc123",
            "email": "dev@example.com",
            "name": "Dev User",
        }

        with (
            patch.object(app_module.http_requests, "post", return_value=token_res),
            patch.object(app_module.http_requests, "get", return_value=userinfo_res),
            patch.object(app_module, "_upsert_user", return_value="oidc:abc123"),
            patch.object(app_module, "_get_tenant_membership", return_value={"id": "default", "role": "member"}),
        ):
            res = self.client.get("/auth/callback?code=ok-code&state=state-123")

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("Location"), "/")

    def test_auth_me_requires_login(self):
        res = self.client.get("/auth/me")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json()["error"], "unauthorized")

    def test_auth_me_returns_user(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = "oidc:test-user"

        mock_me = {
            "id": "oidc:test-user",
            "email": "dev@example.com",
            "name": "Dev User",
            "roles": ["member"],
            "tenant": {"id": "default", "name": "Default"},
        }

        with patch.object(app_module, "_get_current_user", return_value=mock_me):
            res = self.client.get("/auth/me")

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["email"], "dev@example.com")


if __name__ == "__main__":
    unittest.main()
