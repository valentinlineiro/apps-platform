import os
import alembic.config
import alembic.command

from flask import Flask, jsonify
from flask_cors import CORS
from apps_platform_sdk.observability import setup_logging
from apps_platform_sdk import register_error_handlers

from adapters.routes.aneca import create_aneca_blueprint
from adapters.sql.article_repo import SqlArticleRepository
from adapters.sql.journal_repo import SqlJournalQuartileGateway

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

app = Flask(__name__, static_folder="static", static_url_path="/apps/aneca-advisor")
setup_logging(app)
register_error_handlers(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.secret_key = os.environ.get("PORTAL_SESSION_SECRET", "dev-portal-secret-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_MANIFEST = {
    "manifestVersion": 1,
    "id": "aneca-advisor",
    "name": "ANECA Advisor",
    "description": "Simulador de acreditación ANECA para investigadores universitarios",
    "route": "aneca-advisor",
    "icon": "🎓",
    "status": "wip",
    "scriptUrl": "/apps/aneca-advisor/element/main.js",
    "elementTag": "aneca-advisor-app",
    "backend": {"pathPrefix": "/api/aneca/"},
}


class _PgConn:
    def __init__(self, pg_conn) -> None:
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


def _run_alembic_upgrade() -> None:
    """Run alembic upgrade head to ensure the database schema is up-to-date."""
    if not DATABASE_URL:
        app.logger.warning("DATABASE_URL not set, skipping migrations")
        return
    app.logger.info("running database migrations (alembic)")
    try:
        ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
        cfg = alembic.config.Config(ini_path)
        alembic.command.upgrade(cfg, "head")
        app.logger.info("database migrations complete")
    except Exception as exc:
        app.logger.error(f"database migrations failed: {exc}")


@app.get("/manifest")
def manifest():
    return jsonify(_MANIFEST)


def _bootstrap() -> None:
    _run_alembic_upgrade()
    journal_repo = SqlJournalQuartileGateway(_db)
    article_repo = SqlArticleRepository(_db)
    app.register_blueprint(create_aneca_blueprint(journal_repo, article_repo))


if __name__ == "__main__":
    _bootstrap()
    app.run(host="0.0.0.0", port=5001)

_bootstrap()
