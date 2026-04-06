# Stage 1: Build the Angular web component bundle
FROM node:20-alpine AS element-build
WORKDIR /app
COPY package.json ./
COPY apps/portal/package.json apps/portal/package.json
COPY apps/exam-corrector/frontend/package.json apps/exam-corrector/frontend/package.json
RUN npm install
COPY apps/portal/ apps/portal/
COPY apps/exam-corrector/frontend/ apps/exam-corrector/frontend/
WORKDIR /app/apps/portal
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
COPY apps/exam-corrector/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/exam-corrector/backend/ .
COPY --from=element-build /app/apps/exam-corrector/backend/static/element/ static/element/
RUN mkdir -p uploads
EXPOSE 8000
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "300"]
