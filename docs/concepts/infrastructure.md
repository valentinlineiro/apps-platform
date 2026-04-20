---
id: DOC-CON-002
title: Infrastructure & Networking
audience: [human, ai]
last_updated: 2026-04-20
tags: [infrastructure, docker, caddy, nginx, keycloak, networking]
source_of_truth: true
related: [DOC-CON-001, DOC-REF-ENV-001]
---

# Infrastructure & Networking

## Purpose
This document describes the container orchestration, internal networking, and security layers of the platform.

## When to use
Use this when configuring Docker services, modifying ingress rules in Caddy, or adjusting Nginx proxy settings.

## Content

### Service Composition
The platform relies on Docker Compose for orchestration:
- **Caddy 2.7**: Ingress, TLS termination (`localhost`), and routing.
- **Portal Nginx**: Internal routing, auth-gating, and static frontend hosting.
- **Keycloak 26.2.2**: OIDC/OAuth2 identity provider.
- **PostgreSQL 16**: Persistence for Portal backend and Keycloak.
- **App Backends**: Individual Flask services (`exam-corrector-backend`, `aneca-advisor-backend`).

### Traffic Routing

#### Caddy Ingress (`Caddyfile`)
The `Caddyfile` is **static** — Caddy docker-proxy labels on containers are not used and have no effect.
- `/realms/*`, `/admin/*`, `/resources/*`, `/js/*`, `/welcome/*` → `keycloak:8080`
- Everything else → `portal:80`

#### Portal Nginx (`apps/portal/nginx.conf`)
The portal Nginx acts as an internal reverse proxy and auth gate:
- `/api/aneca/*` → `aneca-advisor-backend:5001`
- `/api/*`, `/auth/*` → `portal-backend:5000`
- `/apps/aneca-advisor/*` → `aneca-advisor-backend:5001` (auth-gated)
- `/apps/exam-corrector/*`, `/exam-corrector/*` → `exam-corrector-backend:8000` (auth-gated)
- `/_auth` (internal) — subrequest to `portal-backend/auth/me`
- `/*` → Angular PWA (`index.html` fallback)

### Docker Build Pipeline
Every app with a frontend uses a **multi-stage Dockerfile**:
- **Stage 1** (`node:20-alpine`): Runs `ng build <element-name>`, emitting `backend/static/element/main.js`.
- **Stage 2** (`python:3.11-slim`): Copies the Python backend and the built JS from Stage 1.

The build context in `docker-compose.yml` is always the **app root** (`./apps/<name>`), not the backend subdirectory, so Stage 1 can access both `frontend/` source and `angular.json`.

Built frontend artifacts are **not committed to git** — the `.gitignore` in each `backend/` directory excludes `static/element/`.

### Auth & Security
- **Provider**: Keycloak (OIDC/OAuth2 with PKCE).
- **Subrequest Authentication**: Internal routes are gated by Nginx `auth_request` subrequests to the portal's `/auth/me` endpoint.
- **Roles**: `owner`, `admin`, `member` (default), `viewer`.

## References
- [System Architecture](architecture.md)
- [Environment Variables](../reference/environment-variables.md)

## Change log
- **2026-04-20**: Add aneca-advisor routing; document static Caddyfile (labels ignored); document multi-stage build pipeline and gitignore policy for artifacts.
- **2026-04-17**: Moved to `concepts/` and standardized.
