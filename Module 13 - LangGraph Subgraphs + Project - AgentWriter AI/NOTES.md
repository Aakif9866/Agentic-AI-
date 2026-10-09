# Module 13 — Subgraphs + AgentWriter AI

A graph used as a **step inside another graph**, and why that's worth the ceremony.

## Run it

```bash
uv sync
uv run python research_subgraph.py   # the subgraph alone
uv run python main.py                # the full pipeline
```

---

## The idea

Every graph so far has been flat. A **subgraph** is a compiled graph you call from inside a node of another graph.

```
plan → research → write → edit → END
          │                 └── needs_revision ──┐
          │                                      ↓
          │                                    write
          └─ invokes:  plan_queries → gather → synthesize
                       (its own graph, its own schema)
```

It matters for exactly the reason functions matter: **build the research pipeline once, test it alone, reuse it anywhere.** The research half knows nothing about articles.

---

## 1. `research_subgraph.py` — narrow on purpose

```python
class ResearchState(TypedDict):
    topic: str          # input
    queries: list[str]  # internal
    raw: str            # internal
    notes: str          # output
```

Three steps: ask the model for 3 search queries → run them through Tavily → synthesize bullet notes.

**The schema is the interface.** It takes a `topic` and returns `notes`. No `word_count`, no `tone`, no `draft` — nothing about articles. That narrowness is what makes it reusable: it would work just as well inside TripMate (Module 11) as the `places` specialist.

### Proof it's genuinely reusable

Running it standalone produced real notes with no parent involved:

```
Queries it chose:
  - Why does LangGraph use reducers?
  - LangGraph reducers purpose
  - LangGraph reducer explanation

Notes:
- Reducers let LangGraph merge multiple node outputs into a single, coherent value...
- By defining a reducer for a state field, parallel branches can write concurrently...
```

If this only worked through `main.py`, it wouldn't be a subgraph — it'd be three functions with extra steps.

---

## 2. The explicit mapping — the actual lesson

There are two ways to connect a subgraph. This module uses the harder-looking one deliberately.

```python
def research(state: ArticleState) -> dict:
    sub_in  = {"topic": state["topic"]}          # parent state -> subgraph input
    sub_out = research_subgraph.invoke(sub_in)   # separate schema, separate graph
    return {"research_notes": sub_out["notes"]}  # subgraph output -> parent state
```

Three lines, and every one is visible. Compare to the shortcut — giving both graphs a shared `notes` key and letting LangGraph merge them automatically. The shortcut is less typing and worse:

| | Explicit mapping (used here) | Shared-keys shortcut |
|---|---|---|
| What the subgraph needs | obvious from the call | you must read both schemas to know |
| Renaming a parent field | breaks in one visible place | breaks silently, somewhere else |
| Reusing the subgraph elsewhere | works — it has no opinion about the parent | the new parent must adopt the same key names |
| Debugging an empty result | check 3 lines | check two schemas and hope |

**Rule of thumb:** when a subgraph is meant to be reused, map explicitly. Shared keys couple the two graphs together, which is the opposite of why you built a subgraph.

If `research_notes` ever comes back empty, your **mapping** is wrong — not the subgraph. Run the subgraph standalone to find out which.

---

## 3. The capped revision loop

`edit` is a real critic, not a rubber stamp. It returns structured output:

```python
class Critique(BaseModel):
    verdict: Literal["approved", "needs_revision"]
    feedback: str
```

and the router sends the draft back to `write` with that feedback:

```python
def route(state) -> Literal["done", "revise"]:
    if state["verdict"] == "approved" or state["iteration"] >= state["max_iteration"]:
        return "done"
    return "revise"

g.add_conditional_edges("edit", route, {"done": END, "revise": "write"})
g.add_edge("write", "edit")          # the loop
```

`write` injects the feedback into its own prompt on the next pass:

```python
fix = f"\n\nAddress this editor feedback:\n{state['feedback']}" if state.get("feedback") else ""
```

**Where the counter lives matters.** `iteration` increments in `write`, not `edit`. If `write` ever reset or skipped it, the loop would run forever — Module 5's lesson. `recursion_limit=25` is passed as the second line of defence.

A `drafts: Annotated[list[str], operator.add]` field keeps every draft, so you can read the article's evolution instead of only its final state.

---

## 4. `stream_mode="updates"` to watch the stages

```
  [plan]
  [research] -> 1151 chars of notes
  [write]
  [edit] -> approved
```

Four lines that tell you the pipeline ran in order and the subgraph returned real content. Far better feedback than waiting for one blob at the end.

**One cost trap:** stream and then `invoke` the same brief and you pay for the whole pipeline **twice**. Accumulate the streamed payloads instead:

```python
out = final or {}   # never invoke twice, it doubles the cost
```

---

## Verified / not verified

**Verified:**
- Full pipeline runs `plan → research → write → edit`, produced a 365-word article matching the brief.
- `state["research_notes"]` is populated and inspectable separately — proving the subgraph's output flowed into the parent.
- The subgraph runs **standalone** and produces sensible notes.

**Not verified — the revise path.** The editor **approved on pass 1** (`Revisions: 1 (cap 3) | verdict: approved`), so `edit → write` never actually fired. The loop is wired and capped, but it hasn't been *seen* looping.

To force it (one line, worth doing):

```python
# make the brief hard to satisfy in one go
"word_count": 1200, "tone": "rhyming verse",
```

or tighten the editor prompt (`"Reject any draft that doesn't cite at least 3 research notes verbatim"`). An approving-on-first-pass critic is the classic false-positive in this pattern — the loop *looks* fine because nothing errors. Always prove your critic can say no.

---

## Quick reference

| Piece | Detail |
|---|---|
| Subgraph | own `StateGraph`, own schema, `.compile()`d separately |
| Interface | `topic` in → `notes` out, nothing article-specific |
| Connection | **explicit** dict mapping in and out, inside one node |
| Revision loop | `Literal` verdict + feedback, `iteration` incremented in `write`, cap 3 |
| Observability | `stream_mode="updates"` per stage |
| Cost trap | don't stream *and* invoke the same input |

## Where to go next

- **Reuse the subgraph in Module 11** as TripMate's `places` specialist. That's the real test of reusability — and it should need no changes to `research_subgraph.py`.
- Parallelise `gather` with `Send` (Module 5) — one branch per query instead of a loop. Good practice, and faster.
- Add a `fact_check_subgraph` feeding into `edit`. Two subgraphs in one parent.
- Have `plan` return a structured outline, then `Send` one `write` branch per section and assemble — turns this into map-reduce (Module 5, file 04).
- Force the revise loop as above, then print `drafts` to read how the article changed between passes.
