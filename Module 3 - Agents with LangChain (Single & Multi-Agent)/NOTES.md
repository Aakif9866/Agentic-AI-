# Module 3 — Agents with LangChain (Single & Multi-Agent)

Two working projects built with **LangChain** rather than LangGraph. **Skim this module.** Its value is contrast: it shows what LangGraph replaced and why.

```
Single AI Agent System/     one agent + tools
Multi-Agent AI System/      Search → Reader → Writer → Critic
```

Both are uv projects with their own `pyproject.toml`, so they run independently.

---

## Why this module exists

Module 4 onward uses LangGraph's `StateGraph`. To appreciate what that buys you, it helps to have seen the alternative: chaining calls in LangChain, where the control flow lives in Python glue rather than in an explicit graph.

**What you'll notice after Module 5:** in these projects, "what runs next" is scattered through the code. In LangGraph it's one `add_edge` line you can read off the top of the file — and `app.get_graph().draw_mermaid()` can draw it. That legibility is the whole reason the rest of the course uses LangGraph.

## Prerequisites

- Module 2's Pydantic check (structured output appears here)
- A `GROQ_API_KEY` and `TAVILY_API_KEY` in each project's `.env`

---

## Setup and run

```bash
cd "Single AI Agent System"
uv sync
uv run python main.py

cd "../Multi-Agent AI System"
uv sync
uv run streamlit run app.py      # UI
uv run main.py                   # CLI
```

Each project has its own `README.md` and `steps.md` explaining how it was built. `.env.example` lists the keys needed — copy it to `.env` and fill in.

---

## File walkthrough

### Single AI Agent System

| File | Role |
|---|---|
| `main.py` | entry point — builds the agent and runs it |
| `project/app.py` | UI layer |
| `project/code.ipynb` | the exploratory notebook it grew from |

One agent, a few tools, one job. The conceptual ancestor of **Module 7**.

### Multi-Agent AI System

A research assistant: **Search agent → Reader agent → Writer chain → Critic chain.**

| File | Role |
|---|---|
| `src/agents/agents.py` | the individual agents |
| `src/tools/tools.py` | tools they can call |
| `src/pipelines/pipeline.py` | wires the agents into a sequence |
| `main.py` / `app.py` | CLI and Streamlit entry points |
| `steps.md` | build walkthrough |

**Recognise the shape?** Search → Read → Write → Critique is almost exactly **Module 13's** `plan → research → write → edit`. Module 13 rebuilds it as a graph with a real subgraph and a capped revision loop. Comparing the two files side by side is the single most useful thing you can do in this module.

The dependency list (`langchain>=1.4.3`, `langgraph>=1.2.12`, `langchain-groq`, `langchain-tavily`, `beautifulsoup4`) shows the transition already happening — LangGraph is present even here.

---

## Expected output

- **Single:** an answer that used at least one tool.
- **Multi:** a short research write-up, having searched the web, read pages, drafted and critiqued.

---

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `GroqError: api_key must be set` | no `.env` in *that* project folder | `cp .env.example .env` and fill it in |
| `model ... does not exist` / decommissioned | hardcoded Groq model has been retired | **most likely failure here** — see [`../AGENT_RULES.md`](../AGENT_RULES.md) #1 and check the live model list |
| `Did not find tavily_api_key` | Tavily key missing, read at construction time | add `TAVILY_API_KEY` |
| `ModuleNotFoundError: src...` | run from the wrong directory | run from the project root, not from `src/` |
| Deprecation warnings from LangChain | this module predates the 1.x API | expected; the rest of the course uses the current API |

> ⚠️ **This is the module most likely to be bit-rotten.** It was written against an earlier LangChain and uses older Groq model names. If it won't run, that is *information*, not your failure — it's the exact problem [`../AGENT_RULES.md`](../AGENT_RULES.md) documents. Don't spend a day fixing it; note what broke and move to Module 4.

---

## Exercises

1. Open `src/pipelines/pipeline.py` and write down, in order, what runs. Then open `Module 13/main.py` and do the same. Which was easier to read?
2. Find where control flow is decided in the multi-agent project. Compare with Module 5's `add_conditional_edges` / `Command(goto=...)`.
3. Count the retry/stop conditions in the critic step. Compare with Module 13's `max_iteration` + `recursion_limit`.
4. **After Module 13:** come back and rebuild the Search→Reader half as a LangGraph subgraph. That's the clearest possible before/after.

---

**Next: Module 4.** That's where the course's real foundation starts, and where verified working code begins.
