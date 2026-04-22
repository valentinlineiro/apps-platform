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
- [ ] Enable RLS on all tables containing tenant-specific data.
- [ ] Implement a mechanism in `apps-platform-sdk` to set the `current_tenant` in the Postgres session (e.g., via `SET app.current_tenant = ...`).
- [ ] Define global RLS policies that restrict access based on the session variable.
- [ ] Verify that a service cannot query data belonging to a different tenant even if the SQL query is missing a `WHERE` clause.

## 🛠 Technical Constraints & References
- **Performance**: Monitor the impact of RLS on complex joins.
- **Migration Path**: Ensure existing data and migrations are compatible with RLS.
- **Postgres Specific**: This task is specific to PostgreSQL 9.5+.

## 🚦 Status
- **Current Status**: `Planned`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## References
- [B-006 - Platform Hardening and Developer Experience](B-006%20-%20Platform%20Hardening%20and%20Developer%20Experience.md)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
