---
id: T-004
title: Distributed Manifest Discovery
audience: [human, ai]
last_updated: 2026-04-21
tags: [backlog, discovery, architecture, dx, architecture]
source_of_truth: true
related: [DOC-CON-001, DOC-APP-POR-001]
---

# T-004 - Distributed Manifest Discovery

## Purpose
Decouple the Portal Catalog from individual apps by allowing each app to own its manifest, which is then aggregated at build/runtime.

## When to use
This task improves developer experience (DX) and reduces architectural coupling. It should be prioritized before scaling the platform to a larger number of independent apps.

## Content

### 🏗 Context & Motivation
Currently, all apps must be manually added to the `static_apps.json` file in the `portal-backend`. This creates a bottleneck and violates the "Independent Apps" principle. Each app should own its metadata.

### 🗺 Scope & Impact
- **Monorepo Structure**: Every app directory will contain a `manifest.json`.
- **Portal Backend**: Update the catalog loading logic to either:
    1. Scan the filesystem for `apps/*/manifest.json` (Runtime discovery).
    2. Consume an aggregated file generated at build time (Build-time discovery).
- **SDK**: Provide utilities for apps to serve their own manifest at `/manifest` automatically.

### ✅ Acceptance Criteria
- [x] `static_apps.json` removed from `portal-backend`.
- [x] `manifest.json` exists in each app's root directory (`exam-corrector`, `aneca-advisor`, `attendance-checker`).
- [x] Portal aggregates manifests via `_discover_apps()`, scanning `APPS_DIR/*/manifest.json` at startup.
- [x] New apps are discovered without modifying portal code — add `manifest.json` to app root + one `COPY` line in the portal Dockerfile.

### 🛠 Technical Constraints & References
- **Nx Integration**: Use `nx list` or project tags to identify "discoverable" apps.
- **Build Time**: Prefer build-time aggregation to ensure fast Portal startup.

---

### 🚦 Status
- **Current Status**: `Done`
- **Priority**: `High`
- **Assignee**: Unassigned

## References
- [System Architecture](../concepts/architecture.md)
- [Portal Deep Dive](../../apps/portal/index.md)

## Change log
- **2026-04-22**: Implemented. manifest.json in each app root; portal uses _discover_apps() scanning APPS_DIR/*/manifest.json; static_apps.json deleted; Dockerfile updated.
- **2026-04-22**: Elevated to High — prerequisite for T-013 (scaffolding) and removes the static_apps.json bottleneck.
- **2026-04-21**: Created to improve architectural decoupling and developer ergonomics.
