# Module 6 — Agentic Chatbot: Memory, Streaming & Threads

Modules 4 and 5 built graphs that run once and forget everything. This module makes a graph behave like a real chatbot: it remembers, it streams, and it keeps separate conversations apart.

## Run it

```bash
uv sync
uv run python 01_basic_chatbot.py
```

Needs `GROQ_API_KEY` in `.env`.

---

## 1. `01_basic_chatbot.py` — a chatbot is just a one-node graph

**The idea:** `MessagesState` is a built-in state with a single field, `messages`. Its reducer (`add_messages`) appends new messages instead of overwriting them — so you don't write a reducer yourself.

```python
def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}
```

That's the whole chatbot. One node, one LLM call.

**What it proves:** no memory. Turn 1 it greets "Aakif"; turn 2, asked "What's my name?", it has no idea. Every `invoke()` starts from an empty state.

**Takeaway:** a graph is stateless by default. Memory is not a feature of the model — it's a feature you add next.

---

## 2. `02_persistent_chatbot.py` — one line gives you memory, threads, and time travel

**The idea:** a **checkpointer** saves the entire state after every node, filed under a `thread_id`.

```python
bot = graph.compile(checkpointer=InMemorySaver())
cfg = {"configurable": {"thread_id": "aakif-1"}}
```

That single argument buys you three things at once:

- **Memory** — same `thread_id`, and it remembers. Output: *"Your name is Aakif."*
- **Threads** — a different `thread_id` is a different conversation. Output: *"I don't have any information about your name."* This is exactly how ChatGPT's sidebar works.
- **Time travel** — `get_state_history(cfg)` lists every saved checkpoint. Pass an old one back with `invoke(None, old_cfg)` and the graph resumes from that moment. `None` means "no new input, just continue from here."

**Takeaway:** `thread_id` is the conversation's name. The checkpointer is the filing cabinet. Memory is storage, not intelligence.

---

## 3. `03_streaming_modes.py` — three different things you might want to watch

`invoke()` waits for everything then hands you the result. `stream()` yields as it goes, and the `stream_mode` picks *what* you get:

| Mode | You receive | Use it for |
|---|---|---|
| `"messages"` | individual tokens as they're generated | the typing effect in a chat UI |
| `"updates"` | what each node returned, per step | debugging which node did what |
| `"values"` | the full state after each step | watching state grow |

```python
for chunk, meta in bot.stream(q, cfg, stream_mode="messages"):
    if isinstance(chunk, AIMessageChunk):
        print(chunk.content, end="", flush=True)
```

The `isinstance(chunk, AIMessageChunk)` check matters — the stream also carries other message types, and without the filter you'd print noise.

**Takeaway:** `"messages"` is for users, `"updates"` is for you.

---

## 4. `04_sqlite_multithread.py` — memory that survives a restart

Change one class and the filing cabinet becomes a file on disk:

```python
conn = sqlite3.connect("chatbot.db", check_same_thread=False)
bot = graph.compile(checkpointer=SqliteSaver(conn))
```

- `InMemorySaver` → gone when the process exits.
- `SqliteSaver` → written to `chatbot.db`, still there tomorrow.
- `check_same_thread=False` is required because web frameworks (Streamlit, FastAPI) touch the same connection from different OS threads.

Two helper functions are the backend of a ChatGPT-style sidebar:

```python
checkpointer.list(None)   # every checkpoint, across all threads -> collect thread_ids
bot.get_state(cfg)        # the current messages for one thread
```

**Proof it works:** run the file twice. First run reports 1 thread, second reports 2 — the first conversation was still in the database.

**Takeaway:** same graph, same API, different checkpointer class. That's the whole change needed to go from demo to restart-proof.

---

## 5. `05_langsmith_tracing.py` — seeing what your agent actually did

**The idea:** tracing requires **zero changes to your graph**. You set environment variables and every run is recorded — each node, each LLM call, tokens, latency, cost.

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<key from smith.langchain.com>
LANGSMITH_PROJECT=agentic-ai-course
```

Optionally tag runs so you can find them later:

```python
cfg = {
    "configurable": {"thread_id": "traced-1"},
    "run_name": "demo_chat_turn",
    "tags": ["module-6", "demo"],
    "metadata": {"user": "aakif"},
}
```

The file prints setup instructions if tracing is off, so it runs either way.

**Takeaway:** observability is configuration, not code. Once an agent has tools and loops (Module 7+), traces are the only practical way to see why it did something.

---

## Quick reference

| File | Adds | Key API |
|---|---|---|
| 01 | nothing (baseline, no memory) | `MessagesState` |
| 02 | memory, threads, time travel | `compile(checkpointer=InMemorySaver())`, `get_state_history` |
| 03 | streaming | `stream(..., stream_mode=...)` |
| 04 | memory that survives restarts | `SqliteSaver(conn)`, `checkpointer.list(None)` |
| 05 | observability | `LANGSMITH_*` env vars, `run_name`/`tags` |

## Gotchas we hit building this

- **Groq's model names change.** The course text says `llama-3.3-70b-versatile`; Groq has since decommissioned it. These files use `openai/gpt-oss-120b`. If a model 404s, list the live ones: `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`.
- **Folder names must not contain `:`.** `uv run` errors out, and worse, `source .venv/bin/activate` *silently* does nothing (you stay on system Python and get confusing import errors). Every module folder in this repo uses ` - ` instead.
- **`invoke(None, cfg)` is not a typo.** `None` means "resume from this checkpoint", which is how time travel replays without re-sending input.
