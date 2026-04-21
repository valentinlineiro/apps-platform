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
- [ ] `static_apps.json` removed from `portal-backend`.
- [ ] `manifest.json` exists in each app's root directory.
- [ ] Portal successfully aggregates all local manifests into its internal catalog.
- [ ] New apps are automatically discovered by the Portal without modifying portal code.

### 🛠 Technical Constraints & References
- **Nx Integration**: Use `nx list` or project tags to identify "discoverable" apps.
- **Build Time**: Prefer build-time aggregation to ensure fast Portal startup.

---

### 🚦 Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: Unassigned

## References
- [System Architecture](../concepts/architecture.md)
- [Portal Deep Dive](../../apps/portal/index.md)

## Change log
- **2026-04-21**: Created to improve architectural decoupling and developer ergonomics.
