# Multi-Agent AI System: build steps

A research assistant where 4 workers hand their output to the next one:

```
topic ─► Search agent ─► Reader agent ─► Writer chain ─► Critic chain ─► report + feedback
         (Tavily)        (scrape URL)    (draft .md)     (score /10)
```

**Agent vs chain**
- **Agent** = LLM + tools in a loop. The LLM *decides* which tool to call, reads the result, and repeats until it has an answer. Use one when the steps aren't known in advance.
- **Chain** = `prompt | llm | parser`. A single fixed pass with no decisions. Use one when the input already holds everything the LLM needs.

**Multi-agent here = a pipeline.** Plain Python passes each worker's output to the next. No supervisor, no shared state graph. That's the simplest multi-agent pattern; supervisor and hand-off patterns come later in LangGraph.

---

## 1. Project setup (uv)

```bash
uv init --python 3.12 --vcs none --name multi-agent-ai-system
uv add langchain langchain-core langgraph langchain-groq groq langchain-tavily \
       python-dotenv requests beautifulsoup4 ipykernel streamlit
cp "../Single AI Agent System/.env.example" .env   # fill GROQ_API_KEY, TAVILY_API_KEY
```

## 2. Folder layout

```
Multi-Agent AI System/
├── .env / .env.example        keys (GROQ_API_KEY, TAVILY_API_KEY)
├── pyproject.toml / uv.lock   dependencies (uv)
├── main.py                    CLI entry:  uv run main.py
├── app.py                     Streamlit UI: uv run streamlit run app.py
├── code.ipynb                 run each agent cell by cell
└── src/
    ├── tools/tools.py         web_search (Tavily), scrape_url (requests + BeautifulSoup)
    ├── agents/agents.py       llm, build_search_agent, build_reader_agent, writer_chain, critic_chain
    └── pipelines/pipeline.py  search_step, reader_step, writer_step, critic_step, run_research_pipeline
```

Dependencies only point downward: `app/main → pipeline → agents → tools`.
No `__init__.py` files are needed: Python 3 treats plain folders as packages (namespace packages), so `from src.agents.agents import ...` works when you run from the project root.

## 3. Tools: `src/tools/tools.py`
- `web_search = TavilySearch(max_results=3)`: a ready-made LangChain tool.
- `scrape_url`: a custom `@tool`. Its docstring is the description the LLM reads. It uses `requests.get(..., timeout=15)`, BeautifulSoup removes `<script>`, `<nav>` and similar tags, and the text is cut to 4000 chars (Groq free tier = 8k tokens/min). Errors come back as **strings** so the agent can report them instead of crashing.
- `load_dotenv()` lives here because `TavilySearch()` reads its key **at creation**, and this is the first module imported.

## 4. Agents and chains: `src/agents/agents.py`
- One shared `llm = init_chat_model("groq:openai/gpt-oss-120b", max_retries=5)`.
- `create_agent(llm, tools=[...], system_prompt=...)` builds each agent.
- `.with_config({"recursion_limit": 15})` stops a looping agent (each tool call costs 2 steps).
- `.with_retry(retry_if_exception_type=(BadRequestError,))`: gpt-oss on Groq sometimes emits a malformed tool call (400 `tool_use_failed`). It's random, so rerunning fixes it.
- Chains: `ChatPromptTemplate | llm | StrOutputParser()` → `.invoke({...})` returns a plain `str`.

## 5. Pipeline: `src/pipelines/pipeline.py`
- One function per step, so `main.py` and `app.py` share exactly the same logic.
- **Bug fixed from the course code:** the reader got `search[:800]`, but the URLs sit at the *end* of the search summary, so the reader never saw one and replied "please give me a URL". Now the URLs are extracted with a regex and passed in explicitly.

## 6. UI: `app.py` (sections CONFIG → STYLE → HELPERS → STATE → UI)
- Step cards are drawn into `st.empty()` placeholders, so they update **live** (waiting → running → done) during the run. In the course version they stayed "waiting" until the end.
- The pipeline runs directly when the button is clicked. The course's `running`/`done` flags + `st.rerun()` dance is gone, and so is the risk of a step that errors leaving `running=True` forever.
- `try/except` → `st.error(...)` if a step fails (rate limit, network).
- Raw agent text is `html.escape`d before it goes into an HTML `<div>`.
- `st.container(border=True)` replaces `<div>` tags that were opened and closed in separate `st.markdown` calls (Streamlit renders each call on its own, so those divs were empty boxes).
- `use_container_width=True` → `width="stretch"` (newer Streamlit).

## 7. Run
```bash
uv run main.py                     # terminal, prints all 4 outputs (~2 min)
uv run streamlit run app.py        # web UI
```
Test headless:
```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=400).run()
at.text_input[0].input("Latest AI agent frameworks in 2026"); at.button[0].click().run()
print(list(at.session_state.results))   # ['search', 'reader', 'writer', 'critic']
```

---

## Old (course, LangChain 0.x) → New (1.x) mapping

| Course / old | This project |
|---|---|
| `ChatGroq(model=...)` / `ChatOpenAI(...)` | `init_chat_model("groq:openai/gpt-oss-120b")` |
| `TavilySearchResults` (langchain_community) | `TavilySearch` (langchain_tavily) |
| `create_react_agent` + `AgentExecutor` + `hub.pull` prompt | `create_agent(llm, tools, system_prompt=...)` |
| `executor.invoke({"input": q})["output"]` | `agent.invoke({"messages": [("user", q)]})["messages"][-1].content` |
| `max_iterations=` | `.with_config({"recursion_limit": N})` |
| `LLMChain(llm, prompt).run(...)` | `prompt \| llm \| StrOutputParser()` then `.invoke({...})` |
| `verbose=True` | `agent.stream(..., stream_mode="values")` + `msg.pretty_print()` (see notebook) |
