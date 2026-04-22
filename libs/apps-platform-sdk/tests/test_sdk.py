from unittest.mock import MagicMock, patch, call
import pytest
import apps_platform_sdk
from apps_platform_sdk.database.pg_conn import PgConn, make_db_factory
from apps_platform_sdk.database.migrations import run_alembic_upgrade
from apps_platform_sdk.manifest import create_manifest_blueprint
from apps_platform_sdk.flask_app import configure_app


def test_sdk_import():
    assert apps_platform_sdk is not None


# ── PgConn ────────────────────────────────────────────────────────────────────

def _make_pg_conn():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    return PgConn(mock_conn), mock_conn, mock_cur


def test_pg_conn_translates_placeholders():
    pc, _, mock_cur = _make_pg_conn()
    pc.execute("SELECT * FROM t WHERE id = ? AND x = ?", (1, 2))
    mock_cur.execute.assert_called_once_with("SELECT * FROM t WHERE id = %s AND x = %s", (1, 2))


def test_pg_conn_execute_returns_cursor():
    pc, _, mock_cur = _make_pg_conn()
    result = pc.execute("SELECT 1")
    assert result is mock_cur


def test_pg_conn_executemany_translates_placeholders():
    pc, _, mock_cur = _make_pg_conn()
    pc.executemany("INSERT INTO t VALUES (?)", [(1,), (2,)])
    mock_cur.executemany.assert_called_once_with("INSERT INTO t VALUES (%s)", [(1,), (2,)])


def test_pg_conn_context_manager_commits_on_success():
    pc, mock_conn, _ = _make_pg_conn()
    with pc:
        pass
    mock_conn.commit.assert_called_once()
    mock_conn.rollback.assert_not_called()
    mock_conn.close.assert_called_once()


def test_pg_conn_context_manager_rolls_back_on_exception():
    pc, mock_conn, _ = _make_pg_conn()
    with pytest.raises(ValueError):
        with pc:
            raise ValueError("boom")
    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_called_once()


def test_make_db_factory_returns_callable():
    factory = make_db_factory("postgresql://localhost/test")
    assert callable(factory)


def test_make_db_factory_uses_database_url():
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = MagicMock()
    with patch("psycopg2.connect", return_value=mock_conn) as mock_connect:
        import psycopg2.extras
        factory = make_db_factory("postgresql://localhost/mydb")
        result = factory()
        mock_connect.assert_called_once_with(
            "postgresql://localhost/mydb",
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    assert isinstance(result, PgConn)


# ── run_alembic_upgrade ───────────────────────────────────────────────────────

def test_run_alembic_upgrade_skips_when_no_url():
    mock_logger = MagicMock()
    run_alembic_upgrade("", "alembic.ini", mock_logger)
    mock_logger.warning.assert_called_once()
    mock_logger.info.assert_not_called()


def test_run_alembic_upgrade_calls_alembic(tmp_path):
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\n")
    mock_logger = MagicMock()
    with patch("alembic.config.Config") as mock_cfg_cls, \
         patch("alembic.command.upgrade") as mock_upgrade:
        run_alembic_upgrade("postgresql://localhost/db", str(ini), mock_logger)
    mock_cfg_cls.assert_called_once_with(str(ini))
    mock_upgrade.assert_called_once_with(mock_cfg_cls.return_value, "head")
    assert mock_logger.info.call_count == 2


def test_run_alembic_upgrade_logs_error_on_failure(tmp_path):
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\n")
    mock_logger = MagicMock()
    with patch("alembic.config.Config"), \
         patch("alembic.command.upgrade", side_effect=RuntimeError("db down")):
        run_alembic_upgrade("postgresql://localhost/db", str(ini), mock_logger)
    mock_logger.error.assert_called_once()
    _, kwargs = mock_logger.error.call_args
    assert kwargs.get("exc_info") is True


# ── create_manifest_blueprint ─────────────────────────────────────────────────

@pytest.fixture
def manifest_client():
    from flask import Flask
    _manifest = {"manifestVersion": 1, "id": "test-app", "name": "Test"}
    flask_app = Flask(__name__)
    flask_app.register_blueprint(create_manifest_blueprint(_manifest))
    flask_app.config["TESTING"] = True
    return flask_app.test_client(), _manifest


def test_manifest_endpoint_returns_manifest(manifest_client):
    client, manifest = manifest_client
    resp = client.get("/manifest")
    assert resp.status_code == 200
    assert resp.get_json() == manifest


def test_manifest_endpoint_content_type(manifest_client):
    client, _ = manifest_client
    resp = client.get("/manifest")
    assert "application/json" in resp.content_type


# ── configure_app ─────────────────────────────────────────────────────────────

def test_configure_app_returns_app():
    from flask import Flask
    flask_app = Flask(__name__)
    result = configure_app(flask_app)
    assert result is flask_app


def test_configure_app_sets_session_cookie_defaults(monkeypatch):
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    from flask import Flask
    flask_app = Flask(__name__)
    configure_app(flask_app)
    assert flask_app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert flask_app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert flask_app.config["SESSION_COOKIE_SECURE"] is False


def test_configure_app_session_cookie_secure_from_env(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    from flask import Flask
    flask_app = Flask(__name__)
    configure_app(flask_app)
    assert flask_app.config["SESSION_COOKIE_SECURE"] is True


def test_configure_app_skips_session_when_disabled():
    from flask import Flask
    flask_app = Flask(__name__)
    configure_app(flask_app, configure_session=False)
    # Flask's default for SAMESITE is None; configure_app sets it to "Lax" only when configure_session=True
    assert flask_app.config.get("SESSION_COOKIE_SAMESITE") != "Lax"
