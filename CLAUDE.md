# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

Requires a Gemini API key:

```bash
export GEMINI_API_KEY="your_api_key"
docker compose up --build
```

- Portal (Angular PWA): `http://localhost:4200`
- exam-corrector backend: internal only (proxied via nginx)

## Architecture

Multi-app monorepo. Each app lives under `apps/<id>/`.

```
apps/
  portal/                     # Angular 21 PWA shell — directory + routing only
  exam-corrector/
    backend/                  # Flask + Gemini Vision API
    frontend/                 # Angular components for this app
  attendance-checker/
    frontend/                 # Angular components (no backend yet)
```

### App registration

Adding a new app requires three steps:
1. Add the app ID to `apps/portal/public/apps/registry.json`
2. Create `apps/portal/public/apps/<id>/manifest.json` (see existing ones for schema)
3. Add a lazy route to `apps/portal/src/app/app.routes.ts`

The portal's `AppRegistryService` fetches `registry.json` + each manifest at runtime to build the directory page automatically.

### Portal (`apps/portal/`)
Angular 21 PWA (standalone components, signals, zoneless change detection).

**Key files:**
- `src/app/app.routes.ts` — lazy routes; one `loadComponent` entry per app
- `src/app/services/app-registry.service.ts` — fetches manifests, drives the directory
- `src/app/pages/directory-page.component.ts` — renders app cards from registry
- `public/apps/` — `registry.json` + per-app `manifest.json` files (served as static assets)
- `nginx.conf` — one `upstream` + `location` block per app with a backend
- `proxy.conf.json` — dev proxy; maps `/exam-corrector/` → `http://localhost:8000`

**Portal dev (without Docker):**
```bash
# From repo root (installs into root node_modules/ — required for cross-app imports)
npm install
cd apps/portal && npm start   # serves on :4200, proxies backend routes
```

### exam-corrector backend (`apps/exam-corrector/backend/`)
Flask + Gemini Vision API.

**Key flows:**
- **Async correction**: `POST /exam-corrector/start` → `job_id` → poll `GET /exam-corrector/status/<job_id>` → `GET /exam-corrector/api/result/<job_id>`
- **Sync correction** (legacy HTML): `POST /exam-corrector/corregir` → renders `resultado.html`
- **Template library**: stored in `uploads/templates/`, indexed in `uploads/saved_templates.json`
- **Template cache**: Gemini analysis cached by SHA-256 in `uploads/template_cache.json`
- **Scoring rules**: `uploads/scoring_rules.json`, editable at `/exam-corrector/rules`

**Correction pipeline** (`procesar_correccion`):
1. `recorte_a4()` — OpenCV perspective-corrects the exam sheet
2. Gemini analyzes answer key → structured template model (cached)
3. Gemini analyzes student exam + template → per-question results
4. Apply scoring rules → return result dict

Jobs run in daemon threads, tracked in the in-memory `JOBS` dict (lost on restart).

### exam-corrector frontend (`apps/exam-corrector/frontend/`)
- `exam-corrector-page.component.ts` — main UI: template selection, file upload, async polling
- `services/exam-corrector-api.service.ts` — HTTP calls; uses same-origin paths (nginx proxies in prod, proxy.conf.json in dev)

## Environment

- `GEMINI_API_KEY` — required by exam-corrector backend; model hardcoded to `gemini-2.5-flash`
- Backend uploads persisted via `exam_corrector_uploads` Docker volume
