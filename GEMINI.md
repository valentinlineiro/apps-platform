# GEMINI.md

This project is a monorepo-style platform orchestrator for a suite of integrated applications (**Portal**, **Exam Corrector**, **Attendance Checker**). It uses **Nx** for workspace management, Git submodules for app source code, and Docker Compose for orchestration.

## 🚀 Project Overview

*   **Type:** Monorepo Orchestrator (Nx Workspace).
*   **Main Technologies:** 
    *   **Orchestrator:** Nx (Task running, dependency management).
    *   **Frontend:** Angular 21 (Standalone, Signals, Zoneless) using **Web Components / Angular Elements** for MFEs.
    *   **Backend:** Flask 3 (Python) with Blueprint-based routing.
    *   **Libraries:** `platform-python-sdk` (Shared registration and observability logic).
    *   **Infrastructure:** Docker, Caddy 2.7 (TLS/Ingress), Keycloak 26.2.2 (Auth), PostgreSQL 16.
    *   **AI:** Gemini Vision API (integration in `exam-corrector`).

## 🏗️ Architecture

The platform follows a **"Heartbeat Registry"** model for dynamic service discovery and frontend composition.

### Traffic Flow
**Browser** → **Caddy** (TLS termination for `localhost`) → **Portal Nginx** → **App Backends** (Proxied and Auth-gated).

### Heartbeat Registry
1.  **App Backends** register themselves with the `portal-backend` at startup (`POST /api/registry/register`).
2.  Apps send a **heartbeat** every 30 seconds (`POST /api/registry/heartbeat/<app_id>`).
3.  The `portal-backend` evicts apps missing heartbeats (default TTL: 60s).
4.  **Portal Frontend** fetches the active registry and dynamically loads apps as Web Components via `MicroFrontendLoaderComponent`.

### Key Components
*   `apps/portal/`: Central hub.
    *   **Frontend:** Angular 21 shell that loads micro-frontends.
    *   **Backend:** Flask API for registry management and OIDC/OAuth2 auth.
*   `apps/exam-corrector/`: AI-powered OMR (Optical Mark Recognition).
    *   **Backend:** OpenCV pipeline for async/batch exam correction.
*   `apps/attendance-checker/`: Attendance tracking (WIP).
    *   **Frontend:** Currently a placeholder Angular component.
    *   **Backend:** Planned (not yet implemented).
*   `libs/platform-python-sdk/`: Shared logic for:
    *   **Registration:** Automatic portal registration and heartbeat loop.
    *   **Observability:** JSON structured logging with request tracking and timing.

## 🛠️ Development Workflow

### Prerequisites
*   Node.js (for Nx).
*   Docker & Docker Compose.
*   Gemini API Key (for `exam-corrector`).

### Setup and Execution
```bash
# Clone with submodules
git clone --recurse-submodules <REPO_URL>

# Start everything
export GEMINI_API_KEY="your_api_key"
docker compose up --build
```

### Local Access & Credentials
*   **Portal:** `https://localhost`
*   **Keycloak Admin:** `https://localhost/admin` (admin/admin)
*   **Demo User:** `demo` / `demo123`

### Scaffolding New Apps
Use the provided script to generate a new app with frontend (Angular Element) and backend (Flask) boilerplate, automatically patching Nginx and Docker configurations:
```bash
./scaffold-app.sh <app-id> "<App Name>" "<Description>" [icon]
```

### Running Tasks (Nx)
```bash
# Build/Test specific projects
npx nx build portal
npx nx test platform-python-sdk

# Run many
npx nx run-many -t build
```

## 🔐 Auth & Security

*   **Provider:** Keycloak (OIDC/OAuth2 with PKCE).
*   **Roles:** `owner`, `admin`, `member` (default), `viewer`.
*   **Nginx Auth:** Internal subrequests (`/_auth`) gate access to app backend routes via `auth_request` module.

## 🤖 Agents & Skills

This repository is optimized for **Gemini CLI** and contains custom agentic capabilities:

*   **Custom Skills:** Located in `.agents/skills/` (Nx-related, linking packages, CI monitoring).
*   **CI Subagent:** `.github/agents/ci-monitor-subagent.agent.md` for self-healing CI pipelines.

## 🧪 Testing

*   **Python Backends:** Run `pytest` within the app's backend directory.
*   **Frontend:** Use `npx nx test <project-name>`.

## 📂 Key Files
*   `CLAUDE.md`: Detailed architectural deep-dive for AI assistants.
*   `Caddyfile`: Ingress and TLS configuration.
*   `docker-compose.yml`: Main orchestration file.
*   `apps/portal/nginx.conf`: Internal routing and auth-gating logic.
