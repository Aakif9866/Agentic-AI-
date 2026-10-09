# Module 9 — Deployment (Docker, CI/CD, Render)

Taking the Module 6 chatbot off your laptop and putting it behind a real HTTP API in a container.

## Run it locally

```bash
uv sync
uv run uvicorn api:app --reload

curl localhost:8000/health
curl -N -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"thread_id":"t1","message":"hi"}'
```

`-N` disables curl's buffering so you see tokens arrive one at a time.

---

## 1. `backend.py` — the graph, with zero web code in it

The whole point of this file is what it **doesn't** import: no FastAPI, no HTTP.

```python
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
agent = graph.compile(checkpointer=SqliteSaver(conn))
```

Why split it out:

- You can `from backend import agent` in a test, a script, or a Streamlit app without starting a server.
- You can replace FastAPI with something else and never touch the graph.
- `CHECKPOINT_DB` is read from the environment, so the database path is configurable at deploy time instead of hardcoded.

**Takeaway:** keep the agent and the transport in separate files. Every later module reuses this shape.

---

## 2. `api.py` — FastAPI with a streaming endpoint

```python
@app.post("/chat")
def chat(body: ChatIn):
    cfg = {"configurable": {"thread_id": body.thread_id}}

    def token_stream():
        for chunk, _meta in agent.stream({"messages": [("user", body.message)]},
                                         cfg, stream_mode="messages"):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content

    return StreamingResponse(token_stream(), media_type="text/plain")
```

The pieces:

- **`StreamingResponse` + a generator** — this is Module 6's `stream_mode="messages"` wired to HTTP. The client gets text as it's produced instead of waiting for the full answer.
- **`thread_id` comes from the request** — so the client controls which conversation it's in. Same `thread_id` = continued conversation, courtesy of the checkpointer.
- **`ChatIn(BaseModel)`** — Pydantic validates the body and rejects malformed requests before your code runs.
- **`/health`** — a trivial endpoint that Render and CI poll to decide whether the app is alive. Every deployed service needs one.

**Verified working:** `/health` returns `{"ok":true}`, `/chat` streams, and asking a follow-up on the same `thread_id` correctly recalls the previous turn.

---

## 3. `Dockerfile` — layer order is the whole trick

```dockerfile
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./      # dependencies FIRST
RUN uv sync --frozen --no-dev
COPY . .                            # your code LAST
```

**Why dependencies before code:** Docker caches each layer and rebuilds from the first change downward. Dependencies change rarely, your code changes constantly. In this order, editing `api.py` reuses the cached dependency layer and rebuilds in seconds. Copy everything first and every rebuild reinstalls the whole dependency tree.

- `--frozen` installs exactly what `uv.lock` pins — the container gets the same versions you tested.
- `--no-dev` skips test/lint tooling you don't need in production.
- `${PORT}` with a default — Render injects its own `PORT`, so don't hardcode 8000.

---

## 4. `.dockerignore` — keep secrets and junk out of the image

```
.venv/
__pycache__/
.env          <-- the important one
chatbot.db
.git/
```

**Never bake `.env` into an image.** Anyone who pulls the image can read it, and images get pushed to registries. Set secrets as environment variables in the host (Render dashboard, GitHub Actions secrets).

Excluding `.venv/` also matters practically: your local venv holds macOS binaries that would break inside a Linux container.

---

## 5. `.github/workflows/deploy.yml` — CI that proves the image boots

The job builds the image, runs it, and polls `/health` until it answers:

```yaml
- run: docker build -t agentic-chatbot:ci .
- run: |
    docker run -d -p 8000:8000 -e GROQ_API_KEY=${{ secrets.GROQ_API_KEY }} --name app agentic-chatbot:ci
    for i in $(seq 1 15); do curl -sf localhost:8000/health && break; sleep 2; done
    curl -sf http://localhost:8000/health
```

A retry loop beats a fixed `sleep 5` — containers don't boot in a predictable time, and a fixed sleep either wastes time or fails randomly.

**Two things to know:**

1. **GitHub only runs workflows at the repository root**, in `.github/workflows/`. This copy lives inside the module as study material. To actually run it, move it to the repo root (the `working-directory` is already set for that).
2. `${{ secrets.GROQ_API_KEY }}` reads from GitHub repo settings → Secrets. Never put the key in the YAML.

---

## Deploying to Render (free tier)

1. Push to GitHub.
2. Render → **New → Web Service** → connect the repo. It detects the `Dockerfile`.
3. Add `GROQ_API_KEY` as an environment variable **in the dashboard**.
4. Deploy. Live at `https://<service>.onrender.com`.

**The limitation that will surprise you:** Render's free tier wipes the container's disk on every redeploy and whenever it sleeps from inactivity. `chatbot.db` disappears — every conversation gone. For real persistence, swap `SqliteSaver` for `PostgresSaver` (`langgraph-checkpoint-postgres`) pointed at a free Neon/Supabase/Render Postgres. Same `compile(checkpointer=...)` call, different class.

---

## Quick reference

| File | Role |
|---|---|
| `backend.py` | the graph + SQLite checkpointer, no web code |
| `api.py` | FastAPI: `/chat` (streaming), `/threads`, `/health` |
| `Dockerfile` | deps layer before code layer, `${PORT}` not hardcoded |
| `.dockerignore` | keeps `.env`, `.venv/`, the DB out of the image |
| `.github/workflows/deploy.yml` | build + `/health` smoke test |

## Honest status

**Verified for real:**

- `/health`, token streaming on `/chat`, memory across calls on one `thread_id`, `/threads` — against a live uvicorn server.
- `docker build -t agentic-chatbot:ci .` → **succeeds**.
- `docker run -p 8901:8000 -e GROQ_API_KEY=...` → container serves `/health` → `{"ok":true}`, and `/chat` returns a real streamed answer **from inside the container**. So the image, the dependency install, and the `${PORT}` command all work.

**Not verified:** the GitHub Actions workflow itself has never run, because it isn't at the repo root yet (see above). Its two steps — `docker build` and polling `/health` — are exactly what was just confirmed locally, so the risk is low, but the YAML is untested.
