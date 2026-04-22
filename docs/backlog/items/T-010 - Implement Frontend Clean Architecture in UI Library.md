---
id: T-010
title: Implement Frontend Clean Architecture in UI Library
audience: [human, ai]
last_updated: 2026-04-22
tags: [frontend, architecture, clean-architecture, ui-library]
source_of_truth: true
related: [T-009]
---

# Implement Frontend Clean Architecture in UI Library

## Purpose
Apply Clean Architecture principles to the frontend by centralizing shared domain models, business logic, and infrastructure adapters in the `apps-platform-ui` library.

## Context & Motivation
Currently, frontend applications (like `portal` and various micro-apps) redefine common models (e.g., `AppManifest`) and handle API communication directly within Angular services. This couples business logic to the Angular framework and leads to duplication. By introducing a framework-agnostic core in the UI library, we can share logic across different frontend apps (and potentially even non-Angular environments) while making the code easier to test and maintain.

## Scope & Impact
- **Shared Libs**: `libs/apps-platform-ui/src/lib/` (new directories for `domain`, `application`, and `infrastructure`).
- **Applications**: All Angular-based apps in `apps/`.
- **Impact**: Decouples business logic from UI components and the Angular framework, enabling better testability and reuse.

## Acceptance Criteria
- [ ] **Frontend Domain Layer**: Define core business models (e.g., `AppManifest`, `User`) and interfaces for services in a framework-agnostic way (pure TypeScript) within `libs/apps-platform-ui`.
- [ ] **Application Layer (Use Cases)**: Move complex frontend logic (e.g., registry filtering, permission checks) into Use Case classes.
- [ ] **Infrastructure Layer**: Implement shared API clients and storage adapters.
- [ ] **Framework Adapters**: Provide Angular-specific wrappers (Services/Signals) that consume the framework-agnostic core.
- [ ] **Refactor `portal`**: Update the `portal` app to use the centralized models and logic from the SDK.
- [ ] **Test Strategy**: Implement unit tests for the domain and application layers that run without Angular's `TestBed`.

## Technical Constraints & References
- **Framework Independence**: The `domain` and `application` folders in the SDK must not import from `@angular/core`.
- **Signals Integration**: Ensure the architecture works seamlessly with Angular Signals for reactive state management in the UI layer.
- **Consistency**: Align naming conventions and patterns with the backend Clean Architecture (T-009).

## Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [Coding Standards](../../how-to/coding-standards.md)
- [Clean Architecture Patterns (T-009)](T-009%20-%20Standardize%20Clean%20Architecture%20Patterns%20in%20SDK.md)

## Change log
- **2026-04-22**: Initial task creation.
