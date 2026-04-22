---
id: T-021
title: Standardized MFE Event Bus
audience: [human, ai]
last_updated: 2026-04-22
tags: [frontend, mfe, communication, dx]
source_of_truth: true
---

# T-021 - Standardized MFE Event Bus

## 🏗 Context & Motivation
MFEs are isolated by design, but they often need to communicate (e.g., "User logged out", "Tenant switched"). We need a standardized, decoupled way for MFEs to broadcast and listen to events without direct dependencies.

## 🗺 Scope & Impact
- **Shared Libs**: `libs/apps-platform-ui/src/lib/events/...`
- **Portal Integration**: Core event bus initialization.
- **MFE Consumption**: All apps in `apps/`.

## ✅ Acceptance Criteria
- [ ] Implement a lightweight event bus (e.g., based on Custom Events or a simple Pub/Sub).
- [ ] Define a standard set of platform events (e.g., `PLATFORM_USER_CHANGED`, `PLATFORM_THEME_CHANGED`).
- [ ] Provide TypeScript types/schemas for event payloads.
- [ ] Implement a utility in `apps-platform-ui` for easy subscription and dispatching.

## 🛠 Technical Constraints & References
- **Decoupling**: MFEs must not need to know about each other's internals.
- **Payload Validation**: Consider using a shared schema (T-014) for complex payloads.
- **Cleanup**: Ensure listeners are properly disposed of when MFEs are unloaded.

## 🚦 Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [B-006 - Platform Hardening and Developer Experience](B-006%20-%20Platform%20Hardening%20and%20Developer%20Experience.md)
- [T-014 - Schema Registry for Cross-App Communication](T-014%20-%20Schema%20Registry%20for%20Cross-App%20Communication.md)
