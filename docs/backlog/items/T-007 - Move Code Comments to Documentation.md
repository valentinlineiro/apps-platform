---
id: T-007
title: Move Code Comments to Documentation
audience: [human, ai]
last_updated: 2026-04-22
tags: [technical-debt, documentation, refactoring]
source_of_truth: true
related: [DOC-TMP-AI-001]
---

# Move Code Comments to Documentation

## Purpose
Clean up the codebase by moving large, descriptive comments into the official documentation and establishing a strict 1-line comment rule to improve readability and maintainability.

## Context & Motivation
Large block comments often clutter source files, making it difficult to read the actual logic. Detailed explanations of "why" and "how" are better suited for documentation files where they can be properly formatted and indexed. This task aims to enforce a "minimalist comment" policy where code speaks for itself, and complex reasoning is offloaded to the docs.

## Scope & Impact
- **All Applications**: `apps/**`
- **Shared Libraries**: `libs/**`
- **Documentation**: `docs/**`

## Acceptance Criteria
- [ ] Scan the entire codebase for comments exceeding 1 line in length.
- [ ] For each large comment block, extract the information and move it to the most relevant documentation file (e.g., `docs/concepts/`, `docs/how-to/`, or a new `.md` file if appropriate).
- [ ] Link the code to the documentation if the reasoning is particularly complex (e.g., `@see docs/...`).
- [ ] Replace moved comments with a concise 1-line summary only if truly necessary.
- [ ] Ensure all remaining comments in the codebase are no more than 1 line long.
- [ ] No changes to logic or functionality; this is purely a documentation and cleanup task.

## Technical Constraints & References
- **Comment Rule**: No comment should exceed 1 line.
- **Necessity**: Comments should only be used when the code itself cannot be made self-explanatory.
- **Source of Truth**: The `docs/` directory is the primary source of truth for architectural and design decisions.

## Status
- **Current Status**: `Planned`
- **Priority**: `Low`
- **Assignee**: [AI Agent]

## References
- [Backlog Guidelines](../../backlog/GUIDELINES.md)
- [Coding Standards](../../how-to/coding-standards.md)

## Change log
- **2026-04-22**: Downgraded to Low — zero user impact, to be done opportunistically alongside other work.
- **2026-04-22**: Initial task creation.
