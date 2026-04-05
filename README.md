# vps-root

Un VPS, todas las apps. Nginx enruta por ruta, cada app en su contenedor Docker.

## Arrancar en local

```bash
docker compose up --build
```

- Directorio: http://localhost/
- Exam corrector: http://localhost/exam-corrector/

## Estructura

```
vps-root/
├── docker-compose.yml        # Orquestación central
├── nginx/default.conf        # Routing → contenedores
├── directory/index.html      # Landing con todas las apps
└── apps/
    └── exam-corrector/       # Flask + OpenCV
```

## Añadir una nueva app

1. Crea `apps/nueva-app/` con su `Dockerfile`
2. Añade el servicio en `docker-compose.yml`
3. Añade el bloque `location` en `nginx/default.conf`
4. Añade la card en `directory/index.html`
5. `docker compose up -d --build nueva-app`

## Comandos útiles

```bash
# Estado de todos los contenedores
docker compose ps

# Logs de una app
docker compose logs -f exam-corrector

# Reiniciar solo una app
docker compose restart exam-corrector

# Rebuild solo una app
docker compose up -d --build exam-corrector
```

## Despliegue en Hetzner

```bash
git clone <repo> && cd vps-root
docker compose up -d --build
```
