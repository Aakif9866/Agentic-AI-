<div align="center">

# 🤖 Agentic AI — Built, Run, Verified

**A 22-module path from "what even is an agent?" to a deployed multi-agent system.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2.0-FF6F00?style=for-the-badge)
![LangChain](https://img.shields.io/badge/LangChain-1.3.1-1C3C3C?style=for-the-badge)
![uv](https://img.shields.io/badge/uv-managed-DE5FE9?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-free_tier-F55036?style=for-the-badge)

![Built](https://img.shields.io/badge/Modules_4–14-✅_built_&_verified-2EA043?style=flat-square)
![Planned](https://img.shields.io/badge/Modules_15–22-📋_planned-8957E5?style=flat-square)
![Every script runs](https://img.shields.io/badge/every_script-actually_run-0969DA?style=flat-square)

</div>

---

## 👋 Read this first

> **Nothing here is a tutorial you watch.** Every module is code that has actually been executed against live APIs, with the real output recorded. When something didn't work, the failure is written down too — those failure notes are the most useful part of the repo.

**If you are a complete beginner: that's fine.** This README tells you exactly where to start and what to ignore. Jump to [🎯 Where to start](#-where-to-start).

---

## 🎯 Where to start

<div align="center">

### 👉 Start at **Module 4 — LangGraph Fundamentals** 👈

</div>

Not Module 1. Here's the honest reasoning:

| Module | What it is | What to do |
|:--|:--|:--|
| 1️⃣ **Foundations** | Concepts only, no code | 📖 **Skim for 20 min.** Good vocabulary, nothing to run. |
| 2️⃣ **Python Essentials** | `async` + Pydantic | ✅ **Check, don't study.** Can you read `async def` / `await`, and `class X(BaseModel)`? If yes, move on. You'll need it from Module 7. |
| 3️⃣ **LangChain Agents** | The *old* way of building agents | 👀 **Skim only.** This is the approach LangGraph replaced. Useful as contrast, not as a foundation. |
| 4️⃣ **LangGraph Fundamentals** | **State, nodes, edges** | 🚀 **START HERE.** Verified working code + beginner notes. Everything after this is built on it. |

**Why Module 4 maximises what you already know:** you know Python functions and dictionaries. That is genuinely all Module 4 is — a function that takes a dict and returns a dict, plus wiring that says which function runs next. No new mental model required on day one.

### 🗓️ Your first three days

```
Day 1  →  Module 4, files 01–02    State, nodes, edges + your first LLM node
Day 2  →  Module 4, files 03–06    Chaining, parallel + reducers, routing, loops
Day 3  →  Module 6                 Memory — the one that makes it feel like ChatGPT
```

**Right now, in your terminal:**

```bash
cd "Module 4 - LangGraph Fundamentals/project"
uv sync
uv run python 01_temperature.py
```

Look at the output **before** you open the file. Then read [`LEARNPLAN.md`](./LEARNPLAN.md) — it's the method that turns this code into understanding instead of a folder you own.

---

## 🧭 The four phases

```
┌─ 🟢 PHASE 1 · FOUNDATIONS ────────────────────────────────┐
│  M1 concepts   M2 python   M3 old-style agents            │  skim
└───────────────────────────────────────────────────────────┘
                              ↓
┌─ 🔵 PHASE 2 · THE CORE  ⭐ most important ────────────────┐
│  M4 state/nodes/edges  →  M5 routing & loops              │
│  M6 memory & threads   →  M7 tools  →  M8 RAG + approval  │  ← learn properly
└───────────────────────────────────────────────────────────┘
                              ↓
┌─ 🟣 PHASE 3 · SHIPPING ───────────────────────────────────┐
│  M9 Docker/FastAPI  M10 capstone  M11 multi-agent         │
│  M12 MCP  M13 subgraphs  M14 guardrails                   │
└───────────────────────────────────────────────────────────┘
                              ↓
┌─ 🟠 PHASE 4 · PRODUCTION CRAFT ───────────────────────────┐
│  M15 harness  M16 evals  M17 gateway                      │
│  M18/20/22 advanced RAG   M19 serverless   M21 case study │
└───────────────────────────────────────────────────────────┘
```

> 💡 **If you only ever do four modules: 4 → 6 → 7 → 8.** State, memory, tools, retrieval. Almost everything else in this field is a variation on those four, and Module 10 is literally those four stacked together.

---

## 📚 Module index

### 🟢 Phase 1 — Foundations *(skim)*

| # | Module | You learn | Status |
|:-:|:--|:--|:-:|
| 1 | [Agentic AI Foundations](./Module%201%20-%20Agentic%20AI%20Foundations) | LLM → RAG → agents → multi-agent; the ReAct loop | 📖 notes |
| 2 | [Python Essentials](./Module%202%20-%20Python%20Essentials%20-%20Async%20&%20Pydantic) | `asyncio`, concurrent calls, validated output | 📓 notebooks |
| 3 | [Agents with LangChain](./Module%203%20-%20Agents%20with%20LangChain%20%28Single%20&%20Multi-Agent%29) | Tool calling the old way, supervisor pattern | 📓 code |

### 🔵 Phase 2 — The Core ⭐

| # | Module | You learn | Status |
|:-:|:--|:--|:-:|
| 4 | [LangGraph Fundamentals](./Module%204%20-%20LangGraph%20Fundamentals) | **State, nodes, edges, reducers** | ✅ 6 files |
| 5 | [Workflow Patterns](./Module%205%20-%20LangGraph%20Workflow%20Patterns) | `Send` fan-out, `Command` routing, capped loops | ✅ 5 files |
| 6 | [Chatbot: Memory & Streaming](./Module%206%20-%20Agentic%20Chatbot%20-%20Memory,%20Streaming%20&%20Threads) | **Checkpointers, `thread_id`, time travel, SQLite** | ✅ 5 files |
| 7 | [Observability & Tools](./Module%207%20-%20Observability%20&%20Tools) | **`ToolNode`, `tools_condition`, context trimming** | ✅ 4 files |
| 8 | [RAG & Human-in-the-Loop](./Module%208%20-%20RAG%20&%20Human-in-the-Loop) | PDF → FAISS, `interrupt()` + resume | ✅ 6 files |

### 🟣 Phase 3 — Shipping

| # | Module | You learn | Status |
|:-:|:--|:--|:-:|
| 9 | [Deployment](./Module%209%20-%20Deployment%20%28Docker,%20CI-CD,%20Render%29) | FastAPI streaming, Docker *(image verified)*, CI | ✅ built |
| 10 | [Capstone: ChatGPT Agent](./Module%2010%20-%20Project%20-%20Build%20Your%20Own%20ChatGPT%20Agent) | All of Phase 2 + Streamlit UI, 4 tools | ✅ built |
| 11 | [TripMate AI](./Module%2011%20-%20Project%20-%20TripMate%20AI%20%28Multi-Agent%20Travel%20Planner%29) | Supervisor + 3 specialists, `Command(goto=)` | ✅ built |
| 12 | [MCP](./Module%2012%20-%20MCP%20%28Model%20Context%20Protocol%29) | One tool server, many clients, async, stdio | ✅ built |
| 13 | [Subgraphs: AgentWriter](./Module%2013%20-%20LangGraph%20Subgraphs%20+%20Project%20-%20AgentWriter%20AI) | Reusable subgraph + revision loop | ✅ built |
| 14 | [Guardrails + Supervisor](./Module%2014%20-%20Guardrails%20+%20Project%20-%20Multi-Agent%20Supervisor%20System) | 4 middleware layers, **5/5 adversarial eval** | ✅ built |

### 🟠 Phase 4 — Production Craft *(planned — each folder has a full build spec)*

| # | Module | You learn | Status |
|:-:|:--|:--|:-:|
| 15 | [Harness & Loop Engineering](./Module%2015%20-%20Harness%20&%20Loop%20Engineering) | Audit 8 rows, fix the weakest in code | 📋 plan |
| 16 | [Agent Evaluation](./Module%2016%20-%20AI%20Agent%20Evaluation) | 25+ evals, LLM-as-judge, CI gate | 📋 plan |
| 17 | [LLM Gateway](./Module%2017%20-%20LLM%20Gateway) | LiteLLM fallbacks + cost tracking | 📋 plan |
| 18 | [Advanced RAG I](./Module%2018%20-%20Advanced%20RAG%20I%20-%20Corrective%20RAG%20&%20Self-RAG) | CRAG + Self-RAG self-correction | 📋 plan |
| 19 | [Self-Correcting App](./Module%2019%20-%20Project%20-%20Self-Correcting%20Multi-Agent%20App%20%28Serverless%29) | Writer/reviewer loop, serverless | 📋 plan |
| 20 | [Advanced RAG II](./Module%2020%20-%20Advanced%20RAG%20II%20-%20Agentic%20RAG) | Routing RAG on hosted Pinecone | 📋 plan |
| 21 | [Forward Deployed Eng](./Module%2021%20-%20Forward%20Deployed%20Engineering%20-%20Roadmap%20+%202%20Projects) | FDE case study of your own project | 📋 plan |
| 22 | [Advanced RAG III](./Module%2022%20-%20Advanced%20RAG%20III%20-%20GraphRAG%20&%20Multimodal%20RAG) | Neo4j GraphRAG + charts/images | 📋 plan |

---

## 🧰 One-time setup

**1. Install uv** (replaces pip/venv, much faster):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Get free API keys:**

| Key | Where | Needed for |
|:--|:--|:--|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | 🔴 **everything** |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | web search (M7+) |
| `LANGSMITH_API_KEY` | [smith.langchain.com](https://smith.langchain.com) | optional tracing |

**3. Run any module** — each is its own self-contained project:

```bash
cd "Module 4 - LangGraph Fundamentals/project"
uv sync                              # installs exactly the pinned versions
uv run python 01_temperature.py
```

Put your keys in a `.env` inside the module folder. `.env` is gitignored everywhere — **never commit it.**

> ⚠️ **Folder names use ` - `, never `:`** — a colon makes `uv run` fail outright *and* makes `source .venv/bin/activate` silently do nothing (you stay on system Python and get baffling import errors). See [`AGENT_RULES.md`](./AGENT_RULES.md) #5.

---

## 📖 The two docs that matter

| Doc | Read it when |
|:--|:--|
| 🎓 **[LEARNPLAN.md](./LEARNPLAN.md)** | **Now.** How to actually learn this: the run → break → predict loop, how to read a `NOTES.md`, realistic pacing, break-it experiments per module, an error decoder. |
| 🛠️ **[AGENT_RULES.md](./AGENT_RULES.md)** | When building Modules 15–22. Pinned stack + every pitfall already hit. Paste it *with* a module's README when asking a coding agent to build it. |

Every built module also has a **`NOTES.md`** written for a beginner — what each file does, why, and a "Gotchas we hit" section at the end. **Read the gotchas twice:** once now, once when you're stuck.

---

## 🔗 Relationship to the original course

This repo follows [**entbappy/Complete-Agentic-AI-Course**](https://github.com/entbappy/Complete-Agentic-AI-Course) — the official repo for the course. I scanned it and compared structure directly. **The overall idea matches.** Same concepts, same order, same projects:

| Original repo | → | Here |
|:--|:-:|:--|
| `Langchain vs LangGraph` | → | M1 |
| `Asynchronous Programming` + `Pydantic-Validation` | → | M2 |
| `Langchain-Single-Agent` + `LangChain-Multi-Agent-Research-System` | → | M3 |
| `LangGraph-Code/1,2,3,5,7,8_*.ipynb` | → | **M4** *(near-exact 1:1 — temperature, QA, chaining, essay, review, iterative)* |
| `LangGraph-Code/4,6_*.ipynb` + workflow patterns | → | M5 |
| `9_Persistence.ipynb` + `Agentic-Chatbot/*_db_*` | → | M6 |
| `Agentic-Chatbot/*_tool_*` + `tools_demo.ipynb` | → | M7 |
| `10_HITL.ipynb` + `*_rag_*` | → | M8 |
| `Agentic-Chatbot-using-LangGraph/` (full app) | → | M9 + M10 |
| `11_subgraphs` + `12_subgraph_shared` | → | M13 *(the original shows **both** patterns — M13's notes explain why to prefer the explicit one)* |
| `13_guardrails_crash_course.ipynb` | → | M14 |
| `AI_Agent_Evaluation.ipynb` | → | M16 |
| `llm_gateway.ipynb` | → | M17 |
| `Corrective-Rag-CRAG` + `Self-Rag-Code` | → | M18 |
| `Advanced-RAG/Agentic-RAG` | → | M20 |
| `Agentic AI Interview Preparation/` | → | M21 |
| `Advanced-RAG/Graph-RAG` + `Multimodal-RAG` | → | M22 |

**What's different, and why:**

- 📂 **22 small modules instead of 12 topic folders.** Same material, finer-grained, so one module = one sitting.
- 🐍 **`.py` scripts instead of `.ipynb` notebooks.** Runnable with one command, diffable in git, and they *fail loudly* instead of hiding stale state in cell outputs.
- 📦 **`uv` + pinned versions instead of `requirements.txt`.** Reproducible — the reason this code still runs.
- ➕ **Four modules with no counterpart in the original:** M9 (Deployment), M11 (TripMate), **M12 (MCP)**, M15 (Harness), M19 (Serverless). These come from the extended course brief.
- 🔐 **Secrets are gitignored here.** The original has **18 committed artifacts**, including **4 `.env` files**, plus `chatbot.db`, `__pycache__/` and `faiss_db/`. Don't copy that pattern — rotate any key you ever push.

### ⚠️ About "the old code is rotten"

**Your diagnosis is correct, and it's the main reason this repo re-implements rather than copies.** The concepts in the original are sound; the code bit-rots because the ecosystem moves fast. Concretely, what broke while building Modules 4–14:

| 💀 What rotted | What it does now | Fix used here |
|:--|:--|:--|
| `llama-3.3-70b-versatile` | **404 — decommissioned** | `openai/gpt-oss-120b` |
| `mixtral-8x7b-32768` | **410 — decommissioned** | same |
| `with_structured_output(Model)` | errors: *"Tool choice is required, but model did not call a tool"* | `method="json_mode"` + field names in the prompt |
| `langchain_community.tools.tavily_search` | deprecated | `langchain-tavily` |
| `init_chat_model("groq:llama-...")` | dead model behind a live API | live model list, checked |
| `langchain-community` | prints a sunset warning | still correct for FAISS/PyPDF — no official replacement yet |

**The lesson, not the complaint:** never trust a hardcoded model name in any tutorial, including this one. Check what's actually live:

```bash
curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

All of this is collected in [`AGENT_RULES.md`](./AGENT_RULES.md) so you hit each gotcha once, not twice.

---

## 🆘 Stuck?

1. 🔍 Check **"Gotchas we hit"** at the bottom of that module's `NOTES.md`.
2. 📋 Check the error table in [`LEARNPLAN.md`](./LEARNPLAN.md) — `InvalidUpdateError`, `GraphRecursionError`, dead models and friends are all decoded there.
3. 🔁 **Run it again.** Code bugs fail identically every time; model weirdness varies. That one distinction saves hours.
4. 👇 Read the **last** line of the traceback first, not the first.

---

## 🙏 Credits

Concepts and projects in this repo are based on **Boktiar Ahmed Bappy's** Agentic AI course, which explains all of this material.

- 💻 GitHub: [github.com/entbappy](https://github.com/entbappy) · [Complete-Agentic-AI-Course](https://github.com/entbappy/Complete-Agentic-AI-Course)
- 📺 YouTube: [@dswithbappy](https://www.youtube.com/@dswithbappy)
- 🎬 Course playlist: [Complete Agentic AI Course](https://www.youtube.com/watch?v=8pE1krNmqCo&list=PLkz_y24mlSJZ9SFlc9O4Q4Grli5SQDbrB)

---

<div align="center">

### 🚀 Stop reading. Go run the first file.

```bash
cd "Module 4 - LangGraph Fundamentals/project" && uv run python 01_temperature.py
```

*Then break it on purpose. That's the part that teaches.*

</div>
