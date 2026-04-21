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

#### 1. Environment Isolation (Mandatory)
Every Python app and library MUST have its own virtual environment in a local `.venv` directory. 
- **Setup**: Run `npx nx run <project>:setup` to create and populate the `.venv`.
- **Execution**: Always use `.venv/bin/python3` or `.venv/bin/pip`. Never install packages into the system Python.
- **Project Structure**: Use the provided `scaffold-app.sh` script to ensure the correct layout.

#### 2. Declarative Catalog & Manifest
Apps no longer use heartbeat threads for registration. Instead:
- **Manifest**: Every app MUST expose its manifest at `GET /apps/<app-id>/manifest.json` or as configured in `portal-backend`.
- **Static Registry**: New apps must be added to `apps/portal/backend/static_apps.json` for discovery.

#### 3. Observability & Logging
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
- **2026-04-21**: Transitioned from Heartbeat Registry to Declarative Catalog; added mandatory Python venv isolation.
- **2026-04-17**: Initial version moved to `how-to/` and standardized.
