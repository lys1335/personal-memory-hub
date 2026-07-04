# Personal Memory Hub — Dockerfile
#
# Multi-stage build for the Python application.
# Stage 1: Build (install dependencies)
# Stage 2: Runtime (minimal image, copy built dependencies)

# ---------------------------------------------------------------------------
# Stage 1: Build
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy project configuration
COPY pyproject.toml README.md ./

# Install dependencies (excluding dev extras for smaller image)
RUN uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy dependencies from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application source
COPY src/ ./src/
COPY scripts/ ./scripts/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Switch to non-root user
USER appuser

# Expose application port (D5+ when API layer is implemented)
# EXPOSE 8000

# Health check (placeholder — actual endpoint added in D5+)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from backend.shared.infrastructure.config.settings import get_settings; print(get_settings().APP_NAME)" || exit 1

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "-m", "backend.cli"]
