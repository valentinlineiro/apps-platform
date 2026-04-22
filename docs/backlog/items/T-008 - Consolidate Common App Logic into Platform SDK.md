---
id: T-008
title: Consolidate Common App Logic into Platform SDK
audience: [human, ai]
last_updated: 2026-04-22
tags: [refactoring, sdk, architecture]
source_of_truth: true
related: [DOC-TMP-AI-001]
---

# Consolidate Common App Logic into Platform SDK

## Purpose
Reduce code duplication and enforce consistency across all applications by moving shared backend patterns, utilities, and configurations into the `apps-platform-sdk`.

## Context & Motivation
Currently, several applications (e.g., `aneca-advisor`, `exam-corrector`) implement similar boilerplate logic for database migrations, Flask app initialization, database connection wrapping, and manifest serving. This duplication leads to maintenance overhead and potential inconsistencies. By centralizing this logic in the SDK, we ensure that all apps benefit from platform-level improvements and follow the same standards.

## Scope & Impact
- **Shared Libs**: `libs/apps-platform-sdk/apps_platform_sdk/`
- **Applications**: `apps/aneca-advisor/backend/`, `apps/exam-corrector/backend/`, `apps/attendance-checker/backend/` (if any), `apps/portal/backend/`
- **Impact**: All backend services will have a more streamlined `app.py` and consistent startup behavior.

## Acceptance Criteria
- [x] **Alembic Utility**: `run_alembic_upgrade(database_url, alembic_ini, logger)` in `apps_platform_sdk.database.migrations`. Lazy-imports alembic; uses `exc_info=True` on failure.
- [x] **App Factory/Config**: `configure_app(app, *, cors_resources, configure_session)` in `apps_platform_sdk.flask_app`. Wires logging, error handlers, CORS, and session-cookie defaults.
- [x] **Database Helpers**: `PgConn` and `make_db_factory(database_url)` in `apps_platform_sdk.database.pg_conn`. Lazy-imports psycopg2.
- [x] **Manifest Standardization**: `create_manifest_blueprint(manifest)` in `apps_platform_sdk.manifest`. Registers `GET /manifest`.
- [x] **Refactor Apps**: `aneca-advisor`, `exam-corrector`, and `portal` backends updated. Duplicated `_PgConn`, `_run_alembic_upgrade`, and session-cookie setup removed from all three.
- [x] **Tests**: 17 unit tests added in `libs/apps-platform-sdk/tests/test_sdk.py` covering all new utilities.

## Technical Constraints & References
- **Backwards Compatibility**: Ensure the SDK remains compatible with different Flask versions if applicable.
- **Optional Dependencies**: Use optional imports or clear error messages for SDK features that require extra packages (like `psycopg2` or `alembic`).
- **Standardized Logging**: All moved logic must use `apps_platform_sdk.observability`.

## Status
- **Current Status**: `Done`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## References
- [Coding Standards](../../how-to/coding-standards.md)
- [Workspace Management](../../how-to/workspace-management.md)

## Change log
- **2026-04-22**: Implemented. New SDK modules: `database/` (PgConn, make_db_factory, run_alembic_upgrade), `flask_app.py` (configure_app), `manifest.py` (create_manifest_blueprint). All 3 backends refactored. 17 tests, all green.
- **2026-04-22**: Initial task creation.
