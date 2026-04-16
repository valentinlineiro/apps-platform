# Parent Repo Model

Este repositorio es el "father repo" del ecosistema.

## Objetivo

Separar cada producto en su propio repositorio, manteniendo aquí solo:

- Orquestación local (`docker-compose.yml`)
- Documentación de arquitectura
- Scripts de apoyo/transición

## Repos destino

- `portal`
- `exam-corrector`
- `attendance-checker`

## Estado aplicado

`apps/` ya fue reemplazado por submódulos git:

- `apps/portal` -> `../portal`
- `apps/exam-corrector` -> `../exam-corrector`
- `apps/attendance-checker` -> `../attendance-checker`

## Flujo recomendado

1. Actualizar submódulos al último `main`:
   - `git submodule update --remote --merge`
2. Commit en repo padre para fijar nuevos SHAs de submódulos.
3. En CI/CD, clonar siempre con `--recurse-submodules`.

## Nota sobre scaffold

`scaffold-app.sh` sigue creando apps dentro de `apps/` para facilitar la transición.
Para el modelo definitivo multi-repo, conviene mover este script a una plantilla o generador externo.
