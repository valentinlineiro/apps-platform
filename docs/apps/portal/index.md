---
id: DOC-APP-POR-001
title: Portal Application
audience: [human, ai]
last_updated: 2026-04-17
tags: [portal, registry, auth, oidc, flask, angular]
source_of_truth: true
related: [DOC-CON-001, DOC-APP-EXC-001]
---

# Portal Application

## Purpose
The Portal is the central hub for the platform, managing user identity, authentication, and the dynamic registration of micro-frontend applications.

## When to use
Consult this document when modifying the registry logic, updating OIDC authentication flows, or changing how micro-frontends are loaded in the Angular shell.

## Content

### Backend (Flask)
The portal backend is a Flask application backed by **PostgreSQL** in Docker, with an SQLite fallback for local development.

#### Key Endpoints
- `POST /api/registry/register`: Upsert app manifest (no auth required, called by app backends).
- `POST /api/registry/heartbeat/<app_id>`: Keep alive.
- `DELETE /api/registry/<app_id>`: Unregister.
- `GET /api/registry`: List active apps (requires auth session).
- `GET /auth/login`: PKCE OAuth flow entry.
- `GET /auth/me`: Current user info and roles.

#### App Manifest Schema (v1)
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

### Frontend (Angular)
The portal frontend is an Angular 21 PWA that dynamically loads micro-frontends as Web Components.

#### Key Components
- `src/app/app.routes.ts`: Lazy routes for app loaders.
- `src/app/services/app-registry.service.ts`: Drives the platform directory.
- `src/app/pages/directory-page.component.ts`: Renders the available apps.

## References
- [System Architecture](../../concepts/architecture.md)
- [Infrastructure Overview](../../concepts/infrastructure.md)

## Change log
- **2026-04-17**: Moved to `apps/portal/` and standardized.
