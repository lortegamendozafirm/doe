FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tu monolito, la API y los JSON (rápido, no ideal)
COPY doe_monolith.py endpoint_app.py ./
COPY client_secret_*.json service_account.json ./
COPY token_drive.json ./

CMD ["uvicorn", "endpoint_app:app", "--host", "0.0.0.0", "--port", "8080"]
