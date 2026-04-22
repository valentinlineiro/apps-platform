---
id: T-016
title: Centralized Audit Logging Specification
audience: [human, ai]
last_updated: 2026-04-22
tags: [security, audit, sdk, technical]
source_of_truth: true
related: [DOC-TMP-AI-001, T-012]
---

# Centralized Audit Logging Specification

## Purpose
Standardize the collection and storage of user activity logs across all platform applications to ensure security compliance and a unified audit trail.

## Context & Motivation
Currently, each app handles auditing differently (or not at all). This makes it impossible for platform administrators to have a single view of "who did what" across different micro-frontends. By centralizing the audit specification in the SDK, apps can easily emit standard events (e.g., `resource_created`, `permission_denied`) to a central database or event stream.

## Scope & Impact
- **Platform SDK**: Define a standard `AuditEvent` schema and a high-level `AuditLogger` utility.
- **Applications**: All backend services should adopt the SDK's audit logger.
- **Portal Backend**: Implement the central collector/repository for these events.
- **Impact**: Improved security, accountability, and simplified compliance auditing.

## Acceptance Criteria
- [x] **SDK Utility**: Add a standard `AuditLogger` to the SDK that emits events with context (user, IP, timestamp, action, target).
- [x] **Standard Schema**: Define a common set of platform-wide action types (CRUD, Auth, Admin).
- [x] **Central Storage**: Implement a centralized audit log repository in the Portal Backend.
- [x] **Audit UI**: Create a simple "Audit Trail" view in the Portal for administrators.
- [x] **Pilot**: Migrate `portal` to use the new centralized audit logger.

## Technical Constraints & References
- **Performance**: Audit logging must be non-blocking or extremely fast.
- **Immutability**: Audit logs should ideally be stored in a way that prevents tampering (e.g., append-only tables).
- **Retention**: Define a standard log retention policy (e.g., 90 days).

## Status
- **Current Status**: `Done`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## 🗒 Implementation Notes
- **SDK** (`apps_platform_sdk.audit`): `AuditActions` class with 8 canonical string constants (Auth, Tenant Admin, Plugin). `AuditLogger` class with `log()`, `list_user_entries()`, and `list_all_entries()` — compatible with the `AuditPort` protocol.
- **Portal backend**: `SqlAuditRepository` now inherits from `AuditLogger` (zero duplication). `AuditPort` extended with `list_all_entries`. New `GET /api/admin/audit` endpoint (owner/admin only) with limit/offset pagination. `_log_audit` in `app.py` routed through `_audit_repo` after bootstrap. Application layer now uses `AuditActions` constants throughout.
- **Angular** (`/audit` route): `AuditPageComponent` — table of all entries with user identity, action badge, resource, and date. Accessible to owners/admins only; "Auditoría" nav link visible only in that role.
- **Tests**: 5 new admin audit use-case tests + 3 SDK tests. All 99 portal + 28 SDK tests pass.
- **Note**: exam-corrector backend is Angular-only (no Python backend at time of implementation). aneca-advisor can adopt `AuditLogger` from the SDK in a future pass.

## References
- [RBAC and Permissions (T-012)](T-012%20-%20Platform-wide%20RBAC%20and%20Fine-Grained%20Permissions.md)
- [Coding Standards](../../how-to/coding-standards.md)

## Change log
- **2026-04-22**: Initial task creation.
