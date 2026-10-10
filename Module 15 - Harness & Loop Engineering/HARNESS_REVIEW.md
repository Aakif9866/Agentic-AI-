# Harness Review — Module 10 (ChatGPT-style Agent)

**Audited project:** `Module 10 - Project - Build Your Own ChatGPT Agent`
**Audited at commit:** `5443728` (pre-fix state)
**Files:** `backend.py` (62 lines), `tools.py` (78 lines), `api.py` (63 lines)

Line references are to the **pre-fix** files. The fix in §9 changed `backend.py` and `api.py`, so numbers shift slightly after it.

---

## The 8 rows

### 1. Context — what the model sees each turn

**Good.** A single system prompt is injected exactly once, and only if absent, so it can't be duplicated by replays or resumes:

> `backend.py:30-34` — `if not isinstance(msgs[0], SystemMessage): msgs = [SYSTEM, *msgs]`

**Weak.** The full message history is sent every turn with **no trimming at all**. Module 7 built `trim_messages` (`Module 7/04_trim_long_history.py`) and Module 10 never adopted it. A long thread will grow until it exceeds the context window and starts erroring — and because `SqliteSaver` persists threads forever, this is a *when*, not an *if*.

> `backend.py:30-34` — no `trim_messages` call anywhere in the file.

---

### 2. Tools — can it do the job, and will it pick correctly?

**Good.** Four tools, each with a docstring written as routing instructions rather than developer notes, and the system prompt disambiguates further:

> `tools.py:37` — `"""Evaluate an arithmetic expression. Numbers and + - * / % ( ) ** only, e.g. '2**10'."""`
> `backend.py:14-24` — per-tool guidance ("`calculator` for math — always use it instead of doing arithmetic yourself")

**Weak.** `web_search` is `TavilySearch(max_results=3)` — a raw third-party object, not a `@tool` with our own docstring. Its description comes from the library, so it's the one tool whose routing text we don't control.

> `tools.py:46` — `web_search = TavilySearch(max_results=3)`

---

### 3. Control flow — who decides what runs next?

**Good.** The model decides tool use; the graph decides topology. Standard, legible, and only three edges:

> `backend.py:40-42` — `add_conditional_edges("chat", tools_condition)` + `add_edge("tools", "chat")`

**Weak.** The `chat → tools → chat` cycle has no app-level ceiling. `api.py` passes **no `recursion_limit` at all**, so a model that loops on tool calls runs to LangGraph's internal default with nothing in our code to stop or log it.

> `api.py:24-26` (pre-fix) — `cfg = {"configurable": {"thread_id": body.thread_id}}` — no `recursion_limit`.

---

### 4. Verification — how do we know the output is right?

**Good.** The one place correctness genuinely matters is deterministic: arithmetic is whitelisted and evaluated by Python, not asserted by the model.

> `tools.py:22,38-39` — `SAFE_EXPR.fullmatch(expression)` before `eval`

**Weak.** **Nothing checks the agent's answers.** No judge, no assertion, no eval set. The RAG path asks for page citations in the prompt (`backend.py:19`) but never verifies one was produced, so a confidently wrong, uncited answer is indistinguishable from a good one. This row stays weak until Module 16 exists.

> `backend.py:30-34` — the reply is returned unexamined.

---

### 5. Permissions — what can it do unasked?

**Good.** The genuinely irreversible action requires a human, and the approval lives *inside* the tool rather than in the conversation, so it can't be routed around:

> `tools.py:62-64` — `send_email` calls `interrupt({...})` before sending

**Weak.** The boundary is drawn once and never revisited. `web_search` sends user text to a third party and `search_docs` reads the local index, both with zero gating. Defensible, but it is an implicit decision rather than a stated policy — nothing in the repo says *why* the line is there.

> `tools.py:75` — `ALL_TOOLS = [calculator, web_search, search_docs, send_email]` — only one of four is gated.

---

### 6. State / memory — what's kept, where, how long?

**Good.** Durable, thread-scoped, and restart-proof, with the DB path configurable for deployment:

> `backend.py:44-46` — `SqliteSaver(conn)`, `check_same_thread=False`
> `backend.py:26` — `DB_PATH = os.getenv("CHECKPOINT_DB", "chatbot.db")`

**Weak.** Memory only grows. There is **no deletion path** — no way to drop a thread, expire old ones, or honour "delete my data". `all_thread_ids()` enumerates everything ever created.

> `backend.py:49-50` — list only; no corresponding delete.

---

### 7. Budgets — what stops it burning money forever? ⬅ **WEAKEST**

**Good.** Retrieval is bounded (`k=4`) and search results are capped at 3.

> `tools.py:56` — `similarity_search(query, k=4)` · `tools.py:46` — `max_results=3`

**Weak — and this is the one I fixed.** A repo-wide grep for any cap found exactly one hit, and it was Tavily's:

```
$ grep -rn "limit|budget|max_|cap" backend.py api.py tools.py
tools.py:46:web_search = TavilySearch(max_results=3)
```

Nothing caps model calls, tool calls, tokens, or cost. Per thread or in total. Combined with row 3 (no `recursion_limit`) and row 6 (threads live forever), a single misbehaving conversation could spend without limit and there was no number anywhere in the codebase that would stop it.

**Why this is the weakest rather than row 4:** verification being absent degrades *quality* and is visible when you read an answer. Budgets being absent is an **unbounded liability** that is invisible until the bill arrives, and it is the only row where the failure mode is open-ended.

---

### 8. Observability — can you find out why it misbehaved?

**Good.** LangSmith needs no code change — it's purely env configuration (Module 6 established this), and the HITL state is inspectable on demand:

> `backend.py:53-57` — `pending_approval()` reads `snapshot.tasks` for pending interrupts

**Weak.** Locally there is **nothing**: no structured logging, no token counts, no latency, no record of which tool ran. If a user reports a bad answer from last Tuesday, the checkpoint holds the messages but nothing explains the behaviour. Tracing is also off by default (`LANGSMITH_TRACING=false` in `.env`), so the default posture is blind.

> `backend.py` / `api.py` — no `logging` import in either file.

---

## 9. The fix: a real budget cap

**Row chosen:** Budgets (§7) — the weakest, by the argument above.

### What changed

`backend.py` — a per-thread model-call counter, checkpointed with the rest of state so it survives restarts, and env-overridable so the old behaviour stays reproducible:

```python
MAX_LLM_CALLS_PER_THREAD = int(os.getenv("MAX_LLM_CALLS_PER_THREAD", "12"))

class ChatState(MessagesState):
    llm_calls: int

def chat_node(state: ChatState) -> dict:
    used = state.get("llm_calls", 0)
    if used >= MAX_LLM_CALLS_PER_THREAD:
        # Refuse *before* spending anything.
        return {"messages": [AIMessage(
            f"This conversation has reached its budget of "
            f"{MAX_LLM_CALLS_PER_THREAD} model calls. Start a new thread to continue."
        )]}
    ...
    return {"messages": [llm.invoke(msgs)], "llm_calls": used + 1}
```

Plus `StateGraph(MessagesState)` → `StateGraph(ChatState)`, and the row-3 gap closed in one line:

```python
# api.py
cfg = {"configurable": {"thread_id": body.thread_id}, "recursion_limit": 25}
```

### Why this design

- **It caps the loop too.** Every pass through `chat_node` costs one model call, so the same counter bounds a runaway `chat → tools → chat` cycle. One guard, two problems.
- **The check precedes the spend.** Refusing before `llm.invoke` means hitting the cap costs nothing, which is the whole point of a budget.
- **It's checkpointed, not in-memory.** `llm_calls` lives in state, so the cap holds across restarts — the same reason threads survive.
- **The old behaviour is reproducible** via env var, which is what makes the before/after below honest rather than remembered.

### Before / after — real output

Same script, same prompts, only the cap differs:

```
$ MAX_LLM_CALLS_PER_THREAD=999 uv run python budget_demo.py      # BEFORE
cap = 999 | thread = budget-c70a59
turn 1: llm_calls=1   answered
turn 2: llm_calls=2   answered
turn 3: llm_calls=3   answered
turn 4: llm_calls=4   answered
turn 5: llm_calls=5   answered
turn 6: llm_calls=6   answered
total model calls charged to this thread: 6
```

```
$ MAX_LLM_CALLS_PER_THREAD=3 uv run python budget_demo.py        # AFTER
cap = 3 | thread = budget-d9a5e5
turn 1: llm_calls=1   answered
turn 2: llm_calls=2   answered
turn 3: llm_calls=3   answered
turn 4: llm_calls=3   REFUSED (no model call spent)
turn 5: llm_calls=3   REFUSED (no model call spent)
turn 6: llm_calls=3   REFUSED (no model call spent)
total model calls charged to this thread: 3
```

**What changed and why it's better:** before, six requests cost six model calls and sixty would have cost sixty — the conversation's cost was bounded only by the user's patience. After, spend stops dead at the cap and the counter **freezes at 3**, which is the evidence that refusals are free rather than merely refused. The agent also now fails *politely and legibly* ("start a new thread") instead of silently costing more than intended.

### No regression

Module 10 re-verified after the change, against a live server:

| Check | Result |
|---|---|
| `GET /health` | `{"ok":true}` |
| `calculator` via `/chat` | `7 × 6` → **42** |
| RAG with citation | answered from the PDF, cited the page |
| `GET /threads` | all 8 threads listed |

---

## 10. Appendix — Ponytail complexity pass

`ponytail-audit` was run on the same three files. Note its scope is **over-engineering only** — it explicitly routes correctness, security and performance elsewhere, so it is *not* a substitute for the 8-row audit above. Findings:

```
Lean already. Ship.
net: -0 lines, -0 deps possible.
```

No single-implementation interfaces, no factories, no wrappers that only delegate, no dead config. The one case worth naming is `ingest_pdf` living in `tools.py` (`tools.py:25`) while being used only by `ingest.py` — defensible, since it shares `EMBEDDINGS` and `DB_PATH` with `search_docs` and splitting it would duplicate both.

---

## 11. Remaining weaknesses, ranked

Deliberately **not** fixed — one row per audit is the exercise:

| Row | Gap | Cheapest fix |
|---|---|---|
| 4 Verification | nothing checks answers | Module 16's eval harness |
| 8 Observability | no local logging or token counts | `logging` + log `response.usage_metadata` |
| 1 Context | no trimming; threads grow unbounded | adopt Module 7's `trim_messages` |
| 6 State | no thread deletion | `DELETE /thread/{id}` + a tombstone table |
| 2 Tools | `web_search` description not ours | wrap Tavily in our own `@tool` |
| 5 Permissions | gating policy implicit | state it in `ARCHITECTURE.md` |

Re-audit after Module 16 — row 4 should change character completely.
