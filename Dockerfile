# Coach Studio — production image (FastAPI API + the single-page frontend it serves).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

# Install dependencies first (better layer caching). psycopg2-binary needs no
# system build deps.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --timeout 300 --retries 10 -r requirements.txt

# App code (includes app/static with Front.html, the service worker, icons).
COPY backend/ ./

EXPOSE 8000

# Run DB migrations, then serve. $PORT is provided by most hosts (Render, etc.).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
