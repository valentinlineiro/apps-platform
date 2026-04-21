---
id: T-003
title: Implement Alembic Schema Migrations
audience: [human, ai]
last_updated: 2026-04-21
tags: [backlog, database, alembic, migration, technical]
source_of_truth: true
related: [DOC-CON-001, DOC-HT-001]
---

# T-003 - Implement Alembic Schema Migrations

## Purpose
Replace raw SQL `CREATE TABLE IF NOT EXISTS` initialization with a robust, versioned schema migration system using Alembic.

## When to use
This is a high-priority infrastructure task that must be completed before the first production deployment to ensure safe database schema evolution.

## Content

### 🏗 Context & Motivation
Currently, backends use a simple `_init_db()` function to create tables at startup. This is sufficient for bootstrapping but dangerous for evolution: it cannot handle adding columns, changing types, or managing indexes without risk of data loss or inconsistency across environments.

### 🗺 Scope & Impact
- **Backend Projects**: `portal-backend`, `aneca-advisor-backend`, `exam-corrector-backend`.
- **Infrastructure**: New `alembic/` directories in each backend.
- **Workflow**: Developers will generate migration scripts (`alembic revision`) for every schema change.

### ✅ Acceptance Criteria
- [x] Alembic initialized in all Python backends.
- [x] Current database schema captured in a "baseline" migration (000_initial).
- [x] Deployment process (Docker/CI) updated to run `alembic upgrade head` before starting the app.
- [x] `_init_db()` functions removed from application code.
- [x] Database connection handling unified through Alembic's `env.py`.

### 🛠 Technical Constraints & References
- **Standard**: Follow the platform's preference for **psycopg2** and **PostgreSQL**.
- **Nx Integration**: Add `migration` and `migrate` targets to `project.json` for each backend.
- **SDK**: Shared database connection logic should be leveraged from `apps-platform-sdk`.

---

### 🚦 Status
- **Current Status**: `Active`
- **Priority**: `High`
- **Assignee**: Gemini CLI

## References
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Postgres Schema Initialization](../concepts/architecture.md)

## Change log
- **2026-04-21**: Fixed silent failure in exam-corrector: psycopg2-binary was missing so SQLAlchemy could not open a Postgres connection; added .dockerignore to prevent Python 3.12 venvs from being copied into Python 3.11 images.
- **2026-04-21**: Initial implementation by Gemini CLI: Alembic initialized in all backends, per-service version tables, --preload gunicorn flag.
- **2026-04-21**: Created to address critical schema evolution gaps.
