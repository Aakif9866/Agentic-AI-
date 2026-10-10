# Single AI Agent System

One agent, two tools: web search (Tavily) and current weather (WeatherStack). A Streamlit chat UI.

## Run

```bash
uv sync
uv run streamlit run project/app.py
```

`main.py` is **not** the entry point — it only prints this command. The agent needs a chat UI for its conversation loop.

## Keys

| Key | Purpose |
|---|---|
| `GROQ_API_KEY` | the model (`groq:openai/gpt-oss-120b`) |
| `TAVILY_API_KEY` | the web-search tool |
| `WEATHERSTACK_API_KEY` | the weather tool |

Copy `../../.env.example` to `.env` here and fill in those three.

## What's in here

| Path | Role |
|---|---|
| `project/app.py` | the agent + tools + Streamlit UI |
| `project/code.ipynb` | the exploratory notebook it grew from |
| `main.py` | prints the correct run command |

## Status

Verified 2026-10-10: dependencies install, imports resolve, and the Streamlit app boots clean (HTTP 200, no errors in log). Uses the current LangChain 1.x API — `create_agent`, `langchain_tavily`, `init_chat_model` — not the deprecated `AgentExecutor`/`initialize_agent`.

The UI has **not** been clicked through end to end, so a live agent turn is unverified.

See [`../NOTES.md`](../NOTES.md) for how this module fits the course, and [`../../AGENT_RULES.md`](../../AGENT_RULES.md) for the pitfalls that apply repo-wide.
