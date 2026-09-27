# syntax=docker/dockerfile:1
# Backend image (T-M6-001, FR-CTR-001). Every base is pinned to a patch version (FR-CTR-004).
# APP_VERSION is deliberately NOT a build arg: it is a runtime env var (AD-014), so one image
# serves every environment (NFR-PORT-001).

FROM ghcr.io/astral-sh/uv:0.12.19 AS uv

FROM python:3.12.14-slim-bookworm AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Manifests first, source second (NFR-PERF-006): a source-only change reuses this layer.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM python:3.12.14-slim-bookworm AS runtime
RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
# Same base as the builder, so the venv's interpreter symlinks resolve.
COPY --from=builder /app/.venv /app/.venv
# Source stays root-owned and read-only to uid 1000: nothing in the app writes to disk.
COPY alembic.ini ./
COPY alembic ./alembic
COPY seeds ./seeds
COPY app ./app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 1000
EXPOSE 8000
# Liveness only; /ready would gate Compose on the database (07-M6 §2.1). slim has no curl.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
# Exec form: uvicorn is PID 1 and receives SIGTERM (FR-BE-021). Graceful 25 s fits the 30 s
# grace period minus the 5 s preStop (BR-OPS-004). Client IP is resolved in app/client_ip.py
# (AD-054), so uvicorn must not rewrite the peer from proxy headers first.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--timeout-graceful-shutdown", "25", "--no-proxy-headers"]
