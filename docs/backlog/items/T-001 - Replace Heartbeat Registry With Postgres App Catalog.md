---
id: T-001
title: Replace Heartbeat Registry With Postgres App Catalog
audience: [human, ai]
last_updated: 2026-04-20
tags: [backlog, technical, architecture, postgres, registry, catalog]
source_of_truth: true
related: [DOC-CON-001, DOC-HT-001]
---

# T-001 - Replace Heartbeat Registry With Postgres App Catalog

## Purpose
Replace the current SQLite-backed, heartbeat-driven app registry with a Postgres-backed app catalog owned by `portal`, using pull-based manifest and health reconciliation instead of app self-registration.

## When to use
Consult this task when refactoring app discovery, backend startup flows, or the shared Python SDK registration model.

## Content

### 🏗 Context & Motivation
The current app registration flow mixes runtime discovery, heartbeat liveness, and catalog persistence:

- `portal-backend` stores registry state in a database table that still supports SQLite fallback.
- app backends call `start_registration(manifest)` on startup and send periodic heartbeats.
- multi-worker startup creates duplicated registration traffic and can trigger fragile boot behavior.

This is the wrong tradeoff for a controlled Nx monorepo where the set of apps is known. App registration should be declarative, owned by `portal`, and persisted in Postgres. Runtime liveness should be derived from explicit health/manifest checks, not from background heartbeat threads inside every app process.

### 🗺 Scope & Impact
- **Portal Backend**: `apps/portal/backend/app.py`, plus supporting repository and route modules.
- **App Backends**: `apps/exam-corrector/backend/app.py`, `apps/aneca-advisor/backend/app.py`, and future app backends.
- **Shared Libs**: `libs/apps-platform-sdk/apps_platform_sdk/registration.py` and package exports.
- **Docs**: architecture, coding standards, and app creation guidance.
- **Infra**: Docker and environment configuration for Postgres-backed catalog storage and optional reconciliation jobs.

### ✅ Acceptance Criteria
- [ ] `portal-backend` no longer uses SQLite fallback for app registry/catalog persistence.
- [ ] App catalog state is persisted in Postgres and modeled as portal-owned metadata, not heartbeat state.
- [ ] Each backend app exposes a manifest endpoint or equivalent portal-readable manifest source.
- [ ] `portal-backend` can reconcile app metadata and runtime availability without app-side heartbeat threads.
- [ ] `start_registration()` is removed from app startup code and deprecated or deleted from `apps-platform-sdk`.
- [ ] `GET /api/registry` or its replacement continues to return the effective installed-and-available app list for a tenant.
- [ ] Existing install/catalog behavior for plugins/apps is preserved or explicitly migrated without regression.
- [ ] Tests cover manifest reconciliation, unavailable app handling, and catalog reads after migration.

### 🛠 Technical Constraints & References
- **Persistence**: Use Postgres as the source of truth for portal-owned catalog data.
- **Compatibility**: Preserve the current manifest contract (`manifestVersion`, route, icon, backend path, script URL) unless a versioned migration is explicitly introduced.
- **Ownership**: `portal` owns app discovery and availability status; app backends must not maintain background registration loops.
- **Resilience**: App unavailability must degrade catalog visibility cleanly without crashing the portal.
- **Migration**: Prefer a phased migration that keeps the current UI contract stable while replacing the backend registration model underneath.
- **Reference Docs**:
  - [System Architecture](../../concepts/architecture.md)
  - [Coding Standards & Conventions](../../how-to/coding-standards.md)
  - [Portal Deep Dive](../../apps/portal/index.md)

### Implementation Plan
1. **Phase 1: Make Postgres mandatory for the portal catalog**
   - Remove SQLite fallback from portal registry/catalog persistence paths.
   - Isolate app catalog queries and writes behind a repository boundary if needed.
   - Add or normalize schema for portal-owned app records and availability state.

2. **Phase 2: Introduce pull-based app discovery**
   - Define a standard manifest endpoint or manifest fetch contract for backend apps.
   - Add portal reconciliation logic that fetches manifests and records app health/availability.
   - Keep the frontend-facing registry response stable during the transition.

3. **Phase 3: Remove app self-registration**
   - Remove `start_registration()` usage from app boot code.
   - Delete heartbeat endpoints or mark them deprecated, then remove them once unused.
   - Remove registration helpers from `apps-platform-sdk` if no longer needed.

4. **Phase 4: Clean up docs and tests**
   - Update app creation guidance to use declarative catalog registration.
   - Add regression coverage for portal catalog reads, tenant installs, and unavailable apps.
   - Remove stale heartbeat/registry language from docs and code comments.

### 🚦 Status
- **Current Status**: `Planned`
- **Priority**: `High`
- **Assignee**: Unassigned

## References
- [System Architecture](../../concepts/architecture.md)
- [Project Backlog Index](../index.md)

## Change log
- **2026-04-20**: Created initial migration plan for replacing the heartbeat registry with a Postgres-backed app catalog.
