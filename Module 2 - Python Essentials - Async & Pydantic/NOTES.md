# Module 2 — Python Essentials: Async & Pydantic

**Treat this as a checklist, not a course.** You need *reading* fluency in two things, not mastery. If you can read both snippets below, skip ahead to Module 4 and come back when something bites.

Files here: [`async.ipynb`](./async.ipynb), [`pydantic.ipynb`](./pydantic.ipynb), [`notes.txt`](./notes.txt), `learning.docx`.

---

## Why this module exists

Two Python features show up constantly from Module 7 onward:

| Feature | Where it bites you |
|---|---|
| **`async` / `await`** | **Module 12 (MCP)** — the MCP client is async, so the agent must be `await`ed. Also any time you run agents concurrently. |
| **Pydantic** | **Modules 5, 11, 13, 14, 16** — every `with_structured_output()` call takes a Pydantic model. It's how you get *typed* data out of an LLM instead of text you have to parse. |

## Prerequisites

Functions, dicts, classes, imports. That's it.

---

## Check 1 — can you read this?

```python
import asyncio

async def fetch(name: str) -> str:
    await asyncio.sleep(1)          # pretend this is a network call
    return f"done: {name}"

async def main():
    results = await asyncio.gather(fetch("a"), fetch("b"), fetch("c"))
    print(results)

asyncio.run(main())
```

**What you must grasp:** those three calls take ~1 second total, not 3. `await` means "pause here and let other work run" — not "wait and block".

- `async def` → a coroutine. Calling it does **nothing** until awaited.
- `await` → run it, yield control meanwhile.
- `asyncio.gather(...)` → run several concurrently.
- `asyncio.run(main())` → the entry point from normal sync code.

**Why it matters for agents:** `notes.txt` makes the point directly — multiple agents that don't depend on each other can run in parallel, cutting total time. Module 5's `Send` and Module 7's parallel tool calls are this idea at the graph level.

**The one error you'll hit:** calling an async function without `await` gives you a coroutine object and a `RuntimeWarning: coroutine was never awaited`, not a result. In Module 12, `agent.invoke(...)` where `ainvoke` was needed fails this way.

## Check 2 — can you read this?

```python
from typing import Literal
from pydantic import BaseModel, Field

class Review(BaseModel):
    sentiment: Literal["positive", "negative"]
    score: int = Field(ge=0, le=10)
    summary: str
```

**What you must grasp:** this is a *contract*. `Literal` means the value can only be one of those two strings. `Field(ge=0, le=10)` means 0–10 inclusive. If data doesn't match, Pydantic raises instead of letting bad data through.

**Why it matters for agents:** you hand this class to `llm.with_structured_output(Review)` and get back a `Review` object with real fields — `r.sentiment`, `r.score`. No regex, no JSON parsing, no string matching on model output. Module 5's file 05 explains why routing on `Literal` beats matching on raw text.

**Pydantic v2 only** (per [`../AGENT_RULES.md`](../AGENT_RULES.md)): `model_dump()`, not the old `.dict()`.

---

## Setup and run

The notebooks need a Jupyter kernel:

```bash
uv init --no-readme --name module2-python --python 3.12
uv add pydantic ipykernel
uv run jupyter lab      # or open the .ipynb in VS Code
```

No API key needed — both notebooks are pure Python.

## Expected output

`async.ipynb`: concurrent calls finishing in roughly the time of the slowest one, not the sum. `pydantic.ipynb`: valid data constructing cleanly, invalid data raising `ValidationError`.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `RuntimeWarning: coroutine ... never awaited` | called an `async def` without `await` | add `await`, or `asyncio.run(...)` at the top level |
| `asyncio.run() cannot be called from a running event loop` | using `asyncio.run` inside a notebook | notebooks already have a loop — just `await` directly in the cell |
| `ValidationError` | data doesn't match the model | that's Pydantic working — read which field failed |
| `AttributeError: 'Review' object has no attribute 'dict'` | Pydantic v1 habit | use `.model_dump()` |

## Exercises

1. Change `asyncio.gather` to a plain `for` loop with `await` inside. Time both. The difference *is* the lesson.
2. Add `email: str` to `Review` and feed it `"not-an-email"`. Nothing happens — then try `EmailStr` and see validation fire.
3. Write a Pydantic model for a trip plan (destination, days, budget). You'll build almost exactly this in Module 11.
4. **Real payoff:** after Module 5, re-read your model above. You'll recognise it as the thing that makes LLM output safe to branch on.

---

**Next:** skim Module 3 for contrast, then start properly at **Module 4**.
