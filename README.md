# apps-platform

Nx 22 monorepo for a multi-tenant app platform. Contains four Angular 21 applications, three Python Flask backends, and a shared Python SDK.

## Repository structure

```
apps-platform/
├── apps/
│   ├── portal/                  # Angular PWA + Flask backend
│   ├── exam-corrector/          # Angular Element + Flask backend
│   ├── aneca-advisor/           # Angular Element + Flask backend
│   └── attendance-checker/      # Angular Element (frontend only)
├── libs/
│   └── apps-platform-sdk/       # Shared Python library
├── docs/                        # Platform documentation
├── docker-compose.yml           # Local development stack
├── docker-compose.prod.yml      # Production stack
├── Caddyfile                    # Reverse proxy config
└── nx.json                      # Nx workspace config
```

## Projects

| Nx project | Type | Dev URL |
|---|---|---|
| `portal` | Angular SPA + Flask backend | `https://localhost` (via Caddy) |
| `exam-corrector` | Angular Element + Flask backend | internal only |
| `aneca-advisor` | Angular Element + Flask backend | internal only |
| `attendance-checker` | Angular Element | internal only |
| `apps-platform-sdk` | Python library | — |

### Service ports (docker compose)

| Service | Internal port | Exposed externally |
|---|---|---|
| Caddy | 80 / 443 | `:80` / `:443` |
| portal (nginx) | 80 | via Caddy |
| portal-backend (Flask) | 5000 | internal only |
| exam-corrector-backend | 8000 | internal only |
| aneca-advisor-backend | 5001 | internal only |
| Postgres | 5432 | internal only |
| Keycloak | 8080 | `https://localhost/keycloak/` |

## Prerequisites

- Docker with Buildx
- Node 20 (for local Angular development)
- Python 3.11 (for local backend development)

## Local startup

```bash
docker compose up --build
```

Access points after startup:

- **Portal**: `https://localhost`
- **Keycloak admin**: `https://localhost/keycloak/admin` (admin / admin)
- **Demo user**: `demo` / `demo123`

Required environment variables (copy `.env.example` if present, or export):

```bash
export GEMINI_API_KEY="your_key"
```

Optional overrides:

```bash
export PORTAL_SESSION_SECRET="change-me"
export OAUTH_CLIENT_ID="portal"
export OAUTH_CLIENT_SECRET="portal-dev-secret"
export OAUTH_REDIRECT_URI="https://localhost/auth/callback"
```

## Angular development servers

Each app manages its own `node_modules`. Install and serve independently:

```bash
# Portal
cd apps/portal && npm install && npm start
# → http://localhost:4200 (proxies API calls to the Docker backend)

# Element apps (build only, served via Flask static)
cd apps/exam-corrector && npm install && npm run build:dev
```

## Python backend development

Use `requirements-dev.txt` for local installs (includes the SDK as an editable install):

```bash
cd apps/portal/backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Nx commands

```bash
# Build a specific project
npx nx run portal:build

# Test a specific project
npx nx run portal:test

# Lint a specific project
npx nx run portal:lint

# Run targets only on projects affected by your changes
npx nx affected -t lint test build
```

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | PR + push to main | `nx affected` lint, test, build; Python backend tests |
| `deploy.yml` | Push to main | Build Docker images → GHCR; deploy to Hetzner |
