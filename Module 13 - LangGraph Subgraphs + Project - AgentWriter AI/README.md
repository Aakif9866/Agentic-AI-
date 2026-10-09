# Module 13 — Subgraphs + AgentWriter AI

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

A content pipeline — **plan → research → write → edit** — where "research" is its own **reusable subgraph** that also runs standalone.

## Why this module exists

So far every graph has been flat. A **subgraph** is a compiled graph used as a step inside another graph. It matters for the same reason functions matter: you build the research pipeline once, test it alone, and reuse it in anything that needs research.

## Setup

```bash
cd "Module 13 - LangGraph Subgraphs + Project - AgentWriter AI"
uv init --no-readme --name module13-agentwriter --python 3.12
rm main.py
uv add langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv pydantic langchain-tavily
cp "../Module 10 - Project - Build Your Own ChatGPT Agent/.env" .env
```

## Files to create

```
research_subgraph.py   its own StateGraph + own schema, runnable on its own
main.py                parent graph: plan -> research -> write -> edit
NOTES.md               your own notes afterwards
```

## Requirements

- **`research_subgraph`** compiled independently, with its **own state schema** (`topic` in, `notes` out), using Tavily. It must be runnable by itself for testing.
- **Parent graph:** `plan_node → research_node → write_node → edit_node → END`.
- `research_node` must use the **"different state, call it inside a node"** pattern — explicitly map parent state → subgraph input → parent state:

  ```python
  def research_node(state: ParentState) -> dict:
      sub_out = research_subgraph.invoke({"topic": state["topic"]})   # explicit mapping in
      return {"research_notes": sub_out["notes"]}                      # explicit mapping out
  ```

  **Not** the "shared state keys" shortcut. The whole point is that the mapping is visible.
- **`edit_node` must be a real revision step:** critique the draft against the original brief using structured output (`Literal["approved", "needs_revision"]`), and loop back to `write_node` with feedback if not approved. **Capped at 3 iterations** (Module 5's capped-loop pattern) plus `recursion_limit`.
- Stream with `stream_mode="updates"` so you can watch each stage finish.

## Acceptance criteria

- [ ] Input: topic + target word count + tone → a complete article, **with `state["research_notes"]` inspectable separately** (proves the subgraph's output really flowed into the parent).
- [ ] Running `research_subgraph` **alone** (not via the parent) produces sensible notes — proving it's genuinely reusable and not hardcoded to this parent.

## Pitfalls specific to this module

- **The edit loop is where this module breaks.** `edit_node → write_node → edit_node` must increment an iteration counter in state; if `write_node` resets or forgets it, you loop forever. Increment in `write_node`, check in the router.
- `Literal["approved", "needs_revision"]` via `with_structured_output` needs `method="json_mode"` on `gpt-oss-120b`, with the field name spelled out in the prompt. See `AGENT_RULES.md` #2.
- A subgraph's state keys **don't** merge into the parent automatically when schemas differ — that's deliberate here. If `research_notes` comes back empty, your mapping is wrong, not the subgraph.
- Word-count targets are soft. The model will miss them. Judge on "did the pipeline run and revise", not exact word counts.

## Further steps & ideas

- Reuse `research_subgraph` in Module 11's TripMate as the `places_agent` — that's the real test of reusability.
- Add a second subgraph: `fact_check_subgraph` that verifies claims in the draft and feeds into `edit_node`.
- Make `plan_node` produce a structured outline (Pydantic), then have `write_node` write section-by-section with `Send` (Module 5's dynamic fan-out) — one branch per section, in parallel.
- Log each revision into a `history` list with an `operator.add` reducer so you can read the draft's evolution.
