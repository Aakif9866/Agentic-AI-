# Module 18 — Advanced RAG I: Corrective RAG (CRAG) & Self-RAG

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

Build **both** self-correcting RAG architectures, test them on the **same** PDF, and explain why they behave differently.

## Why this module exists

Module 8's RAG was naive: retrieve, then answer. If retrieval returned junk, the model answered from junk. These two architectures add a **grading step** so the system can notice its own retrieval was bad and do something about it.

- **CRAG** grades the *documents*. Bad docs → rewrite the query and search the web instead.
- **Self-RAG** grades its own *answer* — twice: is it supported by the docs, and is it actually useful? Either check can send it back round.

Both are built from patterns you already know: conditional routing (Module 5), capped loops (Module 5), structured output.

## Setup

```bash
cd "Module 18 - Advanced RAG I - Corrective RAG & Self-RAG"
uv init --no-readme --name module18-crag-selfrag --python 3.12
rm main.py
uv add langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv pydantic \
       langchain-tavily langchain-community langchain-text-splitters \
       langchain-huggingface sentence-transformers faiss-cpu pypdf
cp "../Module 8 - RAG & Human-in-the-Loop/.env" .env
cp "../Module 8 - RAG & Human-in-the-Loop/sample_notes.pdf" .
cp "../Module 8 - RAG & Human-in-the-Loop/rag_shared.py" .
```

Module 8's `rag_shared.py` already does ingest + search correctly (including the whitespace cleanup) — reuse it rather than rewriting.

## Files to create

```
crag.py           Corrective RAG graph
self_rag.py       Self-RAG graph
COMPARISON.md     the written comparison (required)
NOTES.md          your own notes afterwards
```

## Requirements — CRAG (`crag.py`)

```
retrieve → grade_each_doc → CORRECT             → refine → generate
                          → INCORRECT/AMBIGUOUS → rewrite_query → web_search → refine → generate
```

- `UPPER` / `LOWER` thresholds on a structured **`DocScore` (0–1 float)**.
- A sentence-level **refine** step (keep the relevant sentences, drop the rest).
- Use **`langchain-tavily`'s `TavilySearch`** — not the deprecated `langchain_community.tools.tavily_search`.

## Requirements — Self-RAG (`self_rag.py`)

```
decide_retrieval → direct | retrieve
                 → is_relevant → generate | no_answer
                 → is_sup  → (loop to revise, capped)
                 → is_use  → (loop to rewrite_query, capped) | no_answer
```

- **`MAX_RETRIES`** (for IsSUP) and **`MAX_REWRITE_TRIES`** (for IsUSE) enforced **independently** in state.

## Acceptance criteria

- [ ] Both scripts run against the same ingested PDF with **3 questions each**:
  1. clearly answerable from the doc
  2. needs a rewrite/retry
  3. **not answerable at all** — must gracefully say "I don't know" or use the web fallback, **never** hallucinate a confident wrong answer. **Verify #3 by hand.**
- [ ] `COMPARISON.md`: for the unanswerable question, what did CRAG do vs Self-RAG, and why does the difference make sense given each architecture?

## Pitfalls specific to this module

- **These are the two most loop-prone graphs in the course.** Two independent counters in Self-RAG means two independent ways to loop forever. Pass `recursion_limit` on every `invoke`, and print the counters each pass while developing.
- **Every grader needs structured output**, so every grader hits the `json_mode` requirement — see `AGENT_RULES.md` #2. With this many graders, write one helper that wraps `with_structured_output(Schema, method="json_mode")` plus the "respond with JSON of the exact form {...}" prompt suffix, and reuse it.
- A `DocScore` float from an LLM is noisy. Don't set `UPPER`/`LOWER` too tight or everything lands AMBIGUOUS. Start at `UPPER=0.7`, `LOWER=0.3`, then tune against real output.
- **`sample_notes.pdf` is about LangGraph**, so pick your unanswerable question from a genuinely different domain ("what's the capital of Peru?") — not just a harder LangGraph question, which the doc may partly cover.
- Self-RAG's `no_answer` path is the one people forget to implement, and it's the one that matters most. An agent that says "I don't know" is better than one that invents.

## Further steps & ideas

- Run both on the *same* question set and record which used the web fallback — that's a real architectural comparison.
- Add the graders' scores to the output so you can see *why* a path was taken, not just which.
- Swap `sample_notes.pdf` for a PDF you actually care about (lecture notes, a paper) — the behaviour difference becomes much more obvious on content you know well.
- Combine the two: grade documents (CRAG) *and* grade the answer (Self-RAG) in one graph. That's roughly what production RAG looks like.
- These graders are perfect eval targets — add a `rag_quality` category to Module 16's dataset.
