FROM astral/uv:0.9.2-python3.14-alpine AS builder

RUN apk add --no-cache \
    build-base \
    python3-dev \
    librdkafka-dev

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

FROM astral/uv:0.9.2-python3.14-alpine

RUN apk add --no-cache postgresql-client

RUN addgroup -g 1000 appgroup && \
    adduser -D -u 1000 -G appgroup appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

COPY --chown=appuser:appgroup . /app

USER appuser

CMD ["sh", "-c", "uv run alembic stamp base && uv run alembic upgrade head && uv run python -m bin.main"]