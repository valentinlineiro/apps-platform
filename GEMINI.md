# GEMINI.md

This project is a monorepo-style platform orchestrator for a suite of integrated applications (Portal, Exam Corrector, Attendance Checker). It uses Git submodules to manage each application's source code and Docker Compose for local development and orchestration.

## Project Overview

*   **Type:** Monorepo Orchestrator (Code Project).
*   **Main Technologies:** 
    *   **Frontend:** Angular 21 (Web Components / Angular Elements).
    *   **Backend:** Flask (Python).
    *   **Infrastucture:** Docker, Docker Compose, Caddy (Ingress).
    *   **Auth:** Keycloak (OIDC/OAuth2 with PKCE).
    *   **Database:** PostgreSQL (Keycloak/Portal), SQLite (Registry).
    *   **AI:** Gemini Vision API (for Exam Corrector).

## Building and Running

### Prerequisites
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
2.  **Environment Setup:**
    ```bash
    export GEMINI_API_KEY="your_api_key"
    ```
3.  **Start the platform:**
    ```bash
    docker compose up --build
    ```

### Accessing Services
*   **Portal:** `http://localhost:4200`
*   **Keycloak (Auth):** `http://localhost:8081` (Admin: `admin` / `admin`)
*   **Default Demo User:** `demo` / `demo123`

## Architecture

The platform follows a **"Heartbeat Registry"** model:
1.  **App Backends** register themselves with the `portal-backend` at startup (`POST /api/registry/register`).
2.  Apps send a **heartbeat** every 30 seconds (`POST /api/registry/heartbeat/<app_id>`).
3.  The **Portal Frontend** dynamically loads apps as Web Components based on the registry.

### App Locations
*   `apps/portal/`: The central hub and auth manager.
*   `apps/exam-corrector/`: Gemini-powered exam analyzer.
*   `apps/attendance-checker/`: Attendance tracking application.

## Development Conventions

*   **Adding New Apps:** Use the `./scaffold-app.sh` script to create a new app structure and automatically patch the necessary configuration files.
    ```bash
    ./scaffold-app.sh <app-id> "<App Name>" "<Description>" [icon]
    ```
*   **Manifests:** Every app must expose a `manifest.json` file providing its name, description, icon, route, and entry script.
*   **Routing:** 
    *   In production/compose, Caddy and Nginx (in `portal`) handle path-based routing.
    *   In development, `apps/portal/proxy.conf.json` maps local backend routes.
*   **Code Style:**
    *   **Angular:** Standalone components, signals, and zoneless change detection.
    *   **Flask:** Blueprint-based routing and a standard `registration_service.py` for heartbeat.

## Key Files
*   `docker-compose.yml`: Main orchestration file for all services.
*   `Caddyfile`: Ingress configuration for external access.
*   `scaffold-app.sh`: Transition utility for generating new apps.
*   `CLAUDE.md`: Comprehensive guide for AI assistants (detailed architecture).
*   `.gitmodules`: Defines the submodule-based structure.
