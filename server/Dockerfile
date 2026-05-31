FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv venv .venv && uv pip install --python .venv/bin/python -e . --no-editable 2>/dev/null || uv pip install --python .venv/bin/python .

FROM python:3.11-slim

WORKDIR /app

RUN mkdir -p /app/data

COPY --from=builder /app/.venv /app/.venv
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

ENV PATH="/app/.venv/bin:$PATH"
ENV DATABASE_URL="sqlite+aiosqlite:////app/data/cheat_buster.db"

EXPOSE 8000

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
