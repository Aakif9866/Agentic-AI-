FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Bake the embedding model into the image so the first request isn't slowed by a
# ~90MB download inside a cold container.
RUN uv run --no-sync python -c "\
from langchain_huggingface import HuggingFaceEmbeddings; \
HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')"

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
