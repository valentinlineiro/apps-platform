---
id: DOC-CON-001
title: System Architecture
audience: [human, ai]
last_updated: 2026-04-17
tags: [architecture, registry, portal, heartbeat]
source_of_truth: true
related: [DOC-CON-002, DOC-QS-001]
---

# System Architecture

## Purpose
This document defines the high-level architectural patterns of the platform, specifically the "Heartbeat Registry" model for dynamic micro-frontend composition.

## When to use
Consult this document when adding new applications, debugging service discovery, or understanding the end-to-end traffic flow.

## Content

### Overview
The project is a monorepo-style platform orchestrator for a suite of integrated applications (**Portal**, **Exam Corrector**, **Attendance Checker**).

### Architecture Model: "Heartbeat Registry"
The platform uses a dynamic service discovery and frontend composition model.

#### 1. Traffic Flow
**Browser** → **Caddy** (TLS termination for `localhost`) → **Portal Nginx** → **App Backends** (Proxied and Auth-gated).

#### 2. Service Discovery (Heartbeat Loop)
- **App Backends** register themselves with the `portal-backend` at startup (`POST /api/registry/register`).
- Apps send a **heartbeat** every 30 seconds (`POST /api/registry/heartbeat/<app_id>`).
- The `portal-backend` evicts apps missing heartbeats (default TTL: 60s).
- **Portal Frontend** fetches the active registry and dynamically loads apps as Web Components via `MicroFrontendLoaderComponent`.

### Directory Structure
```text
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
      observability.py        # JSON structured logging
      registration.py         # Heartbeat registration logic
```

### Key Components
- **`apps/portal/`**: Central hub. Angular 21 shell and Flask registry/auth API.
- **`apps/exam-corrector/`**: AI-powered OMR (Optical Mark Recognition).
- **`apps/attendance-checker/`**: Attendance tracking (WIP).
- **`libs/platform-python-sdk/`**: Shared logic for registration and observability.

## References
- [Infrastructure Overview](infrastructure.md)
- [Portal Deep Dive](../apps/portal/index.md)

## Change log
- **2026-04-17**: Initial version moved to `concepts/` and standardized.
