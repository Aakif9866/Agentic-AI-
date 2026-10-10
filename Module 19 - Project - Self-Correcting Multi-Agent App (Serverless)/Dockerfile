FROM python:3.12-slim

WORKDIR /app

# Dependencies before code, so editing graph.py doesn't reinstall the tree.
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Render/Lambda inject their own PORT — don't hardcode it.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
