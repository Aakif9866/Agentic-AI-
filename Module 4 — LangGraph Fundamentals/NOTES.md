# Module 4 — LangGraph Fundamentals

Notes on the six core graph patterns in `project/`, what each one teaches, and the gotchas that actually matter when you build on them.

## Setup

```bash
cd project
uv sync            # installs langgraph, langchain, langchain-groq, pydantic, python-dotenv
uv run python 0X_name.py
```

Requires a `GROQ_API_KEY` in `.env` for every file except `01_temperature.py`. Groq's model catalog changes over time — check `https://console.groq.com/docs/deprecations` if a model name starts 404ing; these files currently use `openai/gpt-oss-120b`.

---

## 1. The three primitives — `01_temperature.py`

Every LangGraph app is built from exactly three things:

- **State** — a `TypedDict` (or Pydantic model) that every node reads from and writes to. It's the only thing passed between steps.
- **Nodes** — plain Python functions `(state) -> dict`. A node returns *only the keys it changed*, not the full state. LangGraph merges the returned dict into state for you.
- **Edges** — wiring that says what runs next. `add_edge(a, b)` is a fixed edge; every graph needs `START` and `END` edges to mark the entry and exit points.

```python
g = StateGraph(State)
g.add_node("convert", convert)
g.add_edge(START, "convert")
g.add_edge("convert", "label")
g.add_edge("label", END)
app = g.compile()
```

`app.compile()` turns the graph definition into something runnable. `app.invoke(initial_state)` runs it start to finish and returns the final state. `app.get_graph().draw_mermaid()` dumps a Mermaid diagram of the graph — paste it into mermaid.live to see the shape.

**Why a dict and not the whole object?** Returning only changed keys is what makes parallel nodes (pattern 4) safe — LangGraph needs to know which writes came from where to merge them correctly.

---

## 2. LLM-powered nodes — `02_qa_llm.py`

A node doesn't have to be math — it can be a call to a chat model. Nothing about the graph changes; `llm.invoke(prompt).content` is just a function that happens to make a network call.

```python
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

def llm_qa(s: State) -> dict:
    return {"answer": llm.invoke(f"Answer briefly: {s['question']}").content}
```

`temperature=0` means "pick the most likely token every time" — deterministic-ish output, good for anything where you want consistency (routing decisions, extraction) rather than variety (creative writing).

---

## 3. Sequential chaining — `03_prompt_chaining.py`

The output of one LLM call becomes the input to the next. Use this when a task decomposes cleanly into fixed steps and each step is *easier for the model alone* than asking for everything in one shot.

```
outline_node → write_node
```

```python
def make_outline(s) -> dict:
    return {"outline": llm.invoke(f"Write a 5-point outline for: {s['title']}").content}

def write_blog(s) -> dict:
    return {"content": llm.invoke(f"Write a blog '{s['title']}' following:\n{s['outline']}").content}
```

This is the simplest possible multi-step agent and is almost always a better starting point than one giant prompt — each step is independently testable and debuggable.

---

## 4. Parallel fan-out / fan-in — `04_parallel.py`

Multiple nodes start from `START` simultaneously; a downstream node waits until *all* of them finish before running.

```python
for aspect in ["language", "analysis", "clarity"]:
    g.add_node(aspect, make_judge(aspect))
    g.add_edge(START, aspect)
    g.add_edge(aspect, "summarize")
```

**The key idea is the reducer.** Three parallel nodes all try to write to `scores` and `feedback` in the same tick. Without a merge strategy, LangGraph has no way to know whether the second write should overwrite or combine with the first — so it raises `InvalidUpdateError`.

```python
class EssayState(TypedDict):
    scores: Annotated[list[int], operator.add]      # concatenate lists instead of overwriting
    feedback: Annotated[list[str], operator.add]
```

`Annotated[list, operator.add]` tells LangGraph "when multiple nodes write to this key in the same step, concatenate the lists." Each judge node returns `{"scores": [r.score]}` — a single-item list — and the reducer appends them together.

**Try breaking it** (from the exercises): switch `scores` back to a plain `list[int]` and rerun. The `InvalidUpdateError` you get *is* the lesson — it's LangGraph refusing to silently drop concurrent writes.

Also uses `llm.with_structured_output(PydanticModel)` — instead of parsing free text, the model is constrained to return something matching your schema (here, `Score(feedback: str, score: int)`). Use this whenever a node's output needs to be *read by code* downstream rather than displayed to a human.

---

## 5. Conditional routing — `05_conditional.py`

An LLM makes a decision (as structured output, not free text), and a plain Python function reads that decision to pick the next node.

```python
class Sentiment(BaseModel):
    sentiment: Literal["positive", "negative"]

def route(s: ReviewState) -> Literal["thank", "apologize"]:
    return "thank" if s["sentiment"] == "positive" else "apologize"

g.add_conditional_edges("find_sentiment", route)
```

**Never route by string-matching raw LLM text** (`if "positive" in response`). Models paraphrase, hedge, and add filler words — text matching is fragile in exactly the cases that matter. Forcing a `Literal["positive", "negative"]` via structured output makes the decision a closed, type-checked value *before* your router function ever sees it. The router itself is deliberately dumb — all the judgment happens in the LLM call, routing is just a lookup.

`add_conditional_edges(source, router_fn)` — LangGraph calls `router_fn(state)` after `source` runs, and uses the returned string to pick which node runs next. You can optionally pass a dict mapping router return values to node names (see pattern 6) when they don't match 1:1.

---

## 6. Iterative loop (evaluator–optimizer) — `06_iterative_loop.py`

Generate → evaluate → if rejected, improve and evaluate again — up to a hard cap. This is the seed pattern behind self-correcting agents (Self-RAG, reflection loops, etc.) covered later in the course.

```python
g.add_conditional_edges("evaluate", should_continue, {"done": END, "again": "optimize"})
g.add_edge("optimize", "evaluate")
```

```python
def should_continue(s) -> Literal["done", "again"]:
    if s["evaluation"] == "approved" or s["iteration"] >= s["max_iteration"]:
        return "done"
    return "again"
```

**Always have both a success condition and a cap.** `s["evaluation"] == "approved"` is the happy path; `s["iteration"] >= s["max_iteration"]` is the safety net. Without the cap, a model that never approves its own output (or a flaky judge) loops forever and burns API calls indefinitely.

The `history` field uses the same `Annotated[list, operator.add]` reducer from pattern 4 — every pass through `generate`/`optimize` appends to it, so you get a full audit trail of every draft, not just the final one.

**Exercise worth doing**: remove the cap and call `app.invoke(..., {"recursion_limit": 5})`. LangGraph's own recursion guard will trip with `GraphRecursionError` — a different failure mode than your own `max_iteration` check, and useful to recognize when you see it in the wild.

---

## Quick reference

| File | Pattern | New idea introduced |
|---|---|---|
| `01_temperature.py` | state / node / edge | the three core pieces, no LLM |
| `02_qa_llm.py` | single LLM node | a model call inside a node |
| `03_prompt_chaining.py` | sequential | chain one call's output into the next |
| `04_parallel.py` | fan-out / fan-in | concurrent nodes + reducer to merge writes |
| `05_conditional.py` | conditional routing | router reads a structured decision |
| `06_iterative_loop.py` | iterative loop | capped retry loop (generate → evaluate → optimize) |

## Things that bit us while building this

- **Groq model names go stale.** `llama-3.3-70b-versatile` and `mixtral-8x7b-32768` both 404'd during this module — Groq had decommissioned them. If a model name fails, query `https://api.groq.com/openai/v1/models` with your key to get the live list rather than guessing from memory or docs.
- **`init_chat_model("groq:...")` vs `ChatGroq(model=...)`** — both exist, but `ChatGroq` from `langchain-groq` is the more direct, version-stable choice for a single fixed provider.
- **A node must return a dict of changed keys, not the full state.** Returning the whole state object back works by accident in sequential graphs but breaks the reducer merge logic in parallel ones.
