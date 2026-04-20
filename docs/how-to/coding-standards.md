---
id: DOC-HT-001
title: Coding Standards & Conventions
audience: [human, ai]
last_updated: 2026-04-17
tags: [how-to, conventions, standards, angular, python, flask]
source_of_truth: true
related: [DOC-QS-001, DOC-CON-001]
---

# Coding Standards & Conventions

## Purpose
Define the mandatory coding standards and patterns to ensure consistency across the monorepo.

## When to use
Apply these conventions whenever writing new code or refactoring existing components in the Portal or individual apps.

## Content

### Angular Frontend (v21)
All components use **separate files** for templates and styles. Never use inline `template` or `styles` in the `@Component` decorator.

```typescript
@Component({
  selector: 'app-my-component',
  templateUrl: './my-component.component.html',   // ✅
  styleUrl: './my-component.component.css',        // ✅
})
```
- **Standards**: Standalone components, Signals, Zoneless change detection.
- **Micro-frontends**: Each app is bundled as an Angular Element.

### Python Backend (Flask 3)
All backends must use the `apps-platform-sdk` for shared logic.

#### 1. Registration & Heartbeat
Apps self-register at startup via `start_registration(manifest)`.
```python
from apps_platform_sdk import start_registration

manifest = { ... }
start_registration(manifest)
```

#### 2. Observability & Logging
Backends must use structured JSON logging.
```python
from apps_platform_sdk.observability import setup_logging, log_exception

setup_logging(app)
log_exception("Something went wrong")
```

#### 3. File Handling
Backend uploads should be persisted via Docker volumes (e.g., `exam_corrector_uploads`).

## References
- [System Architecture](../concepts/architecture.md)
- [Quickstart Guide](../quickstart/setup.md)

## Change log
- **2026-04-17**: Initial version moved to `how-to/` and standardized.
