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
- **Architecture**: Read `docs/concepts/architecture.md` before proposing changes.

<!-- nx configuration start-->
<!-- Leave the start & end comments to automatically receive updates. -->

## General Guidelines for working with Nx

- For navigating/exploring the workspace, invoke the `nx-workspace` skill first - it has patterns for querying projects, targets, and dependencies
- When running tasks (for example build, lint, test, e2e, etc.), always prefer running the task through `nx` (i.e. `nx run`, `nx run-many`, `nx affected`) instead of using the underlying tooling directly
- Prefix nx commands with the workspace's package manager (e.g., `pnpm nx build`, `npm exec nx test`) - avoids using globally installed CLI
- You have access to the Nx MCP server and its tools, use them to help the user
- For Nx plugin best practices, check `node_modules/@nx/<plugin>/PLUGIN.md`. Not all plugins have this file - proceed without it if unavailable.
- NEVER guess CLI flags - always check nx_docs or `--help` first when unsure

## Scaffolding & Generators

- For scaffolding tasks (creating apps, libs, project structure, setup), ALWAYS invoke the `nx-generate` skill FIRST before exploring or calling MCP tools

## When to use nx_docs

- USE for: advanced config options, unfamiliar flags, migration guides, plugin configuration, edge cases
- DON'T USE for: basic generator syntax (`nx g @nx/react:app`), standard commands, things you already know
- The `nx-generate` skill handles generator discovery internally - don't call nx_docs just to look up generator syntax


<!-- nx configuration end-->
