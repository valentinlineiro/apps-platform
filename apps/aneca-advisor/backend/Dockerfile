FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY static/ static/
COPY domain/ domain/
COPY application/ application/
COPY ports/ ports/
COPY adapters/ adapters/
COPY infrastructure/ infrastructure/
EXPOSE 5001
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "120"]
