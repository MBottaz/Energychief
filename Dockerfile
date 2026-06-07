FROM python:3.14-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# ── Runtime image ──
FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY alembic/           alembic/
COPY alembic.ini        .
COPY shared/            shared/
COPY frontend/          frontend/
COPY backend/           backend/
COPY webhook/           webhook/
COPY app.py             .
COPY recs_data.csv      .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port 8000"]