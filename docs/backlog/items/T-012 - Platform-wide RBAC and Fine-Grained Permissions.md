---
id: T-012
title: Platform-wide RBAC and Fine-Grained Permissions
audience: [human, ai]
last_updated: 2026-04-22
tags: [security, authz, rbac, keycloak]
source_of_truth: true
related: [DOC-TMP-AI-001, T-005]
---

# Platform-wide RBAC and Fine-Grained Permissions

## Purpose
Implement a standardized Role-Based Access Control (RBAC) system that allows applications to define and enforce fine-grained permissions using Keycloak as the central identity provider.

## Context & Motivation
While Keycloak handles authentication, the platform lacks a unified way to handle authorization (what a user can do within an app). Currently, permissions are either hardcoded or inconsistently managed. This task aims to create a "Permission Port" in the SDK and a corresponding UI service that allows applications to query user capabilities (e.g., `can_edit_exam`, `can_view_audit_logs`) based on Keycloak roles and attributes.

## Scope & Impact
- **Platform SDK**: Add a `security.authorization` module to handle role-to-permission mapping and decorators for Flask routes.
- **UI Library**: Add a `PermissionService` to handle conditional rendering based on user roles.
- **Portal Backend**: Update the registry to include "Required Permissions" for each app.
- **Impact**: Unified security model, easier auditing, and support for multi-tenant or role-specific features.

## Acceptance Criteria
- [ ] **Permission Port**: Define a standard interface in the SDK for checking permissions.
- [ ] **Flask Decorators**: Implement `@require_permission('permission_name')` in the SDK.
- [ ] **UI Integration**: Create an Angular structural directive `*ifPermission="'name'"` in the UI library.
- [ ] **Catalog Integration**: Update `static_apps.json` to allow defining which permissions are required to see/access an app.
- [ ] **Keycloak Mapping**: Document how to map Keycloak Client Roles to Platform Permissions.
- [ ] **Pilot**: Implement a "Viewer" vs "Admin" role in `exam-corrector` using the new system.

## Technical Constraints & References
- **Decoupling**: Applications should depend on *permissions* (actions), not *roles* (groups), to allow for flexible role definitions.
- **Efficiency**: Permission checks must be cached or performed on the JWT/Session to avoid excessive calls to Keycloak.
- **Fail-Safe**: Defaults must be "Deny All" if no permission is found.

## Status
- **Current Status**: `Planned`
- **Priority**: `High`
- **Assignee**: [AI Agent]

## References
- [Keycloak Authorization Services](https://www.keycloak.org/docs/latest/authorization_services/)
- [Portal Backend Hardening (T-005)](T-005%20-%20Portal%20Backend%20Hardening.md)

## Change log
- **2026-04-22**: Initial task creation.
