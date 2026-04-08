# GEMINI.md

This project is a monorepo-style platform orchestrator for a suite of integrated applications (Portal, Exam Corrector, Attendance Checker). It uses **Nx** for workspace management, Git submodules to manage application source code, and Docker Compose for local development and orchestration.

## Project Overview

*   **Type:** Monorepo Orchestrator (Nx Workspace).
*   **Main Technologies:** 
    *   **Orchestrator:** Nx (Task running, dependency management).
    *   **Frontend:** Angular 21 (Web Components / Angular Elements).
    *   **Backend:** Flask (Python).
    *   **Libraries:** Python SDK (Shared registration and observability logic).
    *   **Infrastructure:** Docker, Docker Compose, Caddy (Ingress).
    *   **Auth:** Keycloak (OIDC/OAuth2 with PKCE).
    *   **Database:** PostgreSQL (Keycloak/Portal), SQLite (Registry).
    *   **AI:** Gemini Vision API (for Exam Corrector).

## Building and Running

### Prerequisites
*   Node.js and npm (for Nx).
*   Git, Docker, and Docker Compose.
*   A Gemini API Key (for `exam-corrector`).

### Setup and Local Execution
1.  **Clone with submodules:**
    ```bash
    git clone --recurse-submodules <REPO_URL>
    ```
    If already cloned without submodules:
    ```bash
    git submodule update --init --recursive
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Environment Setup:**
    ```bash
    export GEMINI_API_KEY="your_api_key"
    ```
4.  **Start the platform:**
    ```bash
    docker compose up --build
    ```

### Running Tasks with Nx
Use Nx to run tasks across projects:
```bash
# Build a specific app
npx nx build portal

# Run tests for the Python SDK
npx nx test platform-python-sdk

# Build all projects
npx nx run-many -t build
```

### Accessing Services
*   **Portal:** `http://localhost:4200`
*   **Keycloak (Auth):** `http://localhost:8081` (Admin: `admin` / `admin`)
*   **Default Demo User:** `demo` / `demo123`

## Architecture

The platform follows a **"Heartbeat Registry"** model:
1.  **App Backends** register themselves with the `portal-backend` at startup (`POST /api/registry/register`).
2.  Apps send a **heartbeat** every 30 seconds (`POST /api/registry/heartbeat/<app_id>`).
3.  Static or frontend-only apps are registered via `apps/portal/backend/static_apps.json`.
4.  The **Portal Frontend** dynamically loads apps as Web Components based on the registry.

### Project Locations
*   `apps/portal/`: The central hub (Angular frontend) and auth/registry manager (Flask backend).
*   `apps/exam-corrector/`: Gemini-powered exam analyzer (Frontend & Backend).
*   `apps/attendance-checker/`: Attendance tracking application (Frontend only).
*   `libs/platform-python-sdk/`: Shared Python library for registry integration and observability.

## Development Conventions

*   **Adding New Apps:** Use the `./scaffold-app.sh` script to create a new app structure and automatically patch the necessary configuration files.
    ```bash
    ./scaffold-app.sh <app-id> "<App Name>" "<Description>" [icon]
    ```
*   **Manifests:** Every app must expose a manifest providing its name, description, icon, route, and entry script. For Python apps, use the `platform-python-sdk` for automatic registration.
*   **Routing:** 
    *   In production/compose, Caddy and Nginx (in `portal`) handle path-based routing.
    *   In development, `apps/portal/proxy.conf.json` maps local backend routes.
*   **Code Style:**
    *   **Angular:** Standalone components, signals, and zoneless change detection.
    *   **Flask:** Blueprint-based routing and use of `platform-python-sdk` for registration.

## Key Files
*   `nx.json`: Nx workspace configuration.
*   `package.json`: Project dependencies and Nx scripts.
*   `docker-compose.yml`: Main orchestration file for all services.
*   `Caddyfile`: Ingress configuration for external access.
*   `scaffold-app.sh`: Transition utility for generating new apps.
*   `CLAUDE.md`: Comprehensive guide for AI assistants (detailed architecture).
*   `.gitmodules`: Defines the submodule-based structure.
