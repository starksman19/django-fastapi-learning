FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY reference/inventory-django/pyproject.toml reference/inventory-django/pyproject.toml
COPY reference/appointments-fastapi/pyproject.toml reference/appointments-fastapi/pyproject.toml
COPY contract-tests/pyproject.toml contract-tests/pyproject.toml
RUN uv sync \
    --frozen \
    --no-dev \
    --package contract-tests \
    --no-install-workspace \
    --compile-bytecode

COPY contract-tests contract-tests

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /workspace/contract-tests

WORKDIR /workspace/contract-tests

USER app

CMD ["pytest", "-ra"]
