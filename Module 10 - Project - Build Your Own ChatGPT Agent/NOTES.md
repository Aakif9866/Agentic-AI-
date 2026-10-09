# Module 10 — Project: Build Your Own ChatGPT Agent

The capstone. Everything from Modules 6–9 in one agent: memory, streaming, threads, tools, RAG, and human approval, behind a FastAPI service.

See `README.md` for the endpoint table and run commands. These notes explain *why* it's built this way.

## Run it

```bash
uv sync
uv run python ingest.py sample_notes.pdf    # fills faiss_db/ for search_docs
uv run uvicorn api:app --reload
uv run streamlit run ui_streamlit.py        # optional UI
```

Needs `GROQ_API_KEY` and `TAVILY_API_KEY`.

---

## The shape: four files, four jobs

```
tools.py    →  everything the agent can DO
backend.py  →  the graph that decides WHEN to do it
api.py      →  how the outside world talks to it
ingest.py   →  one-off: load a PDF into the vector store
```

This is the Module 9 split (graph separate from transport) with tools pulled out too. The reason is practical: `backend.py` stays short enough to read in one screen, and you can add a tool without touching the graph at all.

---

## `tools.py` — the agent's capabilities

Four tools, each a lesson from an earlier module:

| Tool | From | Note |
|---|---|---|
| `calculator` | Module 7 | whitelisted expression, not a bare `eval` |
| `tavily_search` | Module 7 | live web search |
| `search_docs` | Module 8 | FAISS over your PDF, cites page numbers |
| `send_email` | Module 8 | **pauses for human approval** |

Two details worth copying into your own projects:

**1. `load_dotenv()` lives in this file.** `TavilySearch()` reads its API key at *construction* time, and this module constructs it at import. Without `load_dotenv()` here, importing `tools` from a script that hadn't already loaded `.env` crashed — which is exactly what happened when we first ran `ingest.py`. A module with import-time env dependencies should load its own env.

**2. The calculator whitelists before evaluating.**

```python
SAFE_EXPR = re.compile(r"[0-9.\s+\-*/%()]+")
if not SAFE_EXPR.fullmatch(expression):
    return "error: only numbers and + - * / % ( ) are allowed"
return str(eval(expression, {"__builtins__": {}}, {}))
```

The expression is written by an LLM, and an LLM can be steered by prompt injection — so it is **not trusted input**. Because no letters can pass the whitelist, there are no names to abuse and no attribute tricks available.

---

## `backend.py` — the graph

It's the Module 7 tool loop, unchanged:

```python
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")
agent = graph.compile(checkpointer=SqliteSaver(conn))
```

That's the whole insight of this project: **a capable agent is not a complicated graph.** Four tools, a system prompt, and a checkpointer on the same three-line loop you learned in Module 7.

The system prompt does the heavy lifting — in particular this line, learned the hard way in Module 8:

> `send_email` … Call it directly with a body you write yourself; never reply with a plain-text draft and never ask the user to confirm, because an approval step already exists.

Without it the model politely writes the email as chat text, never calls the tool, and the approval step never fires.

Two helpers exist for the API layer:

```python
all_thread_ids()          # the ChatGPT-style sidebar
pending_approval(tid)     # is this thread waiting on a human?
```

---

## `api.py` — and the one flow that's genuinely tricky

`/chat`, `/threads`, `/health` work exactly as in Module 9. The new part is approval, which needs **two** endpoints because an HTTP request can't wait for a human.

```
POST /chat          → graph pauses inside send_email → stream ends EMPTY
GET  /pending/{id}  → returns the draft the human must review
POST /approve       → Command(resume={...}) → graph continues → final message
```

**The counter-intuitive bit:** when the agent pauses, `/chat` returns an **empty stream**. No tokens, no error. That's not a bug — the graph stopped before producing any assistant text. An empty stream is the client's cue to call `/pending`.

Editing works by passing the corrected value through resume:

```python
resume_value = {"approved": body.approved}
if body.edited_body:
    resume_value["edited_body"] = body.edited_body
agent.invoke(Command(resume=resume_value), cfg)
```

---

## `ui_streamlit.py` — why it talks to the graph, not the API

The UI imports `agent` directly instead of calling its own HTTP endpoints. One process, no CORS, and it demonstrates the same primitives:

- sidebar from `all_thread_ids()`
- history from `agent.get_state(cfg)`
- live typing from `agent.stream(..., stream_mode="messages")`
- **the approval screen replaces the chat box** when `pending_approval()` returns a draft — which is the correct UX: if the agent is blocked, don't invite more input.

---

## What we actually verified

Tested against a live server (`uvicorn api:app`), real Groq calls:

| # | Check | Result |
|---|---|---|
| 1 | `/health` | `{"ok":true}` |
| 2 | `calculator` via `/chat` | `18473 * 29361` → 542,385,753 |
| 3 | memory on one `thread_id` | correctly recalled the previous question |
| 4 | RAG with citation | answered from the PDF, cited `page 0` |
| 5 | `send_email` pauses | empty stream, as designed |
| 6 | `/pending/{id}` | returned the full draft |
| 7 | `/approve` + `edited_body` | resumed, returned final message |
| 8 | `/pending` after approval | `null` |
| 9 | `/threads` | all four threads listed |
| 10 | `tavily_search` | live web answer with source marker |
| 11 | the human's edit reached the tool | `{"status":"sent","body":"EDITED BY HUMAN: Q4 was great."}` |

Row 11 is the one that proves HITL is real rather than cosmetic — the text that "sent" was the human's, not the model's.

**Also verified since:** the Streamlit UI **boots clean** — `streamlit run ui_streamlit.py --server.headless true` returns HTTP 200 with no errors in the log. Module 9's Dockerfile (the same pattern this one uses) builds and serves correctly in a real container.

**Still not verified:** this module's own `docker build` — it adds a step that pre-downloads the embedding model, which Module 9's image doesn't have. And the Streamlit UI has never been *clicked* through; only its startup is confirmed.

---

## Carrying this into Module 11+

This project is most of the plumbing the later capstones reuse. For RepoSage-style work you swap the tools (`search_code`, `create_github_issue`) and keep everything else: the loop, the checkpointer, the approval flow, the API shape.

## Known limitations

- **SQLite on a free host doesn't persist.** Render wipes the disk on redeploy and on sleep. Swap `SqliteSaver` → `PostgresSaver` for real durability.
- **No thread deletion.** `SqliteSaver` has no built-in delete; you'd add a "deleted" table and filter in `all_thread_ids()`.
- **The embedding model downloads ~90MB on first use.** The Dockerfile pre-bakes it so a cold container doesn't pay that on its first request.
