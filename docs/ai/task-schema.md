---
id: DOC-AI-TS-001
title: AI Task Schema
audience: [human, ai]
last_updated: 2026-04-17
tags: [schema, ai, backlog, tasks, metadata]
source_of_truth: true
related: [DOC-TMP-AI-001]
---

# AI Task Schema

## Purpose
Formally define the metadata and structural requirements for backlog items to ensure they are machine-readable and executable by AI agents.

## When to use
Use this schema as a reference when updating the `AI_TASK_TEMPLATE.md` or when auditing the backlog for AI-readiness.

## Content

### Required Metadata (Front Matter)
Every backlog item must include:
- `id`: A unique identifier (e.g., `B-001`).
- `title`: A concise, descriptive title.
- `audience`: Must include `ai`.
- `tags`: Must include `backlog` and the category (e.g., `business`, `technical`).
- `source_of_truth`: Boolean (usually `true`).

### Required Sections (In Order)
1.  **Purpose**: Why the task exists.
2.  **When to use**: High-level context.
3.  **Content**:
    - **Context & Motivation**: Detailed background.
    - **Scope & Impact**: Affected files and modules.
    - **Acceptance Criteria**: Verifiable checklist.
    - **Technical Constraints**: Hard requirements.
    - **Status**: State and priority.
4.  **References**: Links to related documentation.
5.  **Change log**: Version history of the task definition.

## References
- [AI-Ready Task Template](../backlog/templates/AI_TASK_TEMPLATE.md)

## Change log
- **2026-04-17**: Initial version of the AI Task Schema.
