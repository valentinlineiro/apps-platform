FROM python:3.11-slim
WORKDIR /app
COPY apps/portal/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY libs/platform-python-sdk/ /libs/platform-python-sdk/
COPY libs/backend-core/ /libs/backend-core/
RUN pip install --no-cache-dir /libs/platform-python-sdk /libs/backend-core
COPY apps/portal/backend/app.py .
COPY apps/portal/backend/static_apps.json .
COPY apps/portal/backend/postgres/ postgres/
COPY apps/portal/backend/keycloak/ keycloak/
COPY apps/portal/backend/domain/ domain/
COPY apps/portal/backend/application/ application/
COPY apps/portal/backend/ports/ ports/
COPY apps/portal/backend/adapters/ adapters/
EXPOSE 5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120"]
