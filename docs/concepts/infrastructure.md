---
id: DOC-CON-002
title: Infrastructure & Networking
audience: [human, ai]
last_updated: 2026-04-17
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
- **App Backends**: Individual Flask services.

### Traffic Routing

#### Caddy Ingress (`Caddyfile`)
- `/realms/*`, `/admin/*`, `/resources/*`, `/js/*`, `/welcome/*` → `keycloak:8080`
- Everything else → `portal:80`

#### Portal Nginx (`apps/portal/nginx.conf`)
The portal Nginx acts as an internal reverse proxy:
- `/api/*`, `/auth/*` → `portal-backend:5000`
- `/exam-corrector/*`, `/apps/exam-corrector/*` → `exam-corrector-backend:8000` (auth-gated)
- `/_auth` (internal) — subrequest to `portal-backend/auth/me`.

### Auth & Security
- **Provider**: Keycloak (OIDC/OAuth2 with PKCE).
- **Subrequest Authentication**: Internal routes are gated by Nginx `auth_request` subrequests to the portal's `/auth/me` endpoint.
- **Roles**: `owner`, `admin`, `member` (default), `viewer`.

## References
- [System Architecture](architecture.md)
- [Environment Variables](../reference/environment-variables.md)

## Change log
- **2026-04-17**: Moved to `concepts/` and standardized.
