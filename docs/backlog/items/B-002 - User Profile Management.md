---
id: B-002
title: User Profile & Settings Management
audience: [human, ai]
last_updated: 2026-04-17
tags: [backlog, profile, settings, user, tenant, business]
source_of_truth: true
related: [DOC-APP-POR-001, DOC-HT-001]
---

# B-002 - User Profile & Settings Management

## Purpose
Decouple personal user preferences from workspace-specific (tenant) settings.

## When to use
Consult this when implementing profile updates, theme preferences, or tenant-wide configuration settings.

## Content

### 🏗 Context & Motivation
Currently, profile and settings are blended. We need a clear split: personal data follows the user across tenants; workspace settings are scoped per tenant.

### 🗺 Scope & Impact
- **Backend**: `apps/portal/backend/app.py`, migration for `user_preferences`, `user_profiles`, and `user_tenant_preferences`.
- **Frontend**: New `ProfilePageComponent` and restructured `SettingsPageComponent`.
- **API**: New endpoints under `/auth/me/profile`, `/auth/me/preferences`, and `/api/tenants/:id/settings`.

### ✅ Acceptance Criteria
- [ ] Schema: New tables `user_preferences`, `user_profiles`, `user_tenant_preferences` created.
- [ ] API: All 6 endpoints defined in the plan are functional and authenticated.
- [ ] UI - Header: Avatar/Initials dropdown added to `ShellHeaderComponent`.
- [ ] UI - Profile: New `/profile` page with Identity, Preferences, Notifications, and Privacy sections.
- [ ] UI - Settings: Renamed to "Workspace" and gated admin-only sections (Member management, App installs).

### 🛠 Technical Constraints & References
- **Rules**: "If it follows the person everywhere → store on the user. If it depends on the workspace → store per tenant."
- **Angular**: Ensure standalone components use Signals and Zoneless change detection.

---

### 🚦 Status
- **Current Status**: `Planned`
- **Priority**: `Medium`
- **Assignee**: Unassigned

## References
- [Coding Standards](../../how-to/coding-standards.md)
- [Portal Deep Dive](../../apps/portal/index.md)

## Change log
- **2026-04-17**: Reformatted to match the standardized AI-Ready Task Template.
