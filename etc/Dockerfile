# Stage 1: Build the dashboard (Vite + React SPA)
FROM node:22-slim AS dashboard-builder

WORKDIR /app

COPY packages/dashboard/package.json packages/dashboard/package-lock.json ./
RUN npm ci

COPY packages/dashboard/ ./
# Build with same-origin API URL so the bundled dashboard works out-of-the-box.
RUN FE_API_BASE_URL=/api/v1 npm run build


# Stage 2: Build the Python virtual environment
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT="/opt/venv" \
    UV_COMPILE_BYTECODE=1

COPY uv.lock packages/api/pyproject.toml ./
COPY packages/api/pyproject.toml ./packages/api/pyproject.toml
COPY packages/api/README.md ./packages/api/README.md
COPY packages/api/forkflux_api ./packages/api/forkflux_api
RUN uv sync --frozen


# Stage 3: Runtime
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
# for alembic
COPY packages/api/pyproject.toml ./packages/api/pyproject.toml
COPY packages/api/forkflux_api /app/packages/api/forkflux_api
# Copy built dashboard static files into the Python package
COPY --from=dashboard-builder /app/dist /app/packages/api/forkflux_api/static

RUN chown -R appuser:appuser /app /opt/venv

USER appuser

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "packages.api.forkflux_api.main:app"]
