# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code).

## 🧠 Knowledge Base

The documentation follows a standardized taxonomy. **Refer to the Documentation Map first.**

- **Entry Point**: [**Platform Documentation Map**](docs/README.md)
- **AI Briefing**: [**AI Context Pack**](docs/ai/context-pack.md)

## Quick Start
```bash
docker compose up --build
```
- **Portal (Angular PWA)**: `https://localhost`
- **Keycloak (Auth)**: `https://localhost/admin` (admin/admin)

## Guidelines
- **Metadata**: Every new doc MUST include YAML front matter and follow the section order: Purpose, When to use, Content, References, Change log.
- **Backlog**: New tasks MUST use the `docs/backlog/templates/AI_TASK_TEMPLATE.md` and be named `Category-Number - Title.md`.
- **Workspace**: Refer to `docs/how-to/workspace-management.md` for Nx-specific guidelines.
- **Architecture**: Read `docs/concepts/architecture.md` before proposing changes.
