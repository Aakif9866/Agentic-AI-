# Module 15 — Harness & Loop Engineering

The only module with almost no new API. It's a **thinking** module: look at something you built and work out what would break it in production.

## What you'll produce

- [`HARNESS_REVIEW.md`](./HARNESS_REVIEW.md) — Module 10 audited across 8 rows, with real `file:line` references
- A **real code fix** to the weakest row, in Module 10
- A before/after comparison with actual output

## Prerequisites

- **Module 10 built** (it's the thing being audited)
- Having *run* Modules 4–10, so you recognise what the code does
- No new packages. Nothing to install.

## Run it

```bash
cd "../Module 10 - Project - Build Your Own ChatGPT Agent"

MAX_LLM_CALLS_PER_THREAD=999 uv run python budget_demo.py   # before: unbounded
MAX_LLM_CALLS_PER_THREAD=3   uv run python budget_demo.py   # after: capped
```

---

## The minimum concepts

**"Harness"** = everything around the model. The model is a text-in/text-out function; the harness is what you build so it's *useful and safe*: the prompt, the tools, the loop, the limits, the logging. Most agent failures are harness failures, not model failures.

**"Loop engineering"** = deciding how an agent repeats work and, crucially, **when it stops**. Modules 5 and 13 did this with `max_iteration`. This module asks the same question about money and time.

### The 8 rows, in plain English

| Row | The question |
|---|---|
| **Context** | What does the model see each turn — and is it the right stuff? |
| **Tools** | Can it do what it needs to? Can it pick the right tool? |
| **Control flow** | Who decides what runs next — you or the model? |
| **Verification** | How do you know the output is right? Who checks? |
| **Permissions** | What can it do without asking? What needs a human? |
| **State / memory** | What's remembered, where, for how long? |
| **Budgets** | What stops it burning tokens, money, or time forever? |
| **Observability** | When it misbehaves, can you find out why? |

For each row: one thing done **well**, one **concrete** weakness with a `file:line`. Not "observability could be better" — `backend.py has no logging import`.

---

## What the audit found

Grepping Module 10 for *any* limit returned one line:

```
tools.py:46:web_search = TavilySearch(max_results=3)
```

That's it. No cap on model calls, tool calls, tokens or cost — and `api.py` passed no `recursion_limit` either. So **Budgets** was the weakest row, on evidence rather than vibes.

**Why Budgets over Verification** (which is also absent): a missing verifier degrades *quality*, and you notice when you read a bad answer. A missing budget is an **unbounded liability** — invisible until the bill arrives. It's the only row whose failure mode has no ceiling.

---

## The fix, explained line by line

```python
MAX_LLM_CALLS_PER_THREAD = int(os.getenv("MAX_LLM_CALLS_PER_THREAD", "12"))
```
A number, overridable by env. The env var is what makes the before/after *reproducible* instead of remembered.

```python
class ChatState(MessagesState):
    llm_calls: int
```
Extends the built-in `MessagesState` with one counter. Because it's part of state, the checkpointer persists it — the cap survives a restart, exactly like conversation history does.

```python
used = state.get("llm_calls", 0)
if used >= MAX_LLM_CALLS_PER_THREAD:
    return {"messages": [AIMessage("...reached its budget...")]}
```
`.get(..., 0)` because old threads in `chatbot.db` predate the field. The refusal happens **before** `llm.invoke`, so hitting the cap costs nothing — the entire point of a budget.

```python
return {"messages": [llm.invoke(msgs)], "llm_calls": used + 1}
```
Charge on the way out. Only real calls increment.

**One guard, two problems:** every pass through `chat_node` costs one model call, so this same counter also bounds a runaway `chat → tools → chat` loop.

---

## Expected output

```
cap = 3 | thread = budget-d9a5e5
turn 1: llm_calls=1   answered
turn 2: llm_calls=2   answered
turn 3: llm_calls=3   answered
turn 4: llm_calls=3   REFUSED (no model call spent)
turn 5: llm_calls=3   REFUSED (no model call spent)
turn 6: llm_calls=3   REFUSED (no model call spent)
total model calls charged to this thread: 3
```

**The detail that matters:** `llm_calls` **freezes at 3**. If refusals still cost money the counter would keep climbing. A frozen counter is the proof the guard works.

---

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `KeyError: 'llm_calls'` | used `state["llm_calls"]` on a thread created before the field existed | `state.get("llm_calls", 0)` |
| Cap never triggers | still `StateGraph(MessagesState)` — your new field isn't in the schema | `StateGraph(ChatState)` |
| Counter resets every turn | returning the whole state instead of changed keys, or not returning `llm_calls` at all | return `{"llm_calls": used + 1}` from the node |
| Cap triggers immediately | reusing a thread that already spent its budget | new `thread_id` |
| Refusal still costs money | the check sits *after* `llm.invoke` | move it before |

---

## Exercises

1. **Set `MAX_LLM_CALLS_PER_THREAD=1`** and ask a question needing the calculator. It should refuse on the *second* pass — the tool result comes back and needs one more model call to summarise. Explains why tool-using turns cost ≥2 calls.
2. **Count tokens instead of calls.** `llm.invoke()` returns a message with `.usage_metadata`. Accumulate `total_tokens` in state and cap on that. Closer to real cost, and it also fixes part of row 8.
3. **Surface the budget in the API.** Add `remaining` to `/chat`'s response so a UI can warn before the wall.
4. **Fix a different row.** Row 1 (Context) is a one-liner — Module 7's `trim_messages` already exists; wire it into `chat_node`.
5. **Re-audit after Module 16.** Row 4 (Verification) should change character entirely once an eval harness exists.

---

## Gotchas hit doing this

- **`ponytail-audit` is not a harness audit.** It was invoked for this module and is scoped to **over-engineering only** (`delete`/`stdlib`/`yagni`/`shrink`), explicitly routing correctness and security elsewhere. Its verdict on Module 10 was `Lean already. Ship.` — useful, but orthogonal. Don't mistake a complexity pass for a production-readiness review; they answer different questions.
- **Adding a state field is a two-line change in two places.** New field on the schema *and* `StateGraph(NewState)`. Miss the second and the field is silently dropped — no error, the cap just never fires.
- **`file:line` references rot.** Write the review just before the fix, and record the commit SHA (`5443728` here) so the numbers stay meaningful.
- **Audit, then fix exactly one row.** Module 10 has six remaining weaknesses, all listed and all deliberately left. Fixing everything turns an audit into a rewrite and you learn less.
