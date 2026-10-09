# Module 12 — MCP (Model Context Protocol)

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

Build **one** MCP server and call it from **two different clients** (your LangGraph agent *and* Claude Desktop/Cursor) — proving the protocol really does make tools reusable across apps.

## Why this module exists

Up to now, every tool you wrote was locked inside one Python script. MCP is a standard that lets a tool live in its own process and be used by *any* MCP-aware app. That's the whole point: write `add_note` once, use it from your agent, from Claude Desktop, from Cursor.

**This is the module where the "proof" step is the actual lesson.** Running `client.py` is easy. Registering the server in Claude Desktop and calling it from there is what demonstrates MCP exists for a reason.

## Setup

```bash
cd "Module 12 - MCP (Model Context Protocol)"
uv init --no-readme --name module12-mcp --python 3.12
rm main.py
uv add mcp langchain-mcp-adapters langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv
cp "../Module 10 - Project - Build Your Own ChatGPT Agent/.env" .env
```

## Files to create

```
notes_server.py   the MCP server (FastMCP) with add_note + search_notes
client.py         LangGraph agent connecting over stdio
README_MCP.md     the claude_desktop_config.json snippet + transport explainer
NOTES.md          your own notes afterwards
```

## Requirements

- **`notes_server.py`** using `FastMCP` with at least two tools: `add_note`, `search_notes`. In-memory storage (a dict or list) is fine — this module is about the protocol, not persistence.
- **`client.py`** using `langchain-mcp-adapters`' `MultiServerMCPClient`:
  - connect over **stdio**
  - `await client.get_tools()`
  - run an **async** agent (`create_agent` + `await agent.ainvoke(...)`)
  - one conversation that saves a note *and then* searches for it
- **`claude_desktop_config.json` snippet** in a README (just the JSON block as documentation — do not auto-install it).
- A comment block explaining **when to use `stdio` vs `streamable-http`**: stdio = local subprocess on the same machine; streamable-http = server runs remotely / is shared.

## Acceptance criteria

- [ ] `uv run python client.py` round-trips: saves a note, retrieves it by keyword, prints to console.
- [ ] **You** (not the agent) add the server to Claude Desktop's MCP config and successfully call `add_note` from Claude Desktop's own chat. Skipping this skips the module's point.

## Pitfalls specific to this module

- **This module is `async`, unlike everything before it.** `client.py` needs `asyncio.run(main())` and `await` on the agent. Mixing sync `invoke` with MCP's async client is the most common first failure.
- **stdio means the server is launched as a subprocess by the client**, so the server's command/args in the config must be absolute paths or resolvable from the client's working directory. "It works in my terminal but not in Claude Desktop" is almost always this.
- Claude Desktop's config lives at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS. You must **fully restart** Claude Desktop after editing it.
- The server must write **nothing** to stdout except MCP protocol messages. A stray `print()` in your server corrupts the stream — use `logging` to stderr instead.

## Further steps & ideas

- Swap in-memory storage for SQLite so notes survive restarts.
- Add a third tool `delete_note` and see it appear in Claude Desktop without touching the client.
- Point the same server at Cursor as well — two clients, one server, zero code changes.
- Try `streamable-http`: run the server with an HTTP transport and connect from `MultiServerMCPClient` over a URL. That's how you'd share one tool server with a team.
- Wrap a tool you already own (Module 8's `search_docs`) as an MCP server so your PDF search works inside Claude Desktop.
