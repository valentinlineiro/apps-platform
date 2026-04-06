# Stage 1: Build the Angular web component bundle
FROM node:20-alpine AS element-build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY angular.json tsconfig.json ./
COPY frontend/ frontend/
RUN npx ng build exam-corrector-element

# Stage 2: Python backend
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=element-build /app/backend/static/element/ static/element/
RUN mkdir -p uploads
EXPOSE 8000
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "300"]
