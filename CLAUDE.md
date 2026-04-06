# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

Requires a Gemini API key:

```bash
export GEMINI_API_KEY="your_api_key"
docker compose up --build
```

- Portal (Angular PWA): `http://localhost:4200`
- Keycloak (auth): `http://localhost:8081` (admin/admin in dev)
- Portal backend API: internal only (proxied via nginx at `/api/` and `/auth/`)
- exam-corrector backend: internal only (proxied via nginx at `/exam-corrector/`)

## Architecture

Multi-app monorepo. Each app lives under `apps/<id>/`.

```
apps/
  portal/
    backend/                  # Flask — registry API + OAuth/OIDC auth
    (Angular 21 PWA source)   # directory shell, routing, nginx
  exam-corrector/
    backend/                  # Flask + Gemini Vision API
    frontend/                 # Angular components for this app
  attendance-checker/
    frontend/                 # Angular components (no backend yet)
```

### App registration (heartbeat model)

Apps self-register at startup by calling `POST /api/registry/register` on the portal backend, then send `POST /api/registry/heartbeat/<app_id>` every 30 seconds. The portal backend evicts apps that miss heartbeats (default TTL: 60 s). The directory page reflects the live registry.

Adding a new app requires:
1. In the app's backend: implement `registration_service.start()` pattern (see `apps/exam-corrector/backend/app/services/registration_service.py`) and expose `GET /apps/<id>/manifest.json`
2. In the portal frontend: add a lazy route to `apps/portal/src/app/app.routes.ts`
3. Add a `location /apps/<id>/` proxy block to `apps/portal/nginx.conf`
4. Add an entry to `apps/portal/proxy.conf.json` (dev proxy)
5. Add the backend service to `docker-compose.yml` with `PORTAL_BACKEND_URL=http://portal-backend:5000`

**Manifest v1 schema** (all string fields must be non-empty):
```json
{
  "manifestVersion": 1,
  "id": "my-app",
  "name": "My App",
  "description": "...",
  "route": "my-app",
  "icon": "🔧",
  "status": "stable | wip | disabled",
  "backend": { "pathPrefix": "/my-app/" },   // or null
  "scriptUrl": "/apps/my-app/element/main.js",  // required together with elementTag
  "elementTag": "my-app-app"
}
```

### Portal backend (`apps/portal/backend/`)
Flask app backed by SQLite (`REGISTRY_DB_PATH`, default `/tmp/portal_registry.sqlite3`).

**Key endpoints:**
- `POST /api/registry/register` — upsert app manifest (no auth required, called by app backends)
- `POST /api/registry/heartbeat/<app_id>` — keep alive
- `DELETE /api/registry/<app_id>` — unregister
- `GET /api/registry` — list active apps (requires auth session)
- `GET /auth/login` → PKCE OAuth flow → `GET /auth/callback` → sets session cookie
- `GET /auth/me` — current user info + roles
- `GET|POST /auth/logout`

Auth is OIDC/OAuth2 with PKCE. Keycloak is the default provider in Docker. New users get the `member` role automatically; available roles: `owner`, `admin`, `member`, `viewer`.

**Run tests:**
```bash
cd apps/portal/backend
pip install flask flask-cors requests
python -m pytest tests/          # or: python -m unittest discover tests
```

### Portal (`apps/portal/`)
Angular 21 PWA (standalone components, signals, zoneless change detection).

**Key files:**
- `src/app/app.routes.ts` — lazy routes; one `loadComponent` entry per app
- `src/app/services/app-registry.service.ts` — fetches `/api/registry`, drives the directory
- `src/app/pages/directory-page.component.ts` — renders app cards from registry
- `nginx.conf` — reverse proxy for portal backend (`/api/`, `/auth/`) and each app backend
- `proxy.conf.json` — dev proxy; maps `/api/`, `/auth/`, `/exam-corrector/` → local backends

**Portal dev (without Docker):**
```bash
# From repo root (installs into root node_modules/ — required for cross-app imports)
npm install
cd apps/portal && npm start   # serves on :4200, proxies backend routes
```

### exam-corrector backend (`apps/exam-corrector/backend/`)
Flask + Gemini Vision API. Self-registers with portal backend on startup.

**Key flows:**
- **Async correction**: `POST /exam-corrector/start` → `job_id` → poll `GET /exam-corrector/status/<job_id>` → `GET /exam-corrector/api/result/<job_id>`
- **Sync correction** (legacy HTML): `POST /exam-corrector/corregir` → renders `resultado.html`
- **Template library**: stored in `uploads/templates/`, indexed in `uploads/saved_templates.json`
- **Template cache**: Gemini analysis cached by SHA-256 in `uploads/template_cache.json`
- **Scoring rules**: `uploads/scoring_rules.json`, editable at `/exam-corrector/rules`

**Correction pipeline** (in `app/services/`):
1. `image_service.recorte_a4()` — OpenCV perspective-corrects the exam sheet
2. `gemini_service` analyzes answer key → structured template model (cached)
3. `gemini_service` analyzes student exam + template → per-question results
4. `scoring_service` applies rules → return result dict

Jobs run in daemon threads via `job_service`/`job_store` (in-memory, lost on restart).

### exam-corrector frontend (`apps/exam-corrector/frontend/`)
- `exam-corrector-page.component.ts` — main UI: template selection, file upload, async polling
- `services/exam-corrector-api.service.ts` — HTTP calls; uses same-origin paths (nginx proxies in prod, proxy.conf.json in dev)

## Environment

**Portal backend:**
- `PORTAL_SESSION_SECRET` — Flask session secret (default: `dev-portal-secret-change-me`)
- `SESSION_COOKIE_SECURE` — set `true` in production (HTTPS)
- `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` — OIDC client credentials
- `OAUTH_AUTHORIZE_URL`, `OAUTH_TOKEN_URL`, `OAUTH_USERINFO_URL` — OIDC endpoints
- `OAUTH_REDIRECT_URI` — callback URL (default: derived from request)
- `OAUTH_PROVIDER` — provider name stored on users (default: `oidc`; set to `keycloak` in Docker)
- `REGISTRY_DB_PATH` — SQLite path (default: `/tmp/portal_registry.sqlite3`)
- `HEARTBEAT_TTL` — seconds before an app is considered stale (default: `60`)

**exam-corrector backend:**
- `GEMINI_API_KEY` — required; model hardcoded to `gemini-2.5-flash`
- `PORTAL_BACKEND_URL` — where to register/heartbeat (default: `http://portal-backend:5000`)
- Backend uploads persisted via `exam_corrector_uploads` Docker volume
