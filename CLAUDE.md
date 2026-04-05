# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

Requires a Gemini API key:

```bash
export GEMINI_API_KEY="your_api_key"
docker compose up --build
```

- Frontend Angular PWA: `http://localhost:4200`
- Backend API: `http://localhost:8000`

## Architecture

Two independent apps under `apps/`:

### Backend (`apps/backend/`)
Flask + Gemini Vision API. Single file: `main.py`.

**Key flows:**
- **Async correction** (used by Angular frontend): `POST /exam-corrector/start` → returns `job_id` → poll `GET /exam-corrector/status/<job_id>` → fetch `GET /exam-corrector/api/result/<job_id>`
- **Sync correction** (legacy, used by HTML templates): `POST /exam-corrector/corregir` → renders `resultado.html`
- **Template library**: saved exam templates stored in `uploads/templates/`, indexed in `uploads/saved_templates.json`
- **Template cache**: Gemini analysis of answer keys cached by SHA-256 image hash in `uploads/template_cache.json` to avoid redundant API calls
- **Scoring rules**: configurable via `uploads/scoring_rules.json`, editable at `/exam-corrector/rules`

**Correction pipeline** (`procesar_correccion`):
1. Load images → `recorte_a4()` detects and perspective-corrects the exam sheet via OpenCV
2. Send answer key image to Gemini → extract structured template model (cached)
3. Send student exam image + template model to Gemini → get per-question results
4. Apply scoring rules → return result dict

**Jobs** run in daemon threads, tracked in the in-memory `JOBS` dict (lost on restart).

### Frontend (`apps/frontend/`)
Angular 18 PWA (standalone components, no NgModules). No test suite configured.

**Key files:**
- `src/app/app.routes.ts` — routing: `/` → `DirectoryPageComponent`, `/exam-corrector` → `ExamCorrectorPageComponent`
- `src/app/services/api.service.ts` — all HTTP calls to backend; backend URL resolved from `window.__BACKEND_URL__` or defaults to `http://localhost:8000`
- `src/app/pages/exam-corrector-page.component.ts` — main UI with template selection, file upload, async polling loop

**Frontend dev (without Docker):**
```bash
cd apps/frontend
npm install
npm start   # serves on :4200
```

**Frontend build:**
```bash
cd apps/frontend
npm run build   # output in dist/
```

The Nginx container (`apps/frontend/Dockerfile` + `nginx.conf`) serves the Angular build and proxies `/index.html` for all routes (SPA routing).

## Environment

- `GEMINI_API_KEY` — required by backend; model hardcoded to `gemini-2.5-flash`
- Backend uploads (template images, cache) are persisted via the `backend_uploads` Docker volume
