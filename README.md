# apps-platform

Repositorio padre (orquestador) para el ecosistema de aplicaciones:

- `portal`
- `exam-corrector`
- `attendance-checker`

Este repo mantiene coordinación local y operativa compartida (compose, documentación y utilidades de transición).

## Estado actual

Las apps se gestionan como submódulos git bajo `apps/`.

## Clonado

```bash
git clone --recurse-submodules <APPS_PLATFORM_REPO_URL>
```

Si ya clonaste sin submódulos:

```bash
git submodule update --init --recursive
```

Para traer últimos cambios de submódulos:

```bash
git submodule update --remote --merge
```

## Arrancar en local

```bash
export GEMINI_API_KEY="tu_api_key"
docker compose up --build
```

- Portal frontend: `http://localhost:4200`
- Portal backend: `http://localhost:5000` (interno por compose)
- Exam-corrector backend: `http://localhost:8000` (interno por compose)

## Estructura

```text
apps-platform/
├── docker-compose.yml
├── scaffold-app.sh
├── PARENT_REPO.md
└── apps/  # submódulos git
    ├── portal/
    ├── exam-corrector/
    └── attendance-checker/
```
