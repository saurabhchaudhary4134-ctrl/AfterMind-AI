# AfterMind AI — API service Dockerfile
# Multi-stage build: builder installs deps, runtime is lean
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY services/api/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]" || \
    pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings \
        sqlalchemy alembic bcrypt pyjwt python-multipart email-validator simpleeval \
        numpy scipy pandas scikit-learn celery redis httpx passlib

# ── Runtime stage ──────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd -r aftermind && useradd -r -g aftermind aftermind

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY services/api/ .

# Ensure non-root ownership
RUN chown -R aftermind:aftermind /app

USER aftermind

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
