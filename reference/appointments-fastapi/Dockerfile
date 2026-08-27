FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /workspace

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml uv.lock ./
COPY reference/inventory-django/pyproject.toml reference/inventory-django/pyproject.toml
COPY reference/appointments-fastapi/pyproject.toml reference/appointments-fastapi/pyproject.toml
COPY contract-tests/pyproject.toml contract-tests/pyproject.toml
RUN uv sync \
    --frozen \
    --no-dev \
    --package appointments-fastapi \
    --no-install-workspace \
    --compile-bytecode

COPY reference/appointments-fastapi reference/appointments-fastapi
RUN chown -R app:app /workspace/reference/appointments-fastapi

WORKDIR /workspace/reference/appointments-fastapi

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

FROM runtime AS test

USER root

RUN uv sync \
    --frozen \
    --package appointments-fastapi \
    --no-install-workspace \
    --compile-bytecode

USER app

CMD ["pytest", "-ra"]
