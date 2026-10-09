FROM python:3.12-slim

WORKDIR /app

# Install uv, then dependencies only — so this layer is cached and rebuilds stay fast
# when only application code changes.
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
