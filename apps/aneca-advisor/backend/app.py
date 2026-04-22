import os

from flask import Flask
from flask_cors import CORS
from apps_platform_sdk import configure_app, create_manifest_blueprint, make_db_factory, run_alembic_upgrade

from adapters.routes.aneca import create_aneca_blueprint
from adapters.sql.article_repo import SqlArticleRepository
from adapters.sql.journal_repo import SqlJournalQuartileGateway

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

app = Flask(__name__, static_folder="static", static_url_path="/apps/aneca-advisor")
configure_app(app, cors_resources={r"/api/*": {"origins": "*"}})
app.secret_key = os.environ.get("PORTAL_SESSION_SECRET", "dev-portal-secret-change-me")

_db = make_db_factory(DATABASE_URL)


def _bootstrap() -> None:
    run_alembic_upgrade(DATABASE_URL, os.path.join(os.path.dirname(__file__), "alembic.ini"), app.logger)
    app.register_blueprint(create_manifest_blueprint(_MANIFEST))
    app.register_blueprint(create_aneca_blueprint(SqlJournalQuartileGateway(_db), SqlArticleRepository(_db)))


if __name__ == "__main__":
    _bootstrap()
    app.run(host="0.0.0.0", port=5001)

_bootstrap()
