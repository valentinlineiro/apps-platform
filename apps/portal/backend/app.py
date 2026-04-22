import concurrent.futures
import os
import json
import secrets
import time
import base64
import hashlib
import urllib.parse

import requests as http_requests
import alembic.config
import alembic.command
from flask import Flask, jsonify, redirect, request, session
from flask_cors import CORS
from apps_platform_sdk.observability import setup_logging
from apps_platform_sdk import register_error_handlers, require_session
from adapters.sql.audit_repo import SqlAuditRepository
from adapters.sql.plugin_repo import SqlPluginRepository
from adapters.sql.tenant_repo import SqlTenantRepository
from adapters.sql.user_repo import SqlUserRepository
from adapters.routes.catalog import create_catalog_blueprint
from adapters.routes.profile import create_profile_blueprint
from adapters.routes.tenant_settings import create_tenant_settings_blueprint

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

app = Flask(__name__)
setup_logging(app)
register_error_handlers(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})
_session_secret = os.environ.get("PORTAL_SESSION_SECRET", "")
if not _session_secret:
    import sys
    if os.environ.get("FLASK_ENV") == "production" or os.environ.get("ENFORCE_SESSION_SECRET"):
        print("FATAL: PORTAL_SESSION_SECRET must be set in production", file=sys.stderr)
        sys.exit(1)
    _session_secret = "dev-portal-secret-change-me"
app.secret_key = _session_secret
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
STATIC_APPS_FILE = os.environ.get(
    "STATIC_APPS_FILE",
    os.path.join(os.path.dirname(__file__), "static_apps.json"),
)
DEFAULT_TENANT_ID = "default"
DEFAULT_TENANT_NAME = "Default"
SUPPORTED_MANIFEST_VERSIONS = {1}
ALLOWED_STATUSES = {"stable", "wip", "disabled"}
DEFAULT_ROLE = "member"
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")
OAUTH_AUTHORIZE_URL = os.environ.get("OAUTH_AUTHORIZE_URL", "")
OAUTH_TOKEN_URL = os.environ.get("OAUTH_TOKEN_URL", "")
OAUTH_USERINFO_URL = os.environ.get("OAUTH_USERINFO_URL", "")
OAUTH_SCOPE = os.environ.get("OAUTH_SCOPE", "openid profile email")
OAUTH_REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "")
OAUTH_PROVIDER = os.environ.get("OAUTH_PROVIDER", "oidc")
OAUTH_LOGOUT_URL = os.environ.get("OAUTH_LOGOUT_URL", "")
OAUTH_VERIFY_SSL = os.environ.get("OAUTH_VERIFY_SSL", "true").lower() == "true"


class _PgConn:
    """Thin wrapper around a psycopg2 connection that mimics sqlite3's interface:
    - conn.execute(sql, params) / conn.executemany(sql, seq) return a cursor
    - 'with _PgConn(...) as conn' commits on success, rolls back on error
    - Row access by column name via RealDictCursor
    - SQL placeholders: ? is translated to %s automatically
    """

    def __init__(self, pg_conn: "psycopg2.connection") -> None:
        self._conn = pg_conn
        self._cur = pg_conn.cursor()

    def execute(self, sql: str, params: tuple = ()):
        self._cur.execute(sql.replace("?", "%s"), params)
        return self._cur

    def executemany(self, sql: str, seq_of_params):
        self._cur.executemany(sql.replace("?", "%s"), seq_of_params)
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()


def _db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return _PgConn(conn)


def _ensure_db_exists() -> None:
    """Create the portal database if it does not exist (Postgres only).
    Must be called before _run_alembic_upgrade() so the connection target exists."""
    if not DATABASE_URL or not psycopg2:
        return
    parsed = urllib.parse.urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/")
    # Connect to the maintenance database to run CREATE DATABASE
    admin_url = DATABASE_URL.replace(parsed.path, "/postgres")
    try:
        conn = psycopg2.connect(admin_url)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{db_name}"')
        conn.close()
    except Exception as exc:
        # Non-fatal: Alembic will surface a clear error if the DB is still missing
        app.logger.warning(f"_ensure_db_exists: {exc}")


def _run_alembic_upgrade() -> None:
    """Run alembic upgrade head to ensure the database schema is up-to-date."""
    if not DATABASE_URL:
        app.logger.warning("DATABASE_URL not set, skipping migrations")
        return
    app.logger.info("running database migrations (alembic)")
    try:
        # Resolve config relative to this file
        ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
        cfg = alembic.config.Config(ini_path)
        alembic.command.upgrade(cfg, "head")
        app.logger.info("database migrations complete")
    except Exception as exc:
        app.logger.error(f"database migrations failed: {exc}")


def _init_default_tenant() -> None:
    """Ensure the default tenant exists. Idempotent."""
    now = time.time()
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO tenants (id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (DEFAULT_TENANT_ID, DEFAULT_TENANT_NAME, now, now),
        )


def _install_plugin(conn, tenant_id: str, plugin_id: str, installed_by: str | None = None) -> None:
    """Upsert a plugin install for a tenant. No-op if already active."""
    conn.execute(
        """
        INSERT INTO plugin_installs (tenant_id, plugin_id, installed_at, installed_by, status)
        VALUES (?, ?, ?, ?, 'active')
        ON CONFLICT(tenant_id, plugin_id) DO NOTHING
        """,
        (tenant_id, plugin_id, time.time(), installed_by),
    )


def _sync_plugin_from_manifest(conn, manifest: dict, now: float) -> None:
    """Upsert a plugin and its latest version from a manifest dict."""
    plugin_id = manifest["id"]
    name = manifest.get("name", plugin_id)
    description = manifest.get("description", "")
    icon = manifest.get("icon", "📦")
    conn.execute(
        f"""
        INSERT INTO plugins (id, name, description, icon, visibility, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'internal', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            icon = excluded.icon,
            updated_at = excluded.updated_at
        """,
        (plugin_id, name, description, icon, now, now),
    )
    conn.execute(
        """
        INSERT INTO plugin_versions (plugin_id, version, manifest_json, status, published_at, created_at)
        VALUES (?, '1.0.0', ?, 'published', ?, ?)
        ON CONFLICT(plugin_id, version) DO UPDATE SET
            manifest_json = excluded.manifest_json,
            published_at = excluded.published_at
        """,
        (plugin_id, json.dumps(manifest), now, now),
    )


def _init_static_apps() -> None:
    if not os.path.exists(STATIC_APPS_FILE):
        return
    with open(STATIC_APPS_FILE) as f:
        manifests = json.load(f)
    app.logger.info(f"loading {len(manifests)} static app(s) from {STATIC_APPS_FILE}")
    now = time.time()
    with _db() as conn:
        for manifest in manifests:
            app_url = manifest.get("app_url")
            conn.execute(
                """
                INSERT INTO registry (id, manifest_json, app_url)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    manifest_json = excluded.manifest_json,
                    app_url = excluded.app_url
                """,
                (manifest["id"], json.dumps(manifest), app_url),
            )
            _sync_plugin_from_manifest(conn, manifest, now)
            if manifest.get("status") != "disabled":
                _install_plugin(conn, DEFAULT_TENANT_ID, manifest["id"])


def _available(tenant_id: str) -> list[dict]:
    """Return installed apps for tenant that are currently reachable and permitted.

    Apps without app_url (frontend-only) are always considered available.
    Apps with app_url are checked via GET {app_url}/manifest with a short timeout.
    """
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT r.manifest_json, r.app_url
            FROM registry r
            JOIN plugin_installs pi ON pi.plugin_id = r.id
            WHERE pi.tenant_id = ? AND pi.status = 'active'
            """,
            (tenant_id,),
        ).fetchall()
        tenant_row = conn.execute(
            "SELECT allowed_apps FROM tenants WHERE id = ?", (tenant_id,)
        ).fetchone()

    allowed_apps_list: list[str] | None = None
    if tenant_row and tenant_row["allowed_apps"]:
        try:
            allowed_apps_list = json.loads(tenant_row["allowed_apps"])
        except (ValueError, TypeError):
            pass

    def _is_reachable(app_url: str | None) -> bool:
        if not app_url:
            return True
        try:
            resp = http_requests.get(f"{app_url}/manifest", timeout=1.5)
            return resp.status_code == 200
        except Exception:
            app.logger.debug(f"_available: {app_url} unreachable")
            return False

    available_apps: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_is_reachable, row["app_url"]): row for row in rows}
        for future, row in futures.items():
            if not future.result():
                continue
            manifest = json.loads(row["manifest_json"])
            if allowed_apps_list is not None and manifest.get("id") not in allowed_apps_list:
                continue
            available_apps.append(manifest)
    return available_apps


_RFC1918 = (
    ("10.", 8),
    ("172.16.", 12),
    ("172.17.", 12),
    ("172.18.", 12),
    ("172.19.", 12),
    ("172.20.", 12),
    ("172.21.", 12),
    ("172.22.", 12),
    ("172.23.", 12),
    ("172.24.", 12),
    ("172.25.", 12),
    ("172.26.", 12),
    ("172.27.", 12),
    ("172.28.", 12),
    ("172.29.", 12),
    ("172.30.", 12),
    ("172.31.", 12),
    ("192.168.", 16),
    ("127.", 8),
    ("169.254.", 16),
)


def _is_safe_app_url(url: str) -> bool:
    """Return False for non-http(s) schemes or RFC-1918/loopback addresses."""
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname or ""
    for prefix, _ in _RFC1918:
        if host.startswith(prefix):
            return False
    return True


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _oauth_is_configured() -> bool:
    return all([OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_AUTHORIZE_URL, OAUTH_TOKEN_URL, OAUTH_USERINFO_URL])


def _oauth_redirect_uri() -> str:
    if OAUTH_REDIRECT_URI:
        return OAUTH_REDIRECT_URI
    base = request.url_root.rstrip("/")
    return f"{base}/auth/callback"


def _oauth_logout_url() -> str:
    if OAUTH_LOGOUT_URL:
        return OAUTH_LOGOUT_URL
    parsed = urllib.parse.urlparse(OAUTH_AUTHORIZE_URL)
    if not parsed.scheme or not parsed.netloc or not parsed.path:
        return ""
    if parsed.path.endswith("/auth"):
        logout_path = f"{parsed.path[:-5]}/logout"
    else:
        logout_path = parsed.path.rstrip("/") + "/logout"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, logout_path, "", "", ""))


def _pkce_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _json_metadata(data: dict | None = None) -> str:
    return json.dumps(data or {}, separators=(",", ":"))


def _log_audit(user_id: str | None, action: str, target_type: str | None = None, target_id: str | None = None, metadata: dict | None = None) -> None:
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (user_id, action, target_type, target_id, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, action, target_type, target_id, _json_metadata(metadata), time.time()),
        )


# ── Audit / Catalog / Tenant settings / Tenant members ───────────────────────
# Routes live in adapters/routes/catalog.py and adapters/routes/tenant_settings.py;
# blueprints registered in _bootstrap().


def _upsert_user(email: str, name: str, provider: str, provider_sub: str) -> str:
    now = time.time()
    user_id = f"{provider}:{provider_sub}"
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, name, provider, provider_sub, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, provider_sub) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                updated_at = excluded.updated_at
            """,
            (user_id, email, name, provider, provider_sub, now, now),
        )
        conn.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT ?, id FROM roles WHERE name = ?
            ON CONFLICT DO NOTHING
            """,
            (user_id, DEFAULT_ROLE),
        )
        conn.execute(
            """
            INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tenant_id, user_id) DO NOTHING
            """,
            (DEFAULT_TENANT_ID, user_id, DEFAULT_ROLE, now),
        )
    return user_id


def _get_tenant_membership(user_id: str) -> dict | None:
    """Return the user's primary tenant context, or None if not a member of any tenant."""
    with _db() as conn:
        row = conn.execute(
            """
            SELECT t.id, t.name, tm.role
            FROM tenant_memberships tm
            JOIN tenants t ON t.id = tm.tenant_id
            WHERE tm.user_id = ?
            ORDER BY t.id
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "name": row["name"], "role": row["role"]}


def _get_user_roles(user_id: str) -> list[str]:
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT r.name
            FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ?
            ORDER BY r.name
            """,
            (user_id,),
        ).fetchall()
    return [row["name"] for row in rows]


def _get_current_user() -> dict | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    with _db() as conn:
        row = conn.execute(
            "SELECT id, email, name, provider FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "provider": row["provider"],
        "roles": _get_user_roles(row["id"]),
        "tenant": _get_tenant_membership(row["id"]),
    }




def _validate_manifest(data: object) -> tuple[dict, dict[str, str], int | None]:
    if not isinstance(data, dict):
        return {}, {"manifest": "must be a JSON object"}, None

    field_errors: dict[str, str] = {}
    manifest = data.copy()

    version = manifest.get("manifestVersion")
    if version is None:
        field_errors["manifestVersion"] = "is required"
    elif type(version) is not int:
        field_errors["manifestVersion"] = "must be an integer"
    elif version not in SUPPORTED_MANIFEST_VERSIONS:
        return {}, {}, version

    required_string_fields = ("id", "name", "description", "route", "icon")
    for field in required_string_fields:
        if field not in manifest:
            field_errors[field] = "is required"
            continue
        if not _is_non_empty_string(manifest[field]):
            field_errors[field] = "must be a non-empty string"

    status = manifest.get("status")
    if status is None:
        field_errors["status"] = "is required"
    elif not isinstance(status, str):
        field_errors["status"] = f"must be one of: {', '.join(sorted(ALLOWED_STATUSES))}"
    elif status not in ALLOWED_STATUSES:
        field_errors["status"] = f"must be one of: {', '.join(sorted(ALLOWED_STATUSES))}"

    backend = manifest.get("backend")
    if backend is None:
        pass
    elif not isinstance(backend, dict):
        field_errors["backend"] = "must be null or an object"
    else:
        path_prefix = backend.get("pathPrefix")
        if not _is_non_empty_string(path_prefix):
            field_errors["backend.pathPrefix"] = "must be a non-empty string"

    script_url = manifest.get("scriptUrl")
    if script_url is not None and not _is_non_empty_string(script_url):
        field_errors["scriptUrl"] = "must be a non-empty string"

    element_tag = manifest.get("elementTag")
    if element_tag is not None and not _is_non_empty_string(element_tag):
        field_errors["elementTag"] = "must be a non-empty string"

    if (script_url is None) ^ (element_tag is None):
        field_errors["frontend"] = "scriptUrl and elementTag must be provided together"

    permissions = manifest.get("permissions")
    if permissions is not None:
        if not isinstance(permissions, list) or not all(_is_non_empty_string(p) for p in permissions):
            field_errors["permissions"] = "must be an array of non-empty strings"

    app_url = manifest.get("app_url")
    if app_url is not None:
        if not _is_non_empty_string(app_url):
            field_errors["app_url"] = "must be a non-empty string"
        elif not _is_safe_app_url(app_url):
            field_errors["app_url"] = "must be an http/https URL with a public host"

    publisher = manifest.get("publisher")
    if publisher is not None:
        if not isinstance(publisher, dict):
            field_errors["publisher"] = "must be an object"
        else:
            if not _is_non_empty_string(publisher.get("id")):
                field_errors["publisher.id"] = "must be a non-empty string"
            if not _is_non_empty_string(publisher.get("name")):
                field_errors["publisher.name"] = "must be a non-empty string"

    return manifest, field_errors, None


@app.get("/api/registry")
@require_session
def get_registry():
    membership = _get_tenant_membership(session["user_id"])
    if not membership:
        return jsonify([])
    return jsonify(_available(membership["id"]))




# ── Profile & Preferences ─────────────────────────────────────────────────────
# Routes live in adapters/routes/profile.py; blueprint registered below.




@app.get("/health")
def health():
    try:
        with _db() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "error"}), 503


@app.get("/auth/login")
def auth_login():
    if not _oauth_is_configured():
        return jsonify({"error": "oauth_not_configured"}), 500

    state = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = _pkce_code_challenge(code_verifier)
    session["oauth_state"] = state
    session["oauth_code_verifier"] = code_verifier
    next_path = request.args.get("next", "/")
    session["oauth_next"] = next_path if isinstance(next_path, str) and next_path.startswith("/") else "/"

    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": _oauth_redirect_uri(),
        "scope": OAUTH_SCOPE,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"{OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return redirect(authorize_url, code=302)


@app.get("/auth/callback")
def auth_callback():
    if not _oauth_is_configured():
        return jsonify({"error": "oauth_not_configured"}), 500

    if request.args.get("error"):
        return jsonify(
            {
                "error": "oauth_error",
                "provider_error": request.args.get("error"),
                "provider_error_description": request.args.get("error_description", ""),
            }
        ), 400

    expected_state = session.get("oauth_state")
    code_verifier = session.get("oauth_code_verifier")
    received_state = request.args.get("state")
    code = request.args.get("code")
    if not expected_state or not received_state or expected_state != received_state:
        return jsonify({"error": "invalid_state"}), 400
    if not code_verifier:
        return jsonify({"error": "missing_code_verifier"}), 400
    if not code:
        return jsonify({"error": "missing_code"}), 400

    try:
        token_response = http_requests.post(
            OAUTH_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _oauth_redirect_uri(),
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET,
                "code_verifier": code_verifier,
            },
            timeout=10,
            verify=OAUTH_VERIFY_SSL,
        )
    except http_requests.exceptions.RequestException as exc:
        app.logger.error(f"token exchange network error: {exc}")
        return jsonify({"error": "idp_unreachable"}), 502
    if not token_response.ok:
        app.logger.error(f"token exchange failed: {token_response.status_code} {token_response.text[:200]}")
        return jsonify({"error": "token_exchange_failed"}), 502
    token_payload = token_response.json()
    access_token = token_payload.get("access_token")
    id_token = token_payload.get("id_token")
    if not access_token:
        app.logger.error("token response missing access_token")
        return jsonify({"error": "missing_access_token"}), 502

    try:
        userinfo_response = http_requests.get(
            OAUTH_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
            verify=OAUTH_VERIFY_SSL,
        )
    except http_requests.exceptions.RequestException as exc:
        app.logger.error(f"userinfo network error: {exc}")
        return jsonify({"error": "idp_unreachable"}), 502
    if not userinfo_response.ok:
        app.logger.error(f"userinfo fetch failed: {userinfo_response.status_code}")
        return jsonify({"error": "userinfo_fetch_failed"}), 502
    userinfo = userinfo_response.json()

    provider_sub = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name") or email or str(provider_sub or "")
    if not provider_sub or not email:
        app.logger.error(f"invalid userinfo response: sub={provider_sub!r} email={email!r}")
        return jsonify({"error": "invalid_userinfo"}), 502

    user_id = _upsert_user(email=email, name=name, provider=OAUTH_PROVIDER, provider_sub=provider_sub)
    session.pop("oauth_state", None)
    session.pop("oauth_code_verifier", None)
    if id_token:
        session["oauth_id_token"] = id_token
    next_path = session.pop("oauth_next", "/")
    session["user_id"] = user_id
    _log_audit(user_id, "login", "auth", OAUTH_PROVIDER, {"email": email})
    return redirect(next_path if isinstance(next_path, str) and next_path.startswith("/") else "/", code=302)


@app.get("/auth/logout")
@app.post("/auth/logout")
def auth_logout():
    user_id = session.get("user_id")
    id_token_hint = session.get("oauth_id_token")
    next_path = request.args.get("next", "/")
    if not isinstance(next_path, str) or not next_path.startswith("/"):
        next_path = "/"

    session.clear()
    if user_id:
        _log_audit(user_id, "logout", "auth", OAUTH_PROVIDER)

    logout_url = _oauth_logout_url()
    if logout_url:
        post_logout_redirect_uri = f"{request.url_root.rstrip('/')}{next_path}"
        params = {
            "client_id": OAUTH_CLIENT_ID,
            "post_logout_redirect_uri": post_logout_redirect_uri,
        }
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        return redirect(f"{logout_url}?{urllib.parse.urlencode(params)}", code=302)

    if request.method == "POST":
        return jsonify({"ok": True})
    return redirect(next_path, code=302)


@app.get("/auth/me")
@require_session
def auth_me():
    user = _get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(user)


def _bootstrap():
    _ensure_db_exists()
    _run_alembic_upgrade()
    _init_default_tenant()
    _init_static_apps()
    # Wire blueprints after DB is ready
    _user_repo = SqlUserRepository(_db)
    _tenant_repo = SqlTenantRepository(_db)
    _plugin_repo = SqlPluginRepository(_db)
    _audit_repo = SqlAuditRepository(_db)
    app.register_blueprint(create_profile_blueprint(_user_repo))
    app.register_blueprint(create_tenant_settings_blueprint(_tenant_repo, _audit_repo))
    app.register_blueprint(create_catalog_blueprint(_plugin_repo, _tenant_repo, _audit_repo))


if __name__ == "__main__":
    _bootstrap()
    app.run(host="0.0.0.0", port=5000)


_bootstrap()
