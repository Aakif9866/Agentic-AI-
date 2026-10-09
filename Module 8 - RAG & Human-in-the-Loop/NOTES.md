# Module 8 — RAG & Human-in-the-Loop

Two separate skills in one module. **RAG** lets the agent answer from *your* documents. **HITL** lets the agent stop and wait for a human before doing something risky.

## Run it

```bash
uv sync
uv run python 01_rag_tool.py sample_notes.pdf   # builds faiss_db/ first — run this before 02
uv run python 02_rag_chatbot.py
uv run python 03_hitl_basic.py
```

Needs `GROQ_API_KEY`. Embeddings run locally and free (no API key); the first run downloads ~90MB.

A `sample_notes.pdf` is included so everything works out of the box. Swap in any PDF.

---

## Part 1: RAG

### `rag_shared.py` — ingest once, search many times

RAG has two halves that happen at different times.

**Ingest (slow, once):**

```python
docs   = PyPDFLoader(pdf_path).load()                       # 1. read the PDF
for d in docs:
    d.page_content = " ".join(d.page_content.split())       # 2. clean whitespace
chunks = RecursiveCharacterTextSplitter(
    chunk_size=400, chunk_overlap=80).split_documents(docs) # 3. cut into chunks
FAISS.from_documents(chunks, EMBEDDINGS).save_local(DB_PATH)# 4. embed + save
```

- **Chunking** — models can't read a whole book at once, and smaller chunks make search more precise. `chunk_overlap=80` repeats a bit of text between chunks so a sentence split across a boundary isn't lost.
- **Whitespace cleanup genuinely matters.** Our first run returned the *wrong* chapter because the PDF was full of padding spaces. Collapsing whitespace and shrinking chunks fixed retrieval completely. Real PDFs are messy; clean before you chunk.
- **Embeddings** turn text into vectors so "what does a checkpointer do" can match text that never uses those exact words.

**Search (fast, every question):**

```python
@tool
def search_docs(query: str) -> str:
    """Search the ingested PDF for passages relevant to the query. Cite page numbers."""
    vs = FAISS.load_local(DB_PATH, EMBEDDINGS, allow_dangerous_deserialization=True)
    hits = vs.similarity_search(query, k=4)
    return "\n\n".join(f"[page {d.metadata.get('page','?')}] {d.page_content}" for d in hits)
```

### `02_rag_chatbot.py` — retrieval as a *tool*, not a step

**The key design decision:** search is a tool the agent *chooses* to call, wired exactly like Module 7's calculator. It is **not** a node that runs on every message.

Why it matters — the file proves it:

| Question | Searched the PDF? |
|---|---|
| "What does a checkpointer give me, according to the document?" | yes → answers with `[page 0]` citation |
| "Hi there!" | **no** |

If retrieval were a mandatory step, "Hi there!" would trigger a pointless vector search on every greeting.

**Takeaway:** RAG is a tool. The agent decides when a question needs the documents.

---

## Part 2: Human-in-the-Loop

### `03_hitl_basic.py` — `interrupt()` pauses, `Command(resume=...)` continues

```python
def chat_node(state):
    decision = interrupt({"question": q, "ask": "Approve answering this? yes/no"})
    if decision != "yes":
        return {"messages": [AIMessage("Not approved by reviewer.")]}
    return {"messages": [llm.invoke(state["messages"])]}
```

How it flows:

1. `interrupt(payload)` stops the graph mid-node and saves a checkpoint.
2. The caller finds the payload in `result["__interrupt__"][0].value`.
3. Later, `app.invoke(Command(resume="yes"), same_cfg)` continues — and `interrupt()` *returns* `"yes"` to the node.

**A checkpointer is mandatory.** Without one there's nowhere to save the paused state.

**The gotcha that will bite you:** on resume, the node **re-runs from its first line**. Anything with a side effect (an API call, a database write) must sit *after* the `interrupt()`, or it happens twice.

### `04_hitl_tool_approval.py` — approval inside the risky tool

This is the pattern you'll actually use. The interrupt lives inside the tool, so approval is attached to the dangerous action rather than to the conversation:

```python
@tool
def purchase_stock(symbol: str, quantity: int) -> dict:
    """Buy shares of a stock. Requires human approval before executing."""
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}? (yes/no)")
    if str(decision).lower() != "yes":
        return {"status": "cancelled", "reason": "declined by human"}
    return {"status": "success", "symbol": symbol, "quantity": quantity}
```

The file runs both paths — approved and declined — and the model narrates each outcome correctly. The graph is an ordinary Module 7 tool loop; only the tool changed.

### `05_hitl_approval_ui_simulation.py` — the three HITL patterns

| Pattern | Resume with | Example |
|---|---|---|
| **Approve / reject** | `"yes"` / `"no"` | buy the stock? |
| **Edit** | the corrected arguments | fix the email body before sending |
| **Ask for input** | the human's answer | "which address should I use?" |

This file shows **edit**, which is the most useful and least obvious:

```python
agent.invoke(Command(resume={"approved": True, "edited_body": edited}), cfg)
```

And it shows what a web UI actually polls:

```python
snapshot = agent.get_state(cfg)
pending = [i for task in snapshot.tasks for i in task.interrupts]
```

The output proves the edit took effect — the tool returns the human's text, not the model's draft.

---

## Quick reference

| File | Teaches |
|---|---|
| `rag_shared.py` | ingest + search, defined once and imported by both RAG files |
| `01_rag_tool.py` | build the index, query it directly |
| `02_rag_chatbot.py` | retrieval as a tool the agent chooses |
| `03_hitl_basic.py` | `interrupt()` / `Command(resume=...)` basics |
| `04_hitl_tool_approval.py` | approval inside a risky tool ← the real pattern |
| `05_hitl_approval_ui_simulation.py` | approve / edit / ask, and how a UI finds pending work |

## Gotchas we hit building this

- **The model drafts instead of calling the tool.** Asked to "email team@company.com", it helpfully wrote the email as chat text and never called `send_email` — so the approval never triggered. Fixed with a blunt system message: *call the tool, never reply with a plain-text draft, never ask for confirmation.* If your HITL never fires, check this first.
- **`langchain-huggingface` doesn't install `sentence-transformers`.** You get a clear `ImportError` at runtime; `uv add sentence-transformers` fixes it.
- **`allow_dangerous_deserialization=True`** is needed to load a FAISS index because it unpickles. Fine for an index *you* created; never load one you downloaded.
- **`langchain-community` prints a sunset warning.** It still works and it's what the course uses; the ecosystem is splitting it into standalone packages over time.
