# Agentic AI

A hands-on path through Agentic AI, from first principles to production. It starts with what an agent is, moves through LangChain and LangGraph, chatbots with memory, RAG and human-in-the-loop, and finishes with deployment, MCP, guardrails, evals and advanced RAG.

Each module has notes, notebooks and working code. Every project is rebuilt from scratch, not copy-pasted.

---

## Start here

| Read this | For |
|---|---|
| **[LEARNPLAN.md](./LEARNPLAN.md)** | **How to actually learn this course** — the run → break → predict method, how to read each `NOTES.md`, pacing, break-it experiments, and what to do when stuck. Start here if you're new to any of this. |
| **[AGENT_RULES.md](./AGENT_RULES.md)** | The pinned tech stack plus every pitfall hit while building Modules 4–10 (dead Groq models, `json_mode`, colons in folder names). Paste it alongside a module's README when asking a coding agent to build it. |

**Modules 4–10 are built and verified** — every script was run against live APIs, and each module has a beginner-level `NOTES.md`. **Modules 11–22 are planned, not built** — each folder holds a `README.md` with the full build spec, acceptance criteria and known pitfalls.

Run any module's code with:

```bash
cd "Module 6 - Agentic Chatbot - Memory, Streaming & Threads"
uv sync
uv run python 01_basic_chatbot.py
```

> Folder names use ` - ` and never `:` — a colon makes `uv run` fail and makes `source .venv/bin/activate` silently do nothing. See `AGENT_RULES.md` #5.

---

## Roadmap

### Part A — Core: Foundations to Deployment

| # | Module | Focus |
|---|--------|-------|
| 1 | [Agentic AI Foundations](./Module%201%20-%20Agentic%20AI%20Foundations) | LLM → RAG → agents → multi-agent, the ReAct loop, workflows vs agents |
| 2 | [Python Essentials: Async & Pydantic](./Module%202%20-%20Python%20Essentials%20-%20Async%20&%20Pydantic) | `asyncio`, concurrent LLM calls, validated structured output |
| 3 | [Agents with LangChain](./Module%203%20-%20Agents%20with%20LangChain%20%28Single%20&%20Multi-Agent%29)) | Tool calling, single agent, supervisor-based multi-agent system |
| 4 | [LangGraph Fundamentals](./Module%204%20-%20LangGraph%20Fundamentals) | State, nodes, edges, reducers, `StateGraph` |
| 5 | [LangGraph Workflow Patterns](./Module%205%20-%20LangGraph%20Workflow%20Patterns) | Sequential, parallel, conditional and iterative graphs |
| 6 | [Agentic Chatbot](./Module%206%20-%20Agentic%20Chatbot%20-%20Memory%2C%20Streaming%20%26%20Threads) | Memory, checkpointers, threads, streaming, DB persistence |
| 7 | [Observability & Tools](./Module%207%20-%20Observability%20%26%20Tools) | LangSmith tracing, `ToolNode`, `tools_condition` |
| 8 | [RAG & Human-in-the-Loop](./Module%208%20-%20RAG%20%26%20Human-in-the-Loop) | Retrieval as a tool, `interrupt()` + `Command(resume=...)` |
| 9 | [Deployment](./Module%209%20-%20Deployment%20%28Docker%2C%20CI-CD%2C%20Render%29) | Docker, GitHub Actions CI/CD, AWS EC2, Render |
| 10 | [Project: ChatGPT-style Agent](./Module%2010%20-%20Project%20-%20Build%20Your%20Own%20ChatGPT%20Agent) | LangGraph + FastAPI + ChromaDB + SQLAlchemy + LangSmith |
| 11 | [Project: TripMate AI](./Module%2011%20-%20Project%20-%20TripMate%20AI%20%28Multi-Agent%20Travel%20Planner%29) | Multi-agent travel planner with Groq, LangGraph, PostgreSQL, FastAPI |

### Part B — Advanced: Production Agent Engineering

| # | Module | Focus |
|---|--------|-------|
| 12 | [Model Context Protocol (MCP)](./Module%2012%20-%20MCP%20%28Model%20Context%20Protocol%29) | Hosts, clients, servers; tools, resources, prompts; stdio vs HTTP |
| 13 | [Subgraphs & Multi-Agent Architecture](./Module%2013%20-%20LangGraph%20Subgraphs%20%2B%20Project%20-%20AgentWriter%20AI) | Subgraphs as nodes, supervisor / hierarchical / swarm designs |
| 14 | [Guardrails & Safety](./Module%2014%20-%20Guardrails%20%2B%20Project%20-%20Multi-Agent%20Supervisor%20System) | Prompt injection, PII, output validation, tool allowlists, HITL |
| 15 | [Harness, Loops, Evals & Gateways](./Module%2015%20-%20Harness%20%26%20Loop%20Engineering) | Context and loop engineering, eval sets in CI, LLM gateway with fallback |
| 16 | [Advanced RAG](./Module%2016%20-%20AI%20Agent%20Evaluation) | CRAG, Self-RAG, Agentic RAG, GraphRAG (Neo4j), Multimodal RAG |
| 17 | [Self-Correcting Agents & Serverless](./Module%2017%20-%20LLM%20Gateway) | Generator/critic loops, serverless trade-offs |
| 18 | [Forward Deployed Engineering](./Module%2018%20-%20Advanced%20RAG%20I%20-%20Corrective%20RAG%20%26%20Self-RAG) | Customer problem → scoped solution → production |

---

## Key Concepts

**Agents**
- An LLM predicts text. An agent is an LLM plus tools, memory and a loop that decides the next step.
- ReAct loop: **Reason → Act → Observe → repeat** until the goal is met.
- In a workflow, you design the steps. In an agent, the LLM picks them. Production systems usually mix both.

**Python for agents**
- `async`/`await` + `asyncio.gather()` run many LLM/tool calls concurrently.
- Pydantic models + `with_structured_output` turn LLM output into JSON you can trust.

**LangGraph**
- Shared typed **state**. **Nodes** are functions and **edges** decide what runs next.
- **Reducers** (`add_messages`, `operator.add`) decide whether updates append or overwrite.
- **Checkpointers** enable memory, resuming, time travel and HITL. `thread_id` = one conversation.
- Four patterns cover almost every design: sequential, parallel, conditional and iterative. Always cap the number of iterations.

**RAG**
- Load → chunk → embed → store → retrieve top-k → generate.
- Retrieval quality and chunking matter more than the model.
- Add correction or reflection (CRAG, Self-RAG) only where an eval set shows failures.

**Production**
- The harness (prompts, tools, context, loop control, error handling, observability) decides how well a model performs.
- Evaluate both the final answer and the tool-call trajectory, and run evals as CI regression tests.
- Guardrails come in layers: cheap deterministic checks first, then LLM judges. Fail closed on risky actions.
- An LLM gateway handles routing, fallback, retries, caching, quotas and cost tracking.
- MCP: write a tool server once and use it from any compatible client.

---

## Repository Structure

```
.
├── Module 1 — Agentic AI Foundations/        # notes
├── Module 2 — Python Essentials: Async & Pydantic/
│   ├── async.ipynb
│   └── pydantic.ipynb
├── Module 3 — Agents with LangChain (Single & Multi-Agent)/
│   ├── Single AI Agent System/               # one agent + custom tools
│   └── Multi-Agent AI System/                # supervisor + specialised agents
│       └── src/{agents,tools,pipelines}/
└── Module 4 … 18/                            # added as completed
```

Each project folder is a standalone `uv` project with its own `README.md`, `pyproject.toml` and `.env.example`.

---

## Getting Started

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/) (or `venv` + `pip`).

```bash
git clone git@github.com:Aakif9866/Agentic-AI-.git
cd "Agentic-AI-/Module 3 — Agents with LangChain (Single & Multi-Agent)/Multi-Agent AI System"

cp .env.example .env      # add your API keys
uv sync
uv run main.py
```

**API keys used across projects** (only the ones a project needs):

| Service | Used for |
|---------|----------|
| Groq | Main LLM (fast, free tier) |
| OpenAI / Gemini | Alternative models, embeddings, vision |
| Tavily | Web search tool |
| LangSmith | Tracing and evaluation |
| Pinecone | Managed vector DB |
| Neo4j | GraphRAG |
| PostgreSQL | Persistence |

> `.env` files are git-ignored. Never commit real keys.

---

## Tech Stack

Python · LangChain · LangGraph · Pydantic · FastAPI · Streamlit · ChromaDB · Pinecone · Neo4j · PostgreSQL · SQLAlchemy · LangSmith · MCP · Docker · GitHub Actions · AWS

---

## Progress

- [x] Module 1 — Foundations
- [x] Module 2 — Async & Pydantic
- [x] Module 3 — Single & Multi-Agent with LangChain
- [ ] Modules 4–11 — LangGraph, chatbot, RAG, HITL, deployment, projects
- [ ] Modules 12–18 — MCP, guardrails, evals, advanced RAG, serverless, FDE

---

## Credits

Concepts and projects in this repo are based on **Boktiar Ahmed Bappy's** Agentic AI course, which explains all of this material.

- GitHub: [github.com/entbappy](https://github.com/entbappy)
- YouTube: [@dswithbappy](https://www.youtube.com/@dswithbappy)
- Course playlist: [Complete Agentic AI Course](https://www.youtube.com/watch?v=8pE1krNmqCo&list=PLkz_y24mlSJZ9SFlc9O4Q4Grli5SQDbrB)
