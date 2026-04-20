# Stage 1: Build the Angular web component bundle
FROM node:20-alpine AS element-build
WORKDIR /app
COPY apps/aneca-advisor/package.json ./
RUN npm install
COPY apps/aneca-advisor/angular.json apps/aneca-advisor/tsconfig.json ./
COPY apps/aneca-advisor/frontend/ frontend/
RUN npx ng build aneca-advisor-element

# Stage 2: Python backend
FROM python:3.11-slim
WORKDIR /app
COPY libs/apps-platform-sdk/ /libs/apps-platform-sdk/
COPY apps/aneca-advisor/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/aneca-advisor/backend/ .
COPY --from=element-build /app/backend/static/element/ static/element/
EXPOSE 5001
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "120"]
