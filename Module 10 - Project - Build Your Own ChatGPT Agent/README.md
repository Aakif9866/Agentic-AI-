# Module 10 — ChatGPT-style Agent (capstone for Modules 6–9)

Everything from Modules 6–9 in one agent: memory, streaming, threads, tools, RAG, and human approval, behind a FastAPI service.

## Run it

```bash
uv sync
uv run python ingest.py sample_notes.pdf      # fills faiss_db/ for the search_docs tool
uv run uvicorn api:app --reload               # API on :8000
uv run streamlit run ui_streamlit.py          # optional local UI
```

Needs `GROQ_API_KEY` and `TAVILY_API_KEY` in `.env`.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| POST | `/chat` | Streams the reply token by token. Body: `{thread_id, message}` |
| GET | `/pending/{thread_id}` | The draft awaiting human approval, or `null` |
| POST | `/approve` | Resumes a paused thread. Body: `{thread_id, approved, edited_body?}` |
| GET | `/threads` | Every thread_id stored in `chatbot.db` |
| GET | `/health` | `{"ok": true}` — what Render and CI poll |

## Tools the agent can call

- `calculator` — arithmetic, whitelisted expression (no bare `eval`)
- `tavily_search` — live web search
- `search_docs` — FAISS search over the ingested PDF, cites page numbers
- `send_email` — **pauses for human approval**, and the human can edit the body first

## The one flow worth understanding

Asking the agent to send an email does **not** return text. It pauses:

```bash
curl -N -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"thread_id":"t1","message":"Email team@company.com about Q4, subject Q4 Results."}'
# -> empty stream, because the graph paused inside the tool

curl localhost:8000/pending/t1
# -> {"pending":{"action":"send_email","to":"...","body":"<draft>"}}

curl -X POST localhost:8000/approve -H 'Content-Type: application/json' \
  -d '{"thread_id":"t1","approved":true,"edited_body":"My edited text."}'
# -> {"final_message":"The email has been sent."}
```

An empty `/chat` stream means "check `/pending`" — that is the client's cue, not a bug.

## Deploying

Render: New → Web Service → connect repo → it detects the `Dockerfile`. Set `GROQ_API_KEY` and `TAVILY_API_KEY` as environment variables in the dashboard, never in the image.

**Free-tier limitation:** the container's disk is wiped on redeploy and on sleep, so `chatbot.db` disappears and all threads are lost. For real persistence swap `SqliteSaver` for `PostgresSaver` (`langgraph-checkpoint-postgres`) against a free Neon/Supabase/Render Postgres. Same `compile(checkpointer=...)` call, different class.

## Done-means checklist

- [x] `/chat` streams tokens and remembers context per `thread_id`
- [x] Two different `thread_id`s never see each other's history
- [x] Math goes through `calculator`, not mental arithmetic
- [x] PDF questions cite page numbers
- [x] Email pauses, `/pending` shows the draft, `/approve` with `edited_body` changes what sends
- [ ] Deployed to Render, `/health` green on the public URL
- [ ] LangSmith traces for 5 real conversations (needs `LANGSMITH_API_KEY`)
