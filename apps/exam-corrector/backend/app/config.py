import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # apps/backend/
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
TEMPLATE_CACHE_PATH = os.path.join(UPLOAD_FOLDER, "template_cache.json")
TEMPLATE_LIBRARY_PATH = os.path.join(UPLOAD_FOLDER, "saved_templates.json")
TEMPLATE_STORE_DIR = os.path.join(UPLOAD_FOLDER, "templates")
SCORING_RULES_PATH = os.path.join(UPLOAD_FOLDER, "scoring_rules.json")
JOBS_DB_PATH = os.path.join(UPLOAD_FOLDER, "jobs.db")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-2.5-flash"

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:4200").split(",")

UPLOAD_MAX_AGE_SECONDS = int(os.environ.get("UPLOAD_MAX_AGE_SECONDS", "86400"))
