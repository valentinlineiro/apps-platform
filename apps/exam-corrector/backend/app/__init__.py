import os

from flask import Flask
from flask_cors import CORS

from app import config
from app.services import template_service
from app.services.job_store import JobStore
from app.services import job_service
from platform_sdk.observability import setup_logging


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
    )
    setup_logging(app)

    CORS(app, resources={r"/exam-corrector/*": {"origins": config.ALLOWED_ORIGINS}})

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.TEMPLATE_STORE_DIR, exist_ok=True)

    store = JobStore(config.JOBS_DB_PATH)
    job_service.init(store)

    from app.services import batch_service
    batch_service.init_tables()

    template_service.cargar_template_cache()

    from app.routes import correction, legacy, templates, rules, manifest, batch, settings
    app.register_blueprint(correction.bp)
    app.register_blueprint(legacy.bp)
    app.register_blueprint(templates.bp)
    app.register_blueprint(rules.bp)
    app.register_blueprint(manifest.bp)
    app.register_blueprint(batch.bp)
    app.register_blueprint(settings.bp)

    from platform_sdk import start_registration
    start_registration({
        "manifestVersion": 1,
        "id": "exam-corrector",
        "name": "exam-corrector",
        "description": "Corrección automática de exámenes con Gemini Vision",
        "route": "exam-corrector",
        "icon": "📝",
        "status": "stable",
        "scriptUrl": "/apps/exam-corrector/element/main.js",
        "elementTag": "exam-corrector-app",
        "backend": {"pathPrefix": "/exam-corrector/"}
    })

    return app
