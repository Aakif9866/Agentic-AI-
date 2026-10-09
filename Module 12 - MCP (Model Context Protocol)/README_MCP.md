# Registering this server with Claude Desktop / Cursor

The point of MCP is that **one server works in many clients**. `client.py` proves it from a LangGraph agent. This file is the other half: the same server, no code changes, inside Claude Desktop.

## 1. Config file location

| Client | Path |
|---|---|
| **Claude Desktop (macOS)** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Claude Desktop (Windows)** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Cursor** | Settings → MCP → Add Server (same JSON shape) |

## 2. The JSON block

Paste this (merge into `mcpServers` if the file already has entries). Both paths are **absolute on purpose** — Claude Desktop does not launch the server from this directory.

```json
{
  "mcpServers": {
    "notes": {
      "command": "/Users/shaikyasin/Documents/AI/courses/Agentic AI course (FCC)/Module 12 - MCP (Model Context Protocol)/.venv/bin/python",
      "args": [
        "/Users/shaikyasin/Documents/AI/courses/Agentic AI course (FCC)/Module 12 - MCP (Model Context Protocol)/notes_server.py"
      ]
    }
  }
}
```

**Use the venv's python**, not `python3`. The system python can't `import mcp`, and the failure shows up as a silently missing server rather than a useful error.

## 3. Restart and test

1. **Fully quit** Claude Desktop (⌘Q — closing the window is not enough) and reopen it.
2. Look for the tools/plug icon in the chat input — `notes` should be listed.
3. Ask: *"Add a note that I need to buy milk."* Then: *"Search my notes for milk."*

That is the actual proof the protocol works: a tool you wrote for a Python agent, now usable from an app you didn't write.

## 4. If the server doesn't appear

| Symptom | Cause |
|---|---|
| Server missing entirely | Bad path, or you used system `python`. Try running the `command` + `args` by hand in a terminal — it should start and wait silently. |
| Server appears then disappears | The server crashed. Check `~/Library/Logs/Claude/mcp*.log`. |
| Tools listed but every call errors | Something is writing to **stdout**. Over stdio, stdout is the protocol channel — a stray `print()` corrupts it. Log to stderr. |

## 5. stdio vs streamable-http — when to use which

```python
mcp.run(transport="stdio")            # what this server uses
mcp.run(transport="streamable-http")  # the alternative
```

| | `stdio` | `streamable-http` |
|---|---|---|
| **How** | Client launches the server as a **subprocess**, talks over stdin/stdout pipes | Server runs independently; client connects to a **URL** |
| **Where** | Same machine as the client | Anywhere — another host, a container, the cloud |
| **Lifecycle** | One server process per client; dies with the client | Long-lived; serves many clients at once |
| **Auth** | None needed — it's a local subprocess you launched | You must handle auth; it's a network service |
| **Use it for** | Local tools: files, git, a local DB, personal notes | Shared team tools, anything behind an API key you don't want on every laptop |

Rule of thumb: **stdio for personal/local tools, streamable-http when more than one person or machine needs the same server.** This module uses stdio because the notes live in one process on your laptop.
