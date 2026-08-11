# Personal Memory Hub — Dockerfile
# Build context: project root (.)

# ---------------------------------------------------------------------------
# Stage 1: Build dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/README.md backend/uv.lock ./
RUN uv sync --frozen --no-dev --all-extras

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /build/.venv /app/.venv
COPY backend/src/ ./src/
COPY backend/scripts/start.sh ./scripts/start.sh
COPY backend/dashboard-main.html ./dashboard-main.html
RUN chmod +x ./scripts/start.sh

# Clear any existing bytecode cache to prevent stale .pyc issues
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser

# HEALTHCHECK removed for now - use compose-level healthcheck instead
# HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
#     CMD python -c "from backend.shared.infrastructure.config.settings import get_settings; print(get_settings().NAME)" || exit 1

CMD ["python", "-m", "backend.app"]
