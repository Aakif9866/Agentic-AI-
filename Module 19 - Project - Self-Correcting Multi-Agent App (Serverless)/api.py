"""FastAPI wrapper — same shape as Module 9's api.py.

    uv run uvicorn api:app --reload
    curl -X POST localhost:8000/generate -H 'Content-Type: application/json' \
         -d '{"topic":"why reducers matter","max_iteration":3}'

Not streamed, unlike Module 9: a writer/reviewer loop has nothing useful to
show until the reviewer approves, so the client waits for the finished draft.
"""
from fastapi import FastAPI
from pydantic import BaseModel, Field

from graph import MAX_WORDS, generate

app = FastAPI(title="Self-Correcting Writer")


class GenerateIn(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    max_iteration: int = Field(default=3, ge=1, le=5)


@app.post("/generate")
def generate_endpoint(body: GenerateIn):
    out = generate(body.topic, max_iteration=body.max_iteration)
    return {
        "topic": body.topic,
        "draft": out["draft"],
        "verdict": out["verdict"],
        "iterations": out["iteration"],
        "word_count": out["word_count"],
        "word_limit": MAX_WORDS,
        "buzzwords_found": out["banned_found"],
        "drafts_produced": len(out["drafts"]),
        # If verdict is needs_revision, the cap was hit — the client should know
        # it's reading the best attempt rather than an approved one.
        "hit_cap": out["verdict"] != "approved",
    }


@app.get("/health")
def health():
    return {"ok": True}
