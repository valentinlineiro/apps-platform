import os

from flask import Flask
from flask_cors import CORS

from app import config
from app.services import template_service
from app.services.job_store import JobStore
from app.services import job_service


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
    )

    CORS(app, resources={r"/exam-corrector/*": {"origins": config.ALLOWED_ORIGINS}})

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.TEMPLATE_STORE_DIR, exist_ok=True)

    store = JobStore(config.JOBS_DB_PATH)
    job_service.init(store)

    template_service.cargar_template_cache()

    from app.routes import correction, legacy, templates, rules, manifest
    app.register_blueprint(correction.bp)
    app.register_blueprint(legacy.bp)
    app.register_blueprint(templates.bp)
    app.register_blueprint(rules.bp)
    app.register_blueprint(manifest.bp)

    from app.services import registration_service
    registration_service.start()

    return app
