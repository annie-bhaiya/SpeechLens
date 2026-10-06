FROM node:24.18.0-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 SPEECHLENS_STORAGE=/app/storage HF_HUB_DISABLE_TELEMETRY=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 g++ && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.23
COPY pyproject.toml uv.lock ./
COPY backend/ backend/
COPY scripts/ scripts/
RUN uv sync --frozen --no-dev
COPY configs/ configs/
COPY data/ data/
COPY evaluation/recording_scores.json evaluation/metrics.json evaluation/robustness.json evaluation/
COPY --from=frontend /build/frontend/dist frontend/dist
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["/app/.venv/bin/python","-m","uvicorn","backend.app.api:app","--host","0.0.0.0","--port","8000"]
