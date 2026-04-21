import os
import alembic.config
import alembic.command

from flask import Flask
from flask_cors import CORS
from apps_platform_sdk.observability import setup_logging
from apps_platform_sdk import register_error_handlers

import config
from services import template_service, job_service
from services.job_store import JobStore
from services import batch_service

app = Flask(__name__, template_folder=os.path.join(config.BASE_DIR, "templates"))
setup_logging(app)
register_error_handlers(app)
CORS(app, resources={r"/exam-corrector/*": {"origins": config.ALLOWED_ORIGINS}})

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.TEMPLATE_STORE_DIR, exist_ok=True)


def _run_alembic_upgrade() -> None:
    """Run alembic upgrade head to ensure the database schema is up-to-date."""
    if not config.DATABASE_URL:
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


_run_alembic_upgrade()

store = JobStore(config.DATABASE_URL)
job_service.init(store)
template_service.cargar_bbox_cache()

from routes import correction, legacy, templates, rules, manifest, batch, settings
app.register_blueprint(correction.bp)
app.register_blueprint(legacy.bp)
app.register_blueprint(templates.bp)
app.register_blueprint(rules.bp)
app.register_blueprint(manifest.bp)
app.register_blueprint(batch.bp)
app.register_blueprint(settings.bp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

