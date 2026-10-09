# Project context: LangChain agents with uv (macOS)

Portable context for AI-agent projects. Reference project:
`/Users/shaikyasin/Documents/AI/courses/Agentic AI course (FCC)/Module 3 — Agents with LangChain (Single & Multi-Agent)/Single AI Agent System`
(see `project/code.ipynb`, `project/app.py`, `steps.docx` there).

## How I like to work
- I'm learning agentic AI; explain step by step: concept first, then code, with an old -> new mapping when updating course code.
- Course material uses old LangChain 0.x. Always rewrite it to the latest LangChain 1.x API, don't use `langchain-classic`.
- Keep code well structured and formatted, with section headers (`# ==== CONFIG ====` style).
- No git tracking unless I ask.

## Environment rules (uv)
- uv manages everything; `pyproject.toml` is the only source of truth, `uv.lock` pins versions.
- Change packages only with `uv add` / `uv remove`. Never `pip install` or `uv pip install -r requirements.txt` into `.venv` (that downgraded LangChain to 0.1.x and broke langgraph once).
- Broken env -> `uv sync` (or `rm -rf .venv && uv sync`).
- `requirements.txt` only if needed, generated: `uv export --no-hashes --no-dev --no-emit-project -o requirements.txt`.
- Notebooks need `ipykernel` in the project; pick the `.venv` kernel in VS Code. A 0-byte `.ipynb` is invalid.
- VS Code keeps an open notebook in memory: after the file changes on disk, use "File: Revert File" rather than Save.
- Anaconda `(base)` can shadow `.venv`: `conda deactivate`.

## Secrets
- `.env` in project root (gitignored), `.env.example` with blank values.
- Load with `load_dotenv(find_dotenv(usecwd=True))` (works from subfolders/notebooks).
- Keys used: `GROQ_API_KEY` (set, free), `TAVILY_API_KEY` (set), `OPENAI_API_KEY` (not set), `GOOGLE_API_KEY`, `WEATHERSTACK_API_KEY`, `HF_TOKEN`.

## LangChain 1.x cheat sheet (old -> new)
| Old (0.x) | New (1.x) |
|---|---|
| `ChatOpenAI(model="gpt-3.5-turbo")` | `init_chat_model("openai:gpt-4o-mini")` or `"groq:openai/gpt-oss-120b"` |
| `langchain_community...TavilySearchResults` | `from langchain_tavily import TavilySearch` |
| `hub.pull("hwchase17/react")` | not needed (native tool calling); use `system_prompt=` |
| `create_react_agent` + `AgentExecutor` | `from langchain.agents import create_agent` |
| `executor.invoke({"input": q})["output"]` | `agent.invoke({"messages": [("user", q)]})["messages"][-1].content` |
| `max_iterations=` | `config={"recursion_limit": N}` |
| `verbose=True` | `agent.stream(..., stream_mode="values")` + `msg.pretty_print()` |
| `initialize_agent`, `from langchain.llms import ...` | removed; use provider packages (`langchain_openai`, `langchain_groq`, ...) |

## Known gotchas
- Groq retired `llama-3.3-70b-versatile`; use `groq:openai/gpt-oss-120b` (tool calling works). Check live list: `groq.Groq().models.list()`.
- Groq free tier: 8000 tokens/min. A failing tool (e.g. missing key) makes the agent loop on searches -> 429 rate limit looks like a hang. Always set `recursion_limit` and add "If a tool returns an error, tell the user instead of retrying" to the system prompt.
- Custom tools: `@tool`, docstring written for the LLM, `requests` with `params=` and `timeout=`, return errors as strings.
- `langchain-community` sunset warning is harmless; prefer dedicated integration packages.

## Streamlit pattern (see reference `project/app.py`)
- Sections: CONFIG -> TOOLS -> AGENT -> UI.
- `@st.cache_resource` for the agent (Streamlit reruns the script on every interaction).
- Chat history in `st.session_state.messages`, passed to the agent each turn.
- Sidebar: model picker + key status; `st.error` + `st.stop()` if required keys are missing.
- `st.status` to show tool calls live; run with `uv run streamlit run project/app.py`.
- Test headless: `streamlit.testing.v1.AppTest.from_file("project/app.py").run()`.

## New project bootstrap
```
uv init --python 3.12 --vcs none   # uv creates a git repo by default
uv add langchain langchain-core langgraph langchain-community langchain-groq langchain-openai \
       langchain-tavily python-dotenv requests ipykernel streamlit
cp "<reference project>/.env.example" .env   # fill keys
```
