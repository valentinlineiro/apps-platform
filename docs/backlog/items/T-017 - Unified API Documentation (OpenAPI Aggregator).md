---
id: T-017
title: Unified API Documentation (OpenAPI Aggregator)
audience: [human, ai]
last_updated: 2026-04-22
tags: [dx, documentation, openapi, swagger, sdk]
source_of_truth: true
related: [DOC-TMP-AI-001, T-013]
---

# Unified API Documentation (OpenAPI Aggregator)

## Purpose
Improve the developer experience (DX) by automatically generating and aggregating API documentation for all platform services into a single, searchable portal.

## Context & Motivation
As the number of backend services grows, it becomes increasingly difficult for developers to discover and understand available endpoints. Currently, documentation is mostly manual or buried in source code. By leveraging the SDK to generate OpenAPI (Swagger) specs, we can create a "Developer Portal" within the shell that provides interactive documentation for every micro-service.

## Scope & Impact
- **Platform SDK**: Integrate a library like `flask-openapi3` or `flasgger` to auto-generate specs from routes.
- **Portal Shell**: Create a "Developer Portal" view that fetches and displays specs from the app registry.
- **Applications**: All Python backends should be updated to use the SDK-provided API doc wrapper.
- **Impact**: Faster integration, better API design consistency, and improved onboarding for new developers.

## Acceptance Criteria
- [ ] **SDK Integration**: Add an API documentation helper to the SDK that auto-generates OpenAPI 3.x specs.
- [ ] **Manifest Entry**: Update the `AppManifest` to include an optional `docsPath` (e.g., `/api/docs/openapi.json`).
- [ ] **Aggregator UI**: Build a "Developer Hub" in the Portal using Swagger UI or Redoc that can switch between different service specs.
- [ ] **Type Sharing**: Ensure that the generated documentation reflects the Pydantic/dataclass models used in the backends.
- [ ] **Pilot**: Enable auto-docs for `portal-backend` and `exam-corrector`.

## Technical Constraints & References
- **Standardization**: All services must use OpenAPI 3.x.
- **Auth**: The documentation UI should ideally handle session-based authentication automatically for the interactive "Try it out" feature.
- **Offline Access**: Support exporting the combined specs for use in external tools like Postman or Insomnia.

## Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [Nx Generators (T-013)](T-013%20-%20Automated%20New%20App%20Scaffolding.md)
- [OpenAPI Specification](https://www.openapis.org/)

## Change log
- **2026-04-22**: Initial task creation.
