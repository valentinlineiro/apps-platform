# Stage 1: Build the Angular web component bundle
FROM node:20-alpine AS element-build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY angular.json tsconfig.json ./
COPY frontend/ frontend/
RUN npx ng build aneca-advisor-element

# Stage 2: Python backend
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=element-build /app/backend/static/element/ static/element/
EXPOSE 5001
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "120"]
