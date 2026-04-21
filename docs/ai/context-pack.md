---
id: DOC-AI-CP-001
title: AI Context Pack
audience: [ai]
last_updated: 2026-04-17
tags: [ai, context, briefing, agent-instructions]
source_of_truth: true
related: [DOC-CON-001, DOC-HT-001, DOC-AI-TS-001]
---

# AI Context Pack

## Purpose
Provide a canonical, machine-readable briefing for AI agents (Gemini, Claude, Codex) to ensure they understand the project's core identity and constraints immediately upon entry.

## When to use
AI agents should read this file first whenever they are initialized in this workspace to align their strategy with the platform's architecture and standards.

## Content

### Core Identity
- **Project**: Monorepo orchestrator for micro-frontends.
- **Model**: Declarative App Catalog (Postgres-backed).
- **Primary Tech**: Nx, Angular 21 (Signals/Zoneless), Flask 3 (Blueprint-based), Docker, Caddy, Keycloak.

### Hard Constraints
1. **Frontend**: Standalone components ONLY. Separate HTML/CSS files ONLY.
2. **Backend**: Must use `apps-platform-sdk` for shared backend primitives.
3. **Python Environment**: **Mandatory Isolation**. Every backend app and library MUST use a local `.venv`.
4. **Execution**: Never run `pip` or `python` globally. Always use `.venv/bin/python3` and `.venv/bin/pip`.
5. **Setup**: Use `npx nx run <project>:setup` to initialize virtual environments.
6. **Database**: PostgreSQL (Docker-backed) is the primary source of truth for the app catalog and user data.
7. **Auth**: Keycloak OIDC with PKCE. Gated by Nginx `auth_request`.

### Knowledge Map
- Architecture: `docs/concepts/architecture.md`
- Conventions: `docs/how-to/coding-standards.md`
- Setup: `docs/quickstart/setup.md`
- Backlog: `docs/backlog/index.md`

### Task Execution Protocol
- Always verify against the `AI-Ready Task Template`.
- Always update documentation (Change log) after significant changes.
- Always use Nx for task running.

## References
- [System Architecture](../concepts/architecture.md)
- [Coding Standards](../how-to/coding-standards.md)

## Change log
- **2026-04-21**: Updated with mandatory Python virtual environment standards and Declarative App Catalog transition.
- **2026-04-17**: Initial version of the AI Context Pack.
