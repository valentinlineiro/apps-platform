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
- [ ] **SDK Utility**: Add a standard `AuditLogger` to the SDK that emits events with context (user, IP, timestamp, action, target).
- [ ] **Standard Schema**: Define a common set of platform-wide action types (CRUD, Auth, Admin).
- [ ] **Central Storage**: Implement a centralized audit log repository in the Portal Backend.
- [ ] **Audit UI**: Create a simple "Audit Trail" view in the Portal for administrators.
- [ ] **Pilot**: Migrate `exam-corrector` and `portal` to use the new centralized audit logger.

## Technical Constraints & References
- **Performance**: Audit logging must be non-blocking or extremely fast.
- **Immutability**: Audit logs should ideally be stored in a way that prevents tampering (e.g., append-only tables).
- **Retention**: Define a standard log retention policy (e.g., 90 days).

## Status
- **Current Status**: `Planned`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## References
- [RBAC and Permissions (T-012)](T-012%20-%20Platform-wide%20RBAC%20and%20Fine-Grained%20Permissions.md)
- [Coding Standards](../../how-to/coding-standards.md)

## Change log
- **2026-04-22**: Initial task creation.
