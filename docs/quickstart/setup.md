---
id: DOC-QS-001
title: Project Setup & Execution
audience: [human, ai]
last_updated: 2026-04-17
tags: [setup, quickstart, development, nx, docker]
source_of_truth: true
related: [DOC-CON-001, DOC-HT-001]
---

# Project Setup & Execution

## Purpose
Provide a 5-minute guide to getting the monorepo up and running for local development.

## When to use
Follow this guide during initial machine setup or when onboarding a new developer to the project.

## Content

### Prerequisites
- Node.js (for Nx)
- Docker & Docker Compose
- Gemini API Key (for `exam-corrector`)

### Start Everything
```bash
# Clone with submodules
git clone --recurse-submodules <REPO_URL>

# Start everything
export GEMINI_API_KEY="your_api_key"
docker compose up --build
```

### Local Access
- **Portal:** `https://localhost`
- **Keycloak Admin:** `https://localhost/admin` (admin/admin)
- **Demo User:** `demo` / `demo123`

### Scaffolding New Apps
Use the provided script to generate a new app with frontend (Angular Element) and backend (Flask) boilerplate:
```bash
./scaffold-app.sh <app-id> "<App Name>" "<Description>" [icon]
```

### Running Tasks (Nx)
Prefer running tasks through Nx rather than underlying tools:
```bash
# Build/Test specific projects
npx nx build portal
npx nx test apps-platform-sdk

# Run many
npx nx run-many -t build
```

### Testing
- **Python Backends**: Run `pytest` within the app's backend directory.
- **Frontend**: Use `npx nx test <project-name>`.

## References
- [Coding Standards](../how-to/coding-standards.md)
- [System Architecture](../concepts/architecture.md)

## Change log
- **2026-04-17**: Combined development workflow into a consolidated quickstart guide.
