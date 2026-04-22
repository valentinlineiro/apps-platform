---
id: U-002
title: Centralized Internationalization (i18n) Service
audience: [human, ai]
last_updated: 2026-04-22
tags: [i18n, ux, localization, ui-library]
source_of_truth: true
related: [DOC-TMP-AI-001]
---

# Centralized Internationalization (i18n) Service

## Purpose
Standardize the multi-language experience across the platform by providing a centralized i18n service in the UI library that handles shared translations and app-specific bundles.

## Context & Motivation
Currently, applications handle translations independently (mostly Spanish), leading to an inconsistent user experience for non-Spanish speakers. By centralizing i18n in the `apps-platform-ui` library, we can share common tokens (e.g., "Save", "Cancel", "Welcome") while allowing each MFE to load its own specific translation files. This also enables runtime language switching for the entire portal.

## Scope & Impact
- **UI Library**: Implement a `TranslationService` and a shared assets folder for global tokens.
- **Applications**: All Angular-based apps should migrate to the shared service.
- **Impact**: Consistent terminology across apps and ready-to-scale localization.

## Acceptance Criteria
- [x] **Shared Service**: Create an i18n service in the UI library using standard Angular signals.
- [x] **Global Tokens**: Defined a set of "Common Platform Tokens" (Spanish and English) in `apps/portal/public/i18n/portal/`.
- [x] **App Bundles**: Implemented a lazy-loading strategy that fetches JSON files on-demand.
- [x] **Language Switcher**: Added a language toggle in the Portal Shell Header.
- [x] **Pilot**: Migrated `aneca-advisor` to use the new i18n service.

## Technical Constraints & References
- **Performance**: Translation bundles are lazy-loaded via `HttpClient`.
- **Fallbacks**: Returns the key itself if the translation is missing.
- **Cross-MFE**: Uses a `PLATFORM_LANGUAGE_CHANGED` CustomEvent for real-time synchronization across all MFEs.

## Status
- **Current Status**: `Done`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## 🗒 Implementation Notes
- **UI Library**: `libs/apps-platform-ui/src/lib/i18n/` contains the `TranslationService` (signals-based) and `TranslatePipe` (standalone).
- **MFE Sync**: The `TranslationService` constructor listens for `PLATFORM_LANGUAGE_CHANGED` events and automatically reloads all previously loaded namespaces.
- **Pilot**: `AnecaAdvisorAppComponent` now uses `TranslatePipe` for core labels and computed signals for dynamic text (like tabs).

## References
- [Angular i18n Guide](https://angular.io/guide/i18n-overview)
- [Clean Architecture (T-010)](T-010%20-%20Implement%20Frontend%20Clean%20Architecture%20in%20UI%20Library.md)

## Change log
- **2026-04-22**: Initial task creation.
