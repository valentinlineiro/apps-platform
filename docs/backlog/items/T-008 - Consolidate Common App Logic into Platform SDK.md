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
- [ ] **Alembic Utility**: Move the `_run_alembic_upgrade` logic to a reusable utility in the SDK (e.g., `apps_platform_sdk.database.migrations`).
- [ ] **App Factory/Config**: Create a standard Flask app factory or initialization helper in the SDK that sets up CORS, sessions, logging, and error handlers with platform defaults.
- [ ] **Database Helpers**: Move the `_PgConn` wrapper or similar common DB utilities to the SDK.
- [ ] **Manifest Standardization**: Define a standard `Manifest` model/schema and a helper to register the `/manifest` endpoint automatically.
- [ ] **Refactor Apps**: Update existing applications to use these new SDK utilities and remove duplicated code.
- [ ] **Tests**: Add unit tests in the SDK for all new utilities.

## Technical Constraints & References
- **Backwards Compatibility**: Ensure the SDK remains compatible with different Flask versions if applicable.
- **Optional Dependencies**: Use optional imports or clear error messages for SDK features that require extra packages (like `psycopg2` or `alembic`).
- **Standardized Logging**: All moved logic must use `apps_platform_sdk.observability`.

## Status
- **Current Status**: `Planned`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## References
- [Coding Standards](../../how-to/coding-standards.md)
- [Workspace Management](../../how-to/workspace-management.md)

## Change log
- **2026-04-22**: Initial task creation.
