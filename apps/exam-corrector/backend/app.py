import os

from flask import Flask
from flask_cors import CORS
from apps_platform_sdk import configure_app, run_alembic_upgrade

import config
from services import template_service, job_service
from services.job_store import JobStore
from services import batch_service

app = Flask(__name__, template_folder=os.path.join(config.BASE_DIR, "templates"))
configure_app(app, cors_resources={r"/exam-corrector/*": {"origins": config.ALLOWED_ORIGINS}}, configure_session=False)

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.TEMPLATE_STORE_DIR, exist_ok=True)

run_alembic_upgrade(config.DATABASE_URL, os.path.join(os.path.dirname(__file__), "alembic.ini"), app.logger)

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

