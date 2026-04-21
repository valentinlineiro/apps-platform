---
id: DOC-CON-001
title: System Architecture
audience: [human, ai]
last_updated: 2026-04-20
tags: [architecture, registry, portal, heartbeat, mfe]
source_of_truth: true
related: [DOC-CON-002, DOC-QS-001]
---

# System Architecture

## Purpose
This document defines the high-level architectural patterns of the platform, specifically the "Declarative Catalog" model and shared infrastructure.

## When to use
Consult this document when adding new applications, debugging service discovery, or understanding the end-to-end traffic flow.

## Content

### Overview
The project is a monorepo-style platform orchestrator for a suite of integrated applications (**Portal**, **Exam Corrector**, **ANECA Advisor**, **Attendance Checker**).

### Architecture Model: "Declarative Catalog"
The platform uses a declarative service discovery and frontend composition model.

#### 1. Traffic Flow
**Browser** → **Caddy** (TLS termination for `localhost`) → **Portal Nginx** → **App Backends** (Proxied and Auth-gated).

#### 2. Service Discovery (Declarative)
- **App Metadata**: Each app defines its capabilities and endpoints in a manifest.
- **Static Registry**: The `portal-backend` consumes a central `static_apps.json` catalog to discover and expose applications.
- **Portal Frontend**: Fetches the catalog from the portal API and dynamically loads apps as Web Components via `MicroFrontendLoaderComponent`.

#### 3. Database & Migrations
- **Postgres**: A shared PostgreSQL instance is used as the primary data store.
- **Alembic**: Each backend manages its own schema using Alembic migrations.
- **Automatic Sync**: Migrations are executed automatically by the application on startup (`_bootstrap` sequence), ensuring the schema matches the code in every environment.

#### 4. MFE Loading (`MicroFrontendLoaderComponent`)
Each app's `scriptUrl` is injected into the page as a `type="module"` script tag. Using `type="module"` isolates each Angular runtime in module scope, preventing global variable collisions when multiple MFEs are loaded on the same page. After the script loads, the component waits for `customElements.whenDefined(elementTag)` before mounting the element.

### Directory Structure
```text
apps/
  portal/
    backend/                  # Flask — registry API + OAuth/OIDC auth + Postgres
    src/                      # Angular 21 PWA — shell, routing, MFE loader
    nginx.conf                # Internal reverse proxy and auth-gating
  exam-corrector/
    backend/                  # Flask + OpenCV/OMR pipeline
    frontend/                 # Angular 21 web component
  aneca-advisor/
    backend/                  # Flask — ANECA eligibility API + Postgres
    frontend/                 # Angular 21 web component
  attendance-checker/
    frontend/                 # Angular 21 web component (backend WIP)
libs/
  apps-platform-sdk/          # Shared Python SDK used by all backends
    apps_platform_sdk/
      observability.py        # JSON structured logging
      registration.py         # Heartbeat registration logic
```

### Key Components
- **`apps/portal/`**: Central hub. Angular 21 shell and Flask registry/auth API.
- **`apps/exam-corrector/`**: OMR (Optical Mark Recognition) pipeline using OpenCV.
- **`apps/aneca-advisor/`**: ANECA academic accreditation eligibility simulator.
- **`apps/attendance-checker/`**: Attendance tracking (frontend only, backend WIP).
- **`libs/apps-platform-sdk/`**: Shared logic for registration, observability, auth, and errors.

### Adding a New App
1. Create `apps/<name>/backend/` with a Flask app that calls `apps_platform_sdk.start_registration(manifest)`.
2. Create `apps/<name>/frontend/` with an Angular app that bootstraps via `createApplication()` and calls `customElements.define()`.
3. Add a multi-stage Dockerfile: Stage 1 builds the Angular bundle; Stage 2 is the Python backend.
4. Add the service to `docker-compose.yml` (build context = `./apps/<name>`, no static volume mounts).
5. Add Nginx routes for `/apps/<name>/` and any API paths in `apps/portal/nginx.conf`.

## References
- [Infrastructure Overview](infrastructure.md)
- [Portal Deep Dive](../apps/portal/index.md)

## Change log
- **2026-04-21**: Redesigned as Declarative Catalog model; added Alembic Postgres migration architecture.
- **2026-04-20**: Add aneca-advisor; document MFE module isolation and whenDefined fix; add "Adding a New App" guide; update directory structure.
- **2026-04-17**: Initial version moved to `concepts/` and standardized.
