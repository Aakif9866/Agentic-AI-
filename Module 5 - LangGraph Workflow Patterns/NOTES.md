# Module 5 — LangGraph Workflow Patterns

Beginner-friendly walkthrough of the five files in this folder. Module 4 taught you the building blocks (state, nodes, edges, fixed parallel branches, basic routing, basic loops). Module 5 teaches the versions of those ideas that real LangGraph apps actually use.

## Setup

This folder *is* the uv project (no nested `project/` subfolder this time):

```bash
uv sync
uv run python 01_dynamic_fanout_send.py
```

Needs `GROQ_API_KEY` in `.env` for every file (all five call an LLM).

---

## 1. `01_dynamic_fanout_send.py` — fan-out when you don't know the count yet

**The problem this solves:** in Module 4's parallel example, you hardcoded exactly 3 judge nodes because you knew in advance there'd be 3 aspects to score. But most real tasks don't know the number ahead of time — "summarize each of these N uploaded files" where N depends on what the user uploads.

**The answer: `Send`.** Instead of wiring a fixed number of nodes with `add_edge`, you write one function (`dispatch`) that looks at the state and returns a *list* of `Send(node_name, payload)` objects — one per item. LangGraph reads that list and runs that many copies of the node in parallel, each one getting only the small `payload` you gave it, not the whole state.

```python
def dispatch(state: FanState) -> list[Send]:
    return [Send("write_joke", {"topic": t}) for t in state["topics"]]
```

Give it 4 topics, you get 4 parallel branches. Give it 10, you get 10. The graph doesn't need to be redrawn.

**Plain-English takeaway:** `add_edge(START, "node")` is a train track that always goes to the same place. `Send` is "spawn one train per item in this list, right now, and send each train to the same destination with different cargo."

---

## 2. `02_command_routing.py` — doing the routing and the update in one step

**The problem this solves:** in Module 4, routing was always two separate pieces — a node that computes something, *then* a completely separate `add_conditional_edges(...)` call that reads the result and picks the next node. That's two places you have to keep in sync.

**The answer: `Command`.** A node can return a `Command(update=..., goto=...)` instead of a plain dict. `update` is exactly like before (the dict of changed state keys). `goto` is new — it's the node to run next, decided right there in the same function, by the same code that made the decision.

```python
def triage_node(state) -> Command[Literal["billing", "technical", "general"]]:
    result = llm.with_structured_output(Triage, method="json_mode").invoke(...)
    return Command(
        update={"messages": [("system", f"[routed as: {result.category}]")]},
        goto=result.category,
    )
```

No `add_conditional_edges` call needed for `triage` at all. You still have to `add_node("billing", billing_node)` etc. so the graph knows those nodes exist — but nothing wires `triage` to them except the `Command` itself.

**Plain-English takeaway:** Module 4's routing was "decide, then separately tell the map where to go." `Command` is "decide and immediately walk there" — the decision and the movement are the same action.

---

## 3. `03_multiway_router.py` — routing to more than two destinations, explicitly

**The problem this solves:** Module 4's conditional routing (`05_conditional.py`) only ever picked between two outcomes (thank / apologize). What happens when there are four or five possible destinations, and two of them should actually land on the *same* node?

**The answer:** pass an explicit dictionary as the third argument to `add_conditional_edges`, mapping every possible router output to a real node name.

```python
graph.add_conditional_edges(
    "classify",
    route_by_level,
    {
        "critical": "page_oncall",
        "high": "notify_team",
        "medium": "notify_team",   # two different levels, same destination
        "low": "log_ticket",
    },
)
```

Your router function (`route_by_level`) just returns a plain string — `"critical"`, `"high"`, etc. The dictionary is what actually connects that string to a node. This also means tools that visualize the graph can see the full shape up front, instead of having to guess from your type hints.

**Plain-English takeaway:** this is a `switch` statement for graph edges. Any router with 3+ possible outcomes should use this explicit-map style rather than relying on inference.

---

## 4. `04_map_reduce_pipeline.py` — fan-out, then *actually combine* the results

**The problem this solves:** `Send` (file 01) gets you N parallel results sitting in a list. But a list of 3 separate joke strings is fine to print — a list of 3 separate document summaries usually isn't the final answer. You need a step that reads all of them and produces one coherent output.

**The answer:** fan out with `Send` exactly like file 01, but add one more node after it — a "reduce" node — that the fanned-out branches all feed into.

```python
graph.add_conditional_edges(START, dispatch_summaries, ["summarize_one"])
graph.add_edge("summarize_one", "reduce_summaries")   # every branch converges here
graph.add_edge("reduce_summaries", END)
```

`reduce_summaries` doesn't run until *all* the `summarize_one` branches have finished and written their piece into the shared `summaries` list (using the same `operator.add` reducer pattern from Module 4's parallel example). Then it takes that whole list and asks the LLM to synthesize one overview.

**Plain-English takeaway:** "map" = do the same small job on every item, in parallel. "reduce" = take all those small results and turn them into one answer. File 01 only does the map half; this file does both.

---

## 5. `05_capped_refinement_loop.py` — a loop that checks several things, with a safety net

**The problem this solves:** Module 4's loop (`06_iterative_loop.py`) checked one yes/no condition (approved or not). Real review loops usually check a checklist of things at once (does it have a docstring? type hints? error handling?) — and if your "should we stop" logic has a bug, you want a second guarantee that the program can't loop forever.

**The answer:** two independent safety mechanisms stacked on top of each other.

1. Your own cap, same as Module 4: `state["iteration"] >= state["max_iteration"]`.
2. LangGraph's own built-in cap, passed at invoke time: `app.invoke(state, {"recursion_limit": 25})`.

```python
def route_after_review(state) -> Literal["done", "retry"]:
    if all_criteria_met(state["review"]) or state["iteration"] >= state["max_iteration"]:
        return "done"
    return "retry"
```

If your `max_iteration` logic were ever wrong (off-by-one, wrong comparison, forgot to increment), `recursion_limit` is the backstop that still kills the run with a clear `GraphRecursionError` instead of letting it spin forever and burn API credits.

**Plain-English takeaway:** `max_iteration` is "stop when you're satisfied or tired." `recursion_limit` is "stop no matter what, even if you forgot to get tired" — a second line of defense, not a replacement for the first.

---

## Quick reference

| File | Pattern | What's new vs. Module 4 |
|---|---|---|
| `01_dynamic_fanout_send.py` | dynamic fan-out | branch count decided at runtime via `Send`, not hardcoded |
| `02_command_routing.py` | combined update + route | `Command(update=..., goto=...)` replaces a separate router function |
| `03_multiway_router.py` | N-way routing | explicit `{result: node}` map instead of binary if/else |
| `04_map_reduce_pipeline.py` | map-reduce | a dedicated reduce node synthesizes fanned-out results |
| `05_capped_refinement_loop.py` | multi-criteria loop | `max_iteration` **and** `recursion_limit` as a backstop |

## Things that bit us while building this

- **Groq's `openai/gpt-oss-120b` doesn't reliably force tool calls.** `with_structured_output(PydanticModel)` (the default "tool calling" strategy) failed consistently with `Tool choice is required, but model did not call a tool` whenever the prompt was short and the schema had just one field. Switching to `with_structured_output(PydanticModel, method="json_mode")` fixed it completely.
- **`json_mode` has two requirements you must satisfy yourself**, since it just asks for *any* valid JSON — it doesn't know your Pydantic schema:
  1. The word "json" must literally appear somewhere in your prompt (Groq rejects the request otherwise).
  2. You must spell out the exact field names you want in the prompt (e.g. `{"level": "critical"|"high"|"medium"|"low"}`), or the model will invent its own field names (it returned `"severity"` when we asked for `"level"` without being explicit) and Pydantic validation will fail.
- Same model-deprecation lesson as Module 4: always check `https://api.groq.com/openai/v1/models` against your API key if a model name 404s or gets decommissioned — don't trust a tutorial's hardcoded model name.
