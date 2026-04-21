import os

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

store = JobStore(config.JOBS_DB_PATH)
job_service.init(store)
batch_service.init_tables()
template_service.cargar_bbox_cache()

from routes import correction, legacy, templates, rules, manifest, batch, settings
app.register_blueprint(correction.bp)
app.register_blueprint(legacy.bp)
app.register_blueprint(templates.bp)
app.register_blueprint(rules.bp)
app.register_blueprint(manifest.bp)
app.register_blueprint(batch.bp)
app.register_blueprint(settings.bp)

