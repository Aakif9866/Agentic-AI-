# Module 12 — MCP (Model Context Protocol)

The first module where a tool lives **outside** your program.

## Run it

```bash
uv sync
uv run python client.py
```

Then do the Claude Desktop half — see `README_MCP.md`. That part is the actual point of the module.

---

## The problem MCP solves

Every tool you've written so far was trapped. `search_docs` only existed inside Module 8. `calculator` only existed inside Module 7. To use one from Claude Desktop, or Cursor, or a teammate's agent, you'd rewrite it.

MCP is a **standard shape for tools**. Write a tool once as an MCP server, and any MCP-aware client can call it:

```
                    ┌─ your LangGraph agent  (client.py)
notes_server.py ────┼─ Claude Desktop        (README_MCP.md)
                    └─ Cursor, or anything else
```

**The server has no idea who's calling it.** That's the whole idea.

---

## 1. `notes_server.py` — the server

Strikingly plain:

```python
mcp = FastMCP("notes")

@mcp.tool()
def add_note(text: str) -> str:
    """Save a note for the user. Use this whenever they want something remembered."""
    NOTES.append(text)
    return f"Saved note #{len(NOTES)}: {text}"

mcp.run(transport="stdio")
```

If that looks like Module 7's `@tool`, that's the point — same idea, one process further out. The docstring is still the prompt the model reads to decide whether to call it (Module 7's lesson, unchanged).

### The one rule that's new: stdout is sacred

Over stdio, the client and server talk **through stdout**. A stray `print()` injects garbage into the protocol stream and the connection breaks — usually with an error that says nothing about printing.

```python
print(f"[server] stored note #{len(NOTES)}", file=sys.stderr)   # stderr, always
```

---

## 2. `client.py` — and the bug worth the whole module

Two things are new versus everything before.

### It's async

MCP's client is async, so the agent must be awaited:

```python
tools = await load_mcp_tools(session)
result = await agent.ainvoke({"messages": [("user", turn)]})
asyncio.run(main())
```

This is where Module 2's async material finally earns its place.

### The bug: tools worked, memory didn't

First version used the obvious call:

```python
tools = await client.get_tools()        # looks right, subtly wrong here
```

It ran without errors. Both notes saved. Then:

> **"Search my notes for anything about the budget."**
> *"I checked your saved notes, but there aren't any entries yet that mention 'budget'."*

Two saves had just succeeded. Nothing errored. The search simply found nothing.

**Cause:** `get_tools()` opens a **new stdio session per tool call** — and a new session means a new **subprocess**, with a fresh empty `NOTES` list. Each `add_note` was saving into a server that then exited. `search_notes` ran in a third, empty one.

**Fix — hold one session open for the whole conversation:**

```python
async with client.session("notes") as session:
    tools = await load_mcp_tools(session)
    agent = create_agent(...)
    for turn in [...]:
        await agent.ainvoke(...)     # all turns share ONE server process
```

Now it works:

```
> Save a note: the Goa trip budget is 15000 rupees.     tools used: ['add_note']
> Save a note: remember to renew my passport in March.  tools used: ['add_note']
> Search my notes for anything about the budget.        tools used: ['search_notes']
  Here are the notes that mention budget:
  - The Goa trip budget is 15000 rupees.
```

**Why this bug matters more than the fix:** nothing crashed. The tools were called correctly, the agent behaved sensibly, and the answer was wrong. A server with state has a **lifetime**, and with stdio that lifetime is the session. If your MCP tools are stateless (a calculator, a search), `get_tools()` is fine. The moment the server remembers anything, session lifetime becomes your problem.

This is also a hint about real design: production MCP servers usually persist to a database precisely so they don't care how often they're restarted.

---

## 3. `create_agent` — the 1.x signature

```python
agent = create_agent(model, tools, system_prompt="...")
```

Confirmed by inspection before writing any code — `(model, tools, system_prompt, middleware, response_format, state_schema)`. **Not** the deprecated `initialize_agent(llm, tools, agent=...)` that most older tutorials show. When an API's shape is uncertain, `inspect.signature()` costs one second and beats guessing.

---

## Verified / not verified

**Verified:** `uv run python client.py` discovers `['add_note', 'search_notes']` over stdio, saves two notes, and retrieves the budget one by keyword.

**Not verified — and it's your half of the module:** registering the server in Claude Desktop and calling `add_note` from its chat. `README_MCP.md` has the exact JSON with your absolute paths. **Don't skip it** — running `client.py` only proves Python can talk to Python. Calling the same server from an app you didn't write is what proves MCP is a protocol rather than a library.

---

## Quick reference

| Thing | Detail |
|---|---|
| Server framework | `FastMCP` from `mcp.server.fastmcp` |
| Tool definition | `@mcp.tool()` + a docstring the model reads |
| Transport here | `stdio` — client spawns the server as a subprocess |
| Client | `MultiServerMCPClient` + `load_mcp_tools(session)` |
| Agent | `create_agent(model, tools, system_prompt=...)`, driven with `ainvoke` |
| **Stateful servers** | **hold `client.session(...)` open**, don't use `get_tools()` per call |
| Logging | stderr only — stdout is the protocol |

## Where to go next

- Swap `NOTES: list` for SQLite. Then `get_tools()` works fine, because state no longer lives in the process — a direct demonstration of the bug above.
- Add `delete_note` and watch it show up in Claude Desktop with **zero** client changes. That's the payoff.
- Run with `transport="streamable-http"` and connect by URL instead — see the comparison table in `README_MCP.md`.
- Wrap Module 8's `search_docs` as an MCP server, and your PDF search becomes usable inside Claude Desktop.
- Point Cursor at the same server: two clients, one server, no new code.
