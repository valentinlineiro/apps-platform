---
id: DOC-CON-003
title: Parent Repository Model
audience: [human, ai]
last_updated: 2026-04-17
tags: [architecture, monorepo, submodules, orchestration]
source_of_truth: true
related: [DOC-CON-001]
---

# Parent Repository Model

## Purpose
This document explains the "Father Repo" strategy used for local orchestration and development across multiple product repositories.

## When to use
Consult this when managing git submodules or understanding how the platform is decoupled into individual service repos.

## Content

### Objective
Separate each product into its own repository while maintaining a central point for:
- Local orchestration (`docker-compose.yml`)
- Architectural documentation
- Supporting/transition scripts

### Repository Targets
- `portal`
- `exam-corrector`
- `attendance-checker`

### Current Implementation
The `apps/` directory has been replaced by git submodules:
- `apps/portal` -> `../portal`
- `apps/exam-corrector` -> `../exam-corrector`
- `apps/attendance-checker` -> `../attendance-checker`

### Recommended Workflow
1. **Update submodules** to the latest `main`:
   ```bash
   git submodule update --remote --merge
   ```
2. **Commit in the parent repo** to pin new submodule SHAs.
3. **CI/CD**: Always clone with `--recurse-submodules`.

### Note on Scaffolding
The `scaffold-app.sh` script currently creates apps directly within `apps/` to facilitate the transition. In the final multi-repo model, this script should be moved to an external template or generator.

## References
- [System Architecture](architecture.md)
- [Project Setup](../quickstart/setup.md)

## Change log
- **2026-04-17**: Translated from Spanish to English and standardized metadata.
