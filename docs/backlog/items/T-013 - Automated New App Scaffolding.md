---
id: T-013
title: Automated New App Scaffolding
audience: [human, ai]
last_updated: 2026-04-22
tags: [dx, scaffolding, nx, generators]
source_of_truth: true
related: [DOC-TMP-AI-001, T-008, T-009]
---

# Automated New App Scaffolding

## Purpose
Accelerate the development lifecycle and ensure architectural compliance by providing an automated way to scaffold new micro-frontend applications and their backends.

## Context & Motivation
Currently, creating a new "app" in the platform involves several manual steps: creating directories, copying boilerplate Flask code, setting up `project.json` for Nx, and registering the app in the Portal. This is error-prone and slow. By creating an **Nx Generator**, we can automate this process, ensuring that every new app starts with the Platform SDK, Clean Architecture folders, and MFE-loader integration pre-configured.

## Scope & Impact
- **Workspace Tooling**: Create a custom Nx plugin with generators for "Platform App".
- **Templates**: Define standard templates for Backend (Python/Flask) and Frontend (Angular/MFE).
- **Impact**: Reduces "Time to First Logic" for developers and guarantees adherence to platform standards (T-008, T-009).

## Acceptance Criteria
- [ ] **Nx Generator**: Create a command `npx nx generate @apps-platform/plugin:app --name=my-new-app`.
- [ ] **Backend Template**: Scaffolding must include a Clean Architecture folder structure, `app.py` with SDK initialization, and a basic Alembic setup.
- [ ] **Frontend Template**: Scaffolding must include an Angular component configured as a Web Component (MFE) and the necessary build configuration.
- [ ] **Auto-Registration**: The generator should optionally add a draft entry to the Portal's `static_apps.json` or catalog.
- [ ] **CI Integration**: Ensure the new app is automatically picked up by the workspace-wide CI/CD pipelines.

## Technical Constraints & References
- **Standardization**: Templates must use the latest SDK patterns (T-008).
- **Flexibility**: Allow developers to choose between "Full-stack" and "Frontend-only" scaffolding.
- **Maintainability**: The generator itself must be tested using standard Nx plugin testing utilities.

## Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [Nx Generators Documentation](https://nx.dev/recipes/extending-nx/create-plugins)
- [Consolidate App Logic (T-008)](T-008%20-%20Consolidate%20Common%20App%20Logic%20into%20Platform%20SDK.md)

## Change log
- **2026-04-22**: Initial task creation.
