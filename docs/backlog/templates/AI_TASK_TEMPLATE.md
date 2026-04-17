---
id: DOC-TMP-AI-001
title: AI-Ready Task Template
audience: [human, ai]
last_updated: 2026-04-17
tags: [template, backlog, ai, tasks]
source_of_truth: true
related: [DOC-AI-TS-001]
---

# AI-Ready Task Template

## Purpose
Provide a standardized structure for defining backlog items that AI agents can execute with high autonomy and success rates.

## When to use
Use this template whenever creating a new feature request or technical task in the `docs/backlog/items/` directory.

## Content

### File Naming
Save new files as `Category-Number - Title.md` (e.g., `B-004 - New Feature.md`). Refer to [Backlog Guidelines](../../backlog/GUIDELINES.md) for details.

---

### 🏗 Context & Motivation
*Briefly describe the "Why" behind this task. What problem are we solving? What is the user value?*

---

### 🗺 Scope & Impact
*Identify the areas of the codebase that will be affected.*
- **Frontend Components**: `apps/portal/src/app/...`
- **Backend Endpoints**: `apps/portal/backend/app.py`
- **Shared Libs**: `libs/platform-python-sdk/...`

---

### ✅ Acceptance Criteria
*Provide a checklist of verifiable requirements.*
- [ ] Feature X should behave as described.
- [ ] Unit tests for [module] cover [edge case].
- [ ] UI matches existing styling and component standards.
- [ ] No regressions in [related feature].

---

### 🛠 Technical Constraints & References
*Explicitly state requirements that the AI might miss.*
- **Angular Standards**: Use separate `.html` and `.css` files.
- **Python Standards**: Use `platform_sdk.observability` for all logging.
- **Auth**: Define required roles (e.g., `admin`).
- **Reference Docs**: Link to relevant `concepts/` or `how-to/` files.

---

### 🚦 Status
- **Current Status**: `Draft` | `Planned` | `Active` | `Done`
- **Priority**: `High` | `Medium` | `Low`
- **Assignee**: [AI Agent Name / Human Name]

## References
- [Backlog Guidelines](../../backlog/GUIDELINES.md)
- [Task Schema](../../ai/task-schema.md)

## Change log
- **2026-04-17**: Standardized metadata and section order.
