---
id: T-020
title: Global Design Tokens and Theme Provider
audience: [human, ai]
last_updated: 2026-04-22
tags: [frontend, ui, theme, dx]
source_of_truth: true
---

# T-020 - Global Design Tokens and Theme Provider

## 🏗 Context & Motivation
Currently, different micro-frontends (MFEs) may use inconsistent colors, spacing, and typography. To ensure a cohesive user experience and enable white-labeling/theming, we need a centralized design token system.

## 🗺 Scope & Impact
- **Shared Libs**: `libs/apps-platform-ui/src/styles/...`
- **Portal Integration**: `apps/portal/src/styles.css`
- **MFE Consumption**: All apps in `apps/`.

## ✅ Acceptance Criteria
- [ ] Define a set of base design tokens (colors, spacing, typography) using CSS variables.
- [ ] Implement a `ThemeService` or a global CSS provider in `apps-platform-ui`.
- [ ] Ensure all existing MFEs consume these tokens instead of hardcoded values.
- [ ] Support at least two themes (e.g., Light and Dark) to demonstrate flexibility.

## 🛠 Technical Constraints & References
- **CSS Variables**: Prefer native CSS variables (`--color-primary`) for maximum compatibility across different frameworks.
- **Fallbacks**: Provide sensible default values.
- **Nx Usage**: Tokens should be easily importable into any project in the workspace.

## 🚦 Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: [AI Agent]

## References
- [B-006 - Platform Hardening and Developer Experience](B-006%20-%20Platform%20Hardening%20and%20Developer%20Experience.md)
