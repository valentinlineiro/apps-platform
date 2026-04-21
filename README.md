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
| Postgres | 5432 | `:5432` (migrations/dev) |
| Keycloak | 8080 | `https://localhost/keycloak/` |

## Prerequisites

- Docker with Buildx
- Node 20+ (for local Angular development)
- Python 3.12+ (for local backend development)

## Local startup

```bash
# 1. Start the infrastructure (Postgres, Keycloak, etc.)
docker compose up -d postgres keycloak caddy

# 2. Initialize the monorepo environments
npx nx run-many -t setup

# 3. Start everything
docker compose up --build
```

## Python development

The project uses **isolated virtual environments** for every app. Never install packages into your system Python.

### Environment Setup
```bash
# Initialize all virtual environments
npx nx run-many -t setup
```

### Database Migrations (Alembic)
Migrations run automatically on container startup. To manage them manually:
```bash
# Create a new migration
npx nx run <project>:migration --message="Add user bio"

# Apply migrations
npx nx run <project>:migrate
```

### Testing
```bash
# Run tests for a specific project (uses isolated .venv)
npx nx test <project-name>
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
