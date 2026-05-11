# Runtime image for the SHL recommender API (no scraping at serve time).
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY app ./app
COPY scripts ./scripts
COPY data ./data

# Precompute embedding index when catalog JSON is present (semantic retrieval at runtime).
RUN python scripts/build_embedding_index.py || true

EXPOSE 8000

# Render/Fly/Railway set PORT; default 8000 for local docker run.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
