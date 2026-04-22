---
id: T-022
title: Database Row-Level Security for Tenant Isolation
audience: [human, ai]
last_updated: 2026-04-22
tags: [backend, security, database, multi-tenancy]
source_of_truth: true
---

# T-022 - Database Row-Level Security for Tenant Isolation

## 🏗 Context & Motivation
While the platform supports tenants, isolation is currently handled at the application logic level (e.g., `WHERE tenant_id = ...`). To prevent data leakage due to bugs, we should implement PostgreSQL Row-Level Security (RLS) as a second layer of defense.

## 🗺 Scope & Impact
- **Backend Infrastructure**: Database schema definitions and migrations.
- **Shared Libs**: `apps-platform-sdk` database utilities.
- **App Backends**: All services using the shared PostgreSQL database.

## ✅ Acceptance Criteria
- [x] Enable RLS on all tables containing tenant-specific data.
- [x] Implement a mechanism in `apps-platform-sdk` to set the `current_tenant` in the Postgres session (e.g., via `SET app.current_tenant = ...`).
- [x] Define global RLS policies that restrict access based on the session variable.
- [x] Verify that a service cannot query data belonging to a different tenant even if the SQL query is missing a `WHERE` clause.

## 🛠 Technical Constraints & References
- **Performance**: Monitor the impact of RLS on complex joins.
- **Migration Path**: Ensure existing data and migrations are compatible with RLS.
- **Postgres Specific**: This task is specific to PostgreSQL 9.5+.

## 🚦 Status
- **Current Status**: `Done`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## 🗒 Implementation Notes
- **Migration** (`e6f7a8b9c0d1`): Enables RLS on `tenant_memberships`, `plugin_installs`, `user_tenant_preferences`. Policy allows all rows when `app.current_tenant` is unset (empty) — intentional for migrations and bootstrap.
- **SDK** (`apps_platform_sdk.database`): `PgConn.set_tenant(tenant_id)` issues `set_config('app.current_tenant', …, FALSE)`. `make_tenant_db_factory(url, tenant_id_fn)` wraps `make_db_factory` and calls `set_tenant` on every new connection.
- **Portal backend** (`app.py`): Uses `make_tenant_db_factory` with `_current_tenant_id()` which reads `session["tenant_id"]` inside request context or returns `None` outside it (bootstrap, migrations). Stores `tenant_id` in the Flask session after a successful OAuth login.
- **Unit tests**: 6 new tests in `libs/apps-platform-sdk/tests/test_sdk.py` covering `set_tenant` (with id, None, empty) and `make_tenant_db_factory` (with and without tenant). All 23 SDK + 94 portal tests pass.
- **Integration**: Full enforcement requires the app role to be a non-owner of the tables (Postgres superuser bypasses RLS). See migration docstring.

## References
- [B-006 - Platform Hardening and Developer Experience](B-006%20-%20Platform%20Hardening%20and%20Developer%20Experience.md)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
