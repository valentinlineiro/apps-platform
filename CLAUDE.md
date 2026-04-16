# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```bash
docker compose up --build
```

- Portal (Angular PWA): `https://localhost`
- Keycloak (auth): `https://localhost/admin` (admin/admin in dev)
- Portal backend API: internal only (proxied via Caddy+nginx at `/api/` and `/auth/`)
- exam-corrector backend: internal only (proxied at `/exam-corrector/` and `/apps/exam-corrector/`)

## Architecture

Multi-app monorepo. Each app lives under `apps/<id>/`.

```
apps/
  portal/
    backend/                  # Flask — registry API + OAuth/OIDC auth + Postgres
    (Angular 21 PWA source)   # directory shell, routing, nginx
  exam-corrector/
    backend/                  # Flask + OpenCV/OMR pipeline (no external API calls)
    frontend/                 # Angular components for this app
  attendance-checker/
    frontend/                 # Angular components (no backend yet)
libs/
  platform-python-sdk/        # Shared Python SDK used by all backends
    platform_sdk/
      observability.py        # JSON structured logging (setup_logging, log_exception)
```

### Infrastructure

Traffic flows: **Browser → Caddy (TLS) → portal nginx → backends**.

- **Caddy** (`caddy:2.7-alpine`) terminates TLS for `localhost`, routes via static `Caddyfile`:
  - `/realms/*`, `/admin/*`, `/resources/*`, `/js/*`, `/welcome/*` → `keycloak:8080`
  - Everything else → `portal:80`
- **portal nginx** (`apps/portal/nginx.conf`) routes internally:
  - `/api/*`, `/auth/*` → `portal-backend:5000`
  - `/exam-corrector/*`, `/apps/exam-corrector/*` → `exam-corrector-backend:8000` (auth-gated)
  - `/_auth` (internal) — subrequest to `portal-backend/auth/me`; has `client_max_body_size 0` so large uploads don't cause 413 inside `auth_request`
- **Keycloak** v26.2.2, backed by Postgres, `KC_PROXY=edge`. Realm imported from `apps/portal/backend/keycloak/apps-platform-realm.json` on first boot only (`--import-realm` skips existing realms).

> **Keycloak gotcha**: if the `postgres_data` volume predates a change to the realm JSON, the old config (e.g. stale redirect URIs) remains in the DB. Fix by updating via the admin UI or running `docker compose down -v && docker compose up --build`.

### Shared SDK (`libs/platform-python-sdk/`)

Mounted as a volume into both Flask containers and installed with `python setup.py develop` at startup, so edits to the SDK are picked up without rebuilding.

Key functions:
- `platform_sdk.start_registration(manifest)` — registers the app with the portal backend and starts the heartbeat loop
- `platform_sdk.observability.setup_logging(app)` — attaches JSON structured logging to a Flask app (before/after request hooks, `request_id`, timing)
- `platform_sdk.observability.log_exception(message)` — logs an exception with full traceback from within a request context

### App registration (heartbeat model)

Apps self-register at startup via `start_registration(manifest)` from the SDK, which calls `POST /api/registry/register` and then heartbeats every 30 s. The portal evicts apps missing heartbeats (default TTL: 60 s).

Adding a new app requires:
1. In the app's backend: call `start_registration(manifest)` (see `apps/exam-corrector/backend/app/__init__.py`)
2. In the portal frontend: add a lazy route to `apps/portal/src/app/app.routes.ts`
3. Add proxy blocks to `apps/portal/nginx.conf` for the new app paths
4. Add an entry to `apps/portal/proxy.conf.json` (dev proxy)
5. Add the backend service to `docker-compose.yml` with `PORTAL_BACKEND_URL=http://portal-backend:5000`

**Manifest v1 schema** — all string fields must be non-empty; `route` must not be empty:
```json
{
  "manifestVersion": 1,
  "id": "my-app",
  "name": "My App",
  "description": "...",
  "route": "my-app",
  "icon": "🔧",
  "status": "stable | wip | disabled",
  "backend": { "pathPrefix": "/my-app/" },
  "scriptUrl": "/apps/my-app/element/main.js",
  "elementTag": "my-app-app"
}
```

### Portal backend (`apps/portal/backend/`)
Flask app backed by **Postgres** in Docker (`DATABASE_URL`), SQLite fallback locally.

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
python -m pytest tests/
```

### Portal (`apps/portal/`)
Angular 21 PWA (standalone components, signals, zoneless change detection).

**Key files:**
- `src/app/app.routes.ts` — lazy routes; one `loadComponent` entry per app
- `src/app/services/app-registry.service.ts` — fetches `/api/registry`, drives the directory
- `src/app/pages/directory-page.component.ts` — renders app cards from registry
- `nginx.conf` — reverse proxy for portal backend and each app backend
- `proxy.conf.json` — dev proxy; maps `/api/`, `/auth/`, `/exam-corrector/` → local backends

**Portal dev (without Docker):**
```bash
# From repo root (installs into root node_modules/ — required for cross-app imports)
npm install
cd apps/portal && npm start   # serves on :4200, proxies backend routes
```

### exam-corrector backend (`apps/exam-corrector/backend/`)
Flask + pure CV/OMR pipeline (OpenCV only, no external API calls). Self-registers with portal backend on startup.

**Key flows:**
- **Async correction**: `POST /exam-corrector/start` → `job_id` → poll `GET /exam-corrector/status/<job_id>` → `GET /exam-corrector/api/result/<job_id>`
- **Batch correction**: `POST /exam-corrector/batch/start` (ZIP or PDF of images) → `batch_id` → poll `GET /exam-corrector/batch/status/<batch_id>` → `GET /exam-corrector/batch/items/<batch_id>` / `GET /exam-corrector/batch/result/<batch_id>` (CSV)
- **Sync correction** (legacy HTML): `POST /exam-corrector/corregir` → renders `resultado.html`
- **Template library**: stored in `uploads/templates/`, indexed in `uploads/saved_templates.json`
- **Template bbox cache**: CV-detected answer grid cached by SHA-256 in `uploads/template_bbox_cache.json`
- **Scoring rules**: `uploads/scoring_rules.json`, editable at `/exam-corrector/rules`

**Correction pipeline** (in `app/services/`):
1. `image_service.load_and_crop` — OpenCV perspective-corrects the exam sheet to a 900×1100 canvas
2. `image_service.detectar_bboxes_cv` — detects answer grid via contour analysis and 1D clustering (cached)
3. `image_service.corregir_con_omr` — ECC fine-alignment + per-option ink classifier (blank/selected/cancelled/uncertain); applies Rules 1–6 including rectification (Rule 6)
4. `scoring_service` — applies scoring rules → returns result dict

Jobs and batches persist in `uploads/jobs.db` (SQLite). Batch items process concurrently via `ThreadPoolExecutor` (up to 8 parallel OMR corrections; CPU-only, no rate limits).

### exam-corrector frontend (`apps/exam-corrector/frontend/`)
- `exam-corrector-page.component.ts` — main UI: template selection, file upload, async polling, batch mode
- `services/exam-corrector-api.service.ts` — HTTP calls; uses same-origin paths (nginx proxies in prod, proxy.conf.json in dev)

## Angular component conventions

All Angular components use **separate files** for template and styles — never inline `template` or `styles` in the `@Component` decorator:

```typescript
@Component({
  selector: 'app-my-component',
  templateUrl: './my-component.component.html',   // ✅
  styleUrl: './my-component.component.css',        // ✅
  // NOT: template: `...`, styles: [`...`]          // ❌
})
```

Each component lives alongside its `.html` and `.css` files in the same directory.

## Environment

**Portal backend:**
- `PORTAL_SESSION_SECRET` — Flask session secret (default: `dev-portal-secret-change-me`)
- `SESSION_COOKIE_SECURE` — set `true` in production (HTTPS); default `true` in Docker
- `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` — OIDC client credentials
- `OAUTH_AUTHORIZE_URL`, `OAUTH_TOKEN_URL`, `OAUTH_USERINFO_URL` — OIDC endpoints
- `OAUTH_REDIRECT_URI` — callback URL (default in Docker: `https://localhost/auth/callback`)
- `OAUTH_PROVIDER` — provider name stored on users (default: `oidc`; set to `keycloak` in Docker)
- `OAUTH_VERIFY_SSL` — set `false` in Docker (self-signed cert from Caddy)
- `DATABASE_URL` — Postgres connection string; falls back to SQLite if unset
- `HEARTBEAT_TTL` — seconds before an app is considered stale (default: `60`)

**exam-corrector backend:**
- `PORTAL_BACKEND_URL` — where to register/heartbeat (default: `http://portal-backend:5000`)
- `ALLOWED_ORIGINS` — CORS origins (default: `http://localhost:4200`)
- `UPLOAD_MAX_AGE_SECONDS` — age before temp upload files are purged (default: `86400`)
- Backend uploads persisted via `exam_corrector_uploads` Docker volume


<!-- nx configuration start-->
<!-- Leave the start & end comments to automatically receive updates. -->

## General Guidelines for working with Nx

- For navigating/exploring the workspace, invoke the `nx-workspace` skill first - it has patterns for querying projects, targets, and dependencies
- When running tasks (for example build, lint, test, e2e, etc.), always prefer running the task through `nx` (i.e. `nx run`, `nx run-many`, `nx affected`) instead of using the underlying tooling directly
- Prefix nx commands with the workspace's package manager (e.g., `pnpm nx build`, `npm exec nx test`) - avoids using globally installed CLI
- You have access to the Nx MCP server and its tools, use them to help the user
- For Nx plugin best practices, check `node_modules/@nx/<plugin>/PLUGIN.md`. Not all plugins have this file - proceed without it if unavailable.
- NEVER guess CLI flags - always check nx_docs or `--help` first when unsure

## Scaffolding & Generators

- For scaffolding tasks (creating apps, libs, project structure, setup), ALWAYS invoke the `nx-generate` skill FIRST before exploring or calling MCP tools

## When to use nx_docs

- USE for: advanced config options, unfamiliar flags, migration guides, plugin configuration, edge cases
- DON'T USE for: basic generator syntax (`nx g @nx/react:app`), standard commands, things you already know
- The `nx-generate` skill handles generator discovery internally - don't call nx_docs just to look up generator syntax


<!-- nx configuration end-->