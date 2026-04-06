#!/usr/bin/env bash
# Transition helper for the parent repo: scaffolds a new app under apps/<app-id>.
# Usage: ./scaffold-app.sh <app-id> "<App Name>" "<Description>" [icon]
# Example: ./scaffold-app.sh attendance-checker "Attendance Checker" "Track student attendance" "📋"
set -euo pipefail

# ── Args ──────────────────────────────────────────────────────────────────────
APP_ID="${1:-}"
APP_NAME="${2:-}"
APP_DESC="${3:-}"
APP_ICON="${4:-🔧}"

if [[ -z "$APP_ID" || -z "$APP_NAME" || -z "$APP_DESC" ]]; then
  echo "Usage: $0 <app-id> \"<App Name>\" \"<Description>\" [icon]"
  exit 1
fi
if [[ ! "$APP_ID" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Error: app-id must be lowercase kebab-case (e.g. my-app)"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$ROOT_DIR/apps/$APP_ID"

if [[ -d "$APP_DIR" ]]; then
  echo "Error: apps/$APP_ID already exists."
  exit 1
fi

# ── Naming helpers ─────────────────────────────────────────────────────────────
APP_PASCAL=$(python3 -c "print(''.join(w.capitalize() for w in '${APP_ID}'.split('-')))")
APP_CAMEL=$(python3  -c "s='${APP_PASCAL}'; print(s[0].lower()+s[1:])")
APP_SERVICE="${APP_ID}-backend"
APP_ELEMENT="${APP_ID}-app"
APP_COMPONENT="${APP_CAMEL}PageComponent"

echo "Scaffolding apps/$APP_ID ..."

# ── Directory structure ────────────────────────────────────────────────────────
mkdir -p "$APP_DIR/frontend/src/services"
mkdir -p "$APP_DIR/backend/app/routes"
mkdir -p "$APP_DIR/backend/app/services"

# ══════════════════════════════════════════════════════════════════════════════
# FRONTEND
# ══════════════════════════════════════════════════════════════════════════════

cat > "$APP_DIR/package.json" <<EOF
{
  "name": "${APP_ID}",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "build": "ng build ${APP_ID}-element",
    "build:dev": "ng build ${APP_ID}-element --configuration development"
  },
  "dependencies": {
    "@angular/common": "^21.0.0",
    "@angular/compiler": "^21.0.0",
    "@angular/core": "^21.0.0",
    "@angular/elements": "^21.0.0",
    "@angular/platform-browser": "^21.0.0",
    "rxjs": "^7.8.1",
    "tslib": "^2.8.0"
  },
  "devDependencies": {
    "@angular-devkit/build-angular": "^21.0.0",
    "@angular/cli": "^21.0.0",
    "@angular/compiler-cli": "^21.0.0",
    "typescript": "~5.9.0"
  }
}
EOF

cat > "$APP_DIR/tsconfig.json" <<'EOF'
{
  "compileOnSave": false,
  "compilerOptions": {
    "baseUrl": ".",
    "outDir": "./dist/out-tsc",
    "strict": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "sourceMap": true,
    "declaration": false,
    "downlevelIteration": true,
    "experimentalDecorators": true,
    "moduleResolution": "bundler",
    "importHelpers": true,
    "target": "ES2022",
    "module": "ES2022",
    "useDefineForClassFields": false,
    "lib": ["ES2022", "dom"]
  },
  "angularCompilerOptions": {
    "strictTemplates": true
  }
}
EOF

cat > "$APP_DIR/angular.json" <<EOF
{
  "\$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "projects": {
    "${APP_ID}-element": {
      "projectType": "application",
      "root": ".",
      "sourceRoot": "frontend/src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:application",
          "options": {
            "outputPath": {
              "base": "backend/static/element",
              "browser": ""
            },
            "index": false,
            "browser": "frontend/src/main.element.ts",
            "polyfills": [],
            "tsConfig": "frontend/tsconfig.json",
            "assets": [],
            "styles": [],
            "outputHashing": "none"
          },
          "configurations": {
            "production": {
              "optimization": true
            },
            "development": {
              "optimization": false,
              "sourceMap": true
            }
          },
          "defaultConfiguration": "production"
        }
      }
    }
  }
}
EOF

cat > "$APP_DIR/frontend/package.json" <<'EOF'
{
  "name": "element",
  "private": true
}
EOF

cat > "$APP_DIR/frontend/tsconfig.json" <<'EOF'
{
  "extends": "../tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/element",
    "types": []
  },
  "files": ["src/main.element.ts"],
  "include": ["src/**/*.d.ts"]
}
EOF

cat > "$APP_DIR/frontend/src/main.element.ts" <<EOF
import { provideHttpClient } from '@angular/common/http';
import { provideZonelessChangeDetection } from '@angular/core';
import { createApplication } from '@angular/platform-browser';
import { createCustomElement } from '@angular/elements';
import { ${APP_COMPONENT} } from './${APP_ID}-page.component';

createApplication({
  providers: [provideZonelessChangeDetection(), provideHttpClient()],
}).then(app => {
  customElements.define(
    '${APP_ELEMENT}',
    createCustomElement(${APP_COMPONENT}, { injector: app.injector }),
  );
});
EOF

cat > "$APP_DIR/frontend/src/${APP_ID}-page.component.ts" <<EOF
import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-${APP_ID}-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: \`
    <div style="padding: 24px; font-family: sans-serif;">
      <a href="/" (click)="navigateBack(\$event)" style="text-decoration: none; color: #666;">← Volver</a>
      <h1>${APP_NAME}</h1>
      <p>${APP_DESC}</p>
    </div>
  \`,
})
export class ${APP_COMPONENT} {
  navigateBack(e: Event) {
    e.preventDefault();
    (e.currentTarget as Element).dispatchEvent(
      new CustomEvent('app-navigate', { detail: '/', bubbles: true, composed: true }),
    );
  }
}
EOF

# ══════════════════════════════════════════════════════════════════════════════
# BACKEND
# ══════════════════════════════════════════════════════════════════════════════

cat > "$APP_DIR/backend/requirements.txt" <<'EOF'
flask>=3.0
flask-cors>=4.0
gunicorn>=21.0
requests>=2.31
EOF

cat > "$APP_DIR/backend/wsgi.py" <<'EOF'
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
EOF

cat > "$APP_DIR/backend/app/__init__.py" <<EOF
import os
from flask import Flask
from flask_cors import CORS


def create_app() -> Flask:
    app = Flask(__name__)
    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
    CORS(app, resources={r"/${APP_ID}/*": {"origins": allowed_origins}})

    from app.routes import api, manifest
    app.register_blueprint(api.bp)
    app.register_blueprint(manifest.bp)

    from app.services import registration_service
    registration_service.start()

    return app
EOF

touch "$APP_DIR/backend/app/routes/__init__.py"
touch "$APP_DIR/backend/app/services/__init__.py"

cat > "$APP_DIR/backend/app/routes/api.py" <<EOF
from flask import Blueprint, jsonify

bp = Blueprint("api", __name__, url_prefix="/${APP_ID}/api")


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})
EOF

cat > "$APP_DIR/backend/app/routes/manifest.py" <<EOF
import os
from flask import Blueprint, jsonify, send_from_directory

bp = Blueprint("manifest", __name__)

ELEMENT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "element")


@bp.get("/apps/${APP_ID}/manifest.json")
def manifest():
    return jsonify({
        "id": "${APP_ID}",
        "name": "${APP_NAME}",
        "description": "${APP_DESC}",
        "route": "${APP_ID}",
        "icon": "${APP_ICON}",
        "status": "wip",
        "scriptUrl": "/apps/${APP_ID}/element/main.js",
        "elementTag": "${APP_ELEMENT}",
        "backend": {"pathPrefix": "/${APP_ID}/"},
    })


@bp.get("/apps/${APP_ID}/element/<path:filename>")
def serve_element(filename: str):
    return send_from_directory(os.path.abspath(ELEMENT_DIR), filename)
EOF

cat > "$APP_DIR/backend/app/services/registration_service.py" <<EOF
import os
import threading
import time

import requests

PORTAL_BACKEND_URL = os.environ.get("PORTAL_BACKEND_URL", "http://portal-backend:5000")
HEARTBEAT_INTERVAL = 30
RETRY_INTERVAL = 5

MANIFEST = {
    "id": "${APP_ID}",
    "name": "${APP_NAME}",
    "description": "${APP_DESC}",
    "route": "${APP_ID}",
    "icon": "${APP_ICON}",
    "status": "wip",
    "scriptUrl": "/apps/${APP_ID}/element/main.js",
    "elementTag": "${APP_ELEMENT}",
    "backend": {"pathPrefix": "/${APP_ID}/"},
}


def _try_register() -> bool:
    try:
        r = requests.post(
            f"{PORTAL_BACKEND_URL}/api/registry/register",
            json=MANIFEST,
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _try_heartbeat() -> bool:
    try:
        r = requests.post(
            f"{PORTAL_BACKEND_URL}/api/registry/heartbeat/${APP_ID}",
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


def _loop() -> None:
    while not _try_register():
        time.sleep(RETRY_INTERVAL)
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        if not _try_heartbeat():
            while not _try_register():
                time.sleep(RETRY_INTERVAL)


def start() -> None:
    threading.Thread(target=_loop, daemon=True).start()
EOF

cat > "$APP_DIR/backend/Dockerfile" <<EOF
# Stage 1: Build the Angular web component bundle
FROM node:20-alpine AS element-build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY angular.json tsconfig.json ./
COPY frontend/ frontend/
RUN npx ng build ${APP_ID}-element

# Stage 2: Python backend
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=element-build /app/backend/static/element/ static/element/
EXPOSE 8000
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
EOF

# ══════════════════════════════════════════════════════════════════════════════
# PATCH PORTAL: nginx.conf
# ══════════════════════════════════════════════════════════════════════════════

NGINX_CONF="$ROOT_DIR/apps/portal/nginx.conf"

# Insert upstream block before the server { line
UPSTREAM_BLOCK="upstream ${APP_SERVICE} {\n  server ${APP_SERVICE}:8000;\n}\n"
sed -i "s|^server {|${UPSTREAM_BLOCK}server {|" "$NGINX_CONF"

# Insert two location blocks before the catch-all "location / {"
LOCATION_BLOCKS="  location /apps/${APP_ID}/ {\n    proxy_pass         http://${APP_SERVICE};\n    proxy_set_header   Host \$host;\n  }\n\n  location /${APP_ID}/ {\n    proxy_pass         http://${APP_SERVICE};\n    proxy_set_header   Host \$host;\n    proxy_read_timeout 120s;\n    client_max_body_size 20m;\n  }\n\n"
sed -i "s|  location / {|${LOCATION_BLOCKS}  location / {|" "$NGINX_CONF"

# ══════════════════════════════════════════════════════════════════════════════
# PATCH PORTAL: proxy.conf.json
# ══════════════════════════════════════════════════════════════════════════════

PROXY_CONF="$ROOT_DIR/apps/portal/proxy.conf.json"
python3 - <<PYEOF
import json, pathlib
p = pathlib.Path("$PROXY_CONF")
cfg = json.loads(p.read_text())
cfg["/${APP_ID}/"]      = {"target": "http://localhost:8000", "secure": False}
cfg["/apps/${APP_ID}/"] = {"target": "http://localhost:8000", "secure": False}
p.write_text(json.dumps(cfg, indent=2) + "\n")
PYEOF

# ══════════════════════════════════════════════════════════════════════════════
# PATCH docker-compose.yml
# ══════════════════════════════════════════════════════════════════════════════

COMPOSE="$ROOT_DIR/docker-compose.yml"
SERVICE_BLOCK="  ${APP_SERVICE}:\n    build:\n      context: apps/${APP_ID}\n      dockerfile: backend/Dockerfile\n    expose:\n      - \"8000\"\n    environment:\n      - PORTAL_BACKEND_URL=http://portal-backend:5000\n      - ALLOWED_ORIGINS=http://localhost:4200\n    depends_on:\n      - portal-backend\n    restart: unless-stopped\n\n"
sed -i "s|^volumes:|${SERVICE_BLOCK}volumes:|" "$COMPOSE"

# ══════════════════════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo "✓ apps/${APP_ID}/ created"
echo "✓ nginx.conf patched"
echo "✓ proxy.conf.json patched"
echo "✓ docker-compose.yml patched"
echo ""
echo "Next steps:"
echo "  1. Add the service to the portal's depends_on in docker-compose.yml:"
echo "       depends_on:"
echo "         - portal-backend"
echo "         - exam-corrector-backend"
echo "         - ${APP_SERVICE}   ← add this"
echo ""
echo "  2. docker compose up --build ${APP_SERVICE}"
