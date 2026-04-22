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
- [ ] **Shared Service**: Create an i18n service in the UI library using standard Angular patterns (or a framework-agnostic core).
- [ ] **Global Tokens**: Define a set of "Common Platform Tokens" (Spanish and English) available to all apps.
- [ ] **App Bundles**: Implement a lazy-loading strategy for app-specific translation bundles.
- [ ] **Language Switcher**: Add a language toggle in the Portal Shell that propagates the change to all active MFEs.
- [ ] **Pilot**: Migrate the Portal and `aneca-advisor` to use the new i18n service.

## Technical Constraints & References
- **Performance**: Translation bundles must be lazy-loaded to avoid increasing the initial bundle size.
- **Fallbacks**: Always provide a default fallback language (e.g., Spanish).
- **SEO/Accessibility**: Ensure translated text is correctly handled by screen readers and search engines (if applicable).

## Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [Angular i18n Guide](https://angular.io/guide/i18n-overview)
- [Clean Architecture (T-010)](T-010%20-%20Implement%20Frontend%20Clean%20Architecture%20in%20UI%20Library.md)

## Change log
- **2026-04-22**: Initial task creation.
