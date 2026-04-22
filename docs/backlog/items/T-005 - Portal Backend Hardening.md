---
id: T-005
title: Portal Backend Hardening
audience: [human, ai]
last_updated: 2026-04-22
tags: [backlog, backend, security, observability, performance, technical]
source_of_truth: true
related: [T-002, T-003]
---

# T-005 - Portal Backend Hardening

## Purpose
Close operational, security, and data-integrity gaps discovered during a backend audit of `apps/portal/backend/`. These are pre-production blockers that don't belong to T-002 (DX/tooling) or T-003 (migrations).

## When to use
Tackle these before the first production deployment. Items are grouped by severity; pick off Critical first.

## Content

### 🏗 Context & Motivation
The backend has clean architecture (domain/ports/adapters) and sound business logic, but several operational and security gaps would cause silent failures, hard-to-diagnose incidents, or exploitable vectors in production.

### 🗺 Scope & Impact
- **File**: `apps/portal/backend/`  
- **Layers touched**: adapters/sql, adapters/routes, alembic/versions, app.py

---

### ✅ Acceptance Criteria

#### 🔴 Critical — fix before any deployment

- [x] **`import time` missing in `plugin_repo.py`** (`adapters/sql/plugin_repo.py:1`).  
  `install()` raises `NameError` at runtime whenever a plugin is installed via the API.  
  *Fixed in commit that created this backlog item.*

- [x] **`/health` endpoint** — returns `{"status": "ok"}` with a lightweight DB ping.  
  Required for Docker `HEALTHCHECK`, Caddy upstream probing, and nginx `upstream` resolution (nginx currently exits if portal-backend isn't up at start time).
  *Added to `app.py`, nginx proxies `GET /health`, `HEALTHCHECK` in `Dockerfile` and `docker-compose.yml`.*

- [x] **Database indexes** — add a migration with indexes on the hot-path columns:
  - `plugin_installs(tenant_id, status)`
  - `tenant_memberships(user_id)`
  - `audit_logs(user_id, created_at)`
  - `users(email)` — used by `find_user_by_email`
  *Migration `c4d5e6f7a8b9_add_hot_path_indexes.py` applied.*

#### 🟠 High — fix before soft launch

- [x] **Rate limiting on auth endpoints** — add Flask-Limiter (or nginx `limit_req`) for `/auth/login` and `/auth/callback` (5 req/min per IP). Without this, the IDP token exchange becomes a free amplification target.
  *Flask-Limiter 3.8 added; `@limiter.limit("5 per minute")` on `/auth/login` and `/auth/callback`. In-memory storage with 1 gunicorn worker. Switch to Redis + multiple workers for production scale.*

- [x] **Enforce session secret** — `app.secret_key` falls back to `"dev-portal-secret-change-me"` (`app.py:35`). Make the app fail hard at startup if `PORTAL_SESSION_SECRET` is not set in production.
  *App exits with fatal error at startup if `PORTAL_SESSION_SECRET` is unset and `FLASK_ENV=production` or `ENFORCE_SESSION_SECRET` is set.*

- [x] **URL validation on `app_url`** in `_validate_manifest()` — reject non-http/https schemes and RFC-1918 addresses to close the SSRF surface in `_available()`.
  *`_is_safe_app_url()` added; rejects non-http(s) schemes and RFC-1918/loopback addresses.*

- [x] **`allowed_apps` enforcement** — `tenants.allowed_apps` is stored but never filtered in `_available()` or the catalog query. A tenant can access any app regardless of this setting.
  *`_available()` now reads `tenants.allowed_apps` and filters the result set.*

#### 🟡 Medium — next sprint

- [ ] **Structured logging** — replace bare `app.logger.warning()` calls with JSON-structured log entries including `request_id`, `user_id`, `tenant_id`, and exception tracebacks. The SDK's `setup_logging()` sets up the handler but the call sites still pass unstructured strings.

- [ ] **Remove or implement dead schema** — `user_roles` / `roles` tables and `app_permissions` table are created in the initial migration but never queried. Either implement them or drop them in a migration to reduce confusion.

- [x] **`_available()` executor cap** — `ThreadPoolExecutor()` with no `max_workers` can spawn up to 36 threads for large installs. Cap at 8 and add a per-app timeout log when `_is_reachable` returns False.
  *`max_workers=8` set; debug log added on unreachable app.*

### 🛠 Technical Constraints & References
- Health endpoint must respond before gunicorn workers fork (add to `app.py` as a plain route, not behind `@require_session`).
- Index migration revision must chain from the last portal migration (`b3c4d5e6f7a8`).
- Flask-Limiter requires Redis or a memory backend; start with in-memory for simplicity.

---

### 🚦 Status
- **Current Status**: `Active`
- **Priority**: `High`
- **Assignee**: —

## References
- `apps/portal/backend/app.py`
- `apps/portal/backend/adapters/sql/plugin_repo.py`
- `apps/portal/backend/adapters/sql/tenant_repo.py`

## Change log
- **2026-04-22**: All Critical and most High items done. Rate limiting is the only remaining High item. Medium items carried to next sprint.
- **2026-04-21**: Created from backend audit. `import time` bug fixed immediately.
