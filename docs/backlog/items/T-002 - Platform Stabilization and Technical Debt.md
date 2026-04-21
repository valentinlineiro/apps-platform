---
id: DOC-T-002
title: Platform Stabilization and Technical Debt
audience: [human, ai]
last_updated: 2026-04-21
tags: [technical-debt, stabilization, infrastructure, dx]
source_of_truth: true
related: [DOC-CON-001, DOC-HT-001]
---

# T-002 - Platform Stabilization and Technical Debt

## Purpose
Address critical documentation gaps, architectural brittle points, and missing testing infrastructure identified during the platform audit to ensure high reliability and smooth developer onboarding.

## When to use
This task should be prioritized to stabilize the development environment and establish a foundation for CI/CD and long-term maintainability.

## Content

---

### 🏗 Context & Motivation
The platform is architecturally sound but suffers from significant onboarding friction and deployment fragility:
1. **Outdated README**: The root `README.md` still refers to git submodules and provides incorrect ports, leading to confusion for new developers.
2. **Brittle Dependencies**: The use of `-e` relative path installations in `requirements.txt` for the `apps-platform-sdk` is effective for local development but prone to failure in production Docker builds.
3. **Frontend Testing Gap**: No automated testing infrastructure is configured for the Angular 21 applications.
4. **CI/CD Visibility**: There is currently no unified pipeline to validate changes across the monorepo using Nx's `affected` capabilities.

---

### 🗺 Scope & Impact
- **Root Documentation**: `README.md`
- **Backend Infrastructure**: `apps/*/backend/requirements.txt` and `Dockerfile`
- **Frontend Infrastructure**: `apps/*/frontend/...` (Angular workspace)
- **CI/CD**: `.github/workflows/`

---

### ✅ Acceptance Criteria
- [x] Rewrite root `README.md` to accurately document the Nx monorepo structure, current ports, and startup commands.
- [x] Replace `-e` relative path installations in `requirements.txt` with a robust Docker build strategy; fix `deploy.yml` build contexts; add `requirements-dev.txt` per backend for local development.
- [x] Configure `Jest` for automated unit testing of all Angular 21 applications; seed portal service specs.
- [x] Implement a GitHub Actions workflow that executes `nx affected -t lint test build` on every Pull Request; preserve Python backend tests in a separate job.
- [x] Scaffold `libs/apps-platform-ui` shared Angular library in `libs/` with Vitest, ESLint, and path aliases wired into all app tsconfigs.

---

### 🛠 Technical Constraints & References
- **Nx Standards**: Use `nx affected` to keep CI times efficient.
- **Docker**: Maintain multi-stage builds and ensure the build context remains at the root of the repository.
- **Angular**: Follow standalone component and Signal-based testing patterns.
- **Reference Docs**: 
    - [System Architecture](../../concepts/architecture.md)
    - [Coding Standards](../../how-to/coding-standards.md)

---

### 🚦 Status
- **Current Status**: `Done`
- **Priority**: `High`
- **Assignee**: AI Agent / Platform Team

## References
- [Backlog Index](../index.md)
- [Backlog Guidelines](../GUIDELINES.md)

## Change log
- **2026-04-21**: All acceptance criteria completed by Claude Code (Sonnet 4.6). 7 commits: Docker/SDK fix, nx.json, Jest, ESLint, CI pipeline, README rewrite, apps-platform-ui scaffold.
- **2026-04-20**: Created as a result of a comprehensive platform audit.
