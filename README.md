# Exam Corrector

Arquitectura separada en dos apps:

- `apps/backend`: API Python (Flask) que corrige exámenes.
- `apps/frontend`: Angular PWA que consume la API.

## Arrancar en local

```bash
export GEMINI_API_KEY="tu_api_key"
docker compose up --build
```

- Frontend Angular PWA: `http://localhost:4200`
- Backend API: `http://localhost:8000`

## Estructura

```
exam-corrector/
├── docker-compose.yml
└── apps/
    ├── backend/   # Flask + Gemini + reglas + plantillas
    └── frontend/  # Angular PWA
```
