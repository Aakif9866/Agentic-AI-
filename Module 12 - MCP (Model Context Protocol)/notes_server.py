"""An MCP server exposing two note tools.

Run directly for Claude Desktop/Cursor, or let client.py launch it as a
stdio subprocess.

    uv run python notes_server.py

IMPORTANT: over stdio, stdout IS the protocol channel. A stray print()
corrupts the stream and the client will fail to connect. Log to stderr.
"""
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes")

# In-memory on purpose — this module is about the protocol, not persistence.
NOTES: list[str] = []


@mcp.tool()
def add_note(text: str) -> str:
    """Save a note for the user. Use this whenever they want something remembered."""
    NOTES.append(text)
    print(f"[server] stored note #{len(NOTES)}", file=sys.stderr)  # stderr, never stdout
    return f"Saved note #{len(NOTES)}: {text}"


@mcp.tool()
def search_notes(keyword: str) -> str:
    """Search saved notes for a keyword and return the ones that match."""
    if not NOTES:
        return "No notes have been saved yet."
    hits = [n for n in NOTES if keyword.lower() in n.lower()]
    if not hits:
        return f"No notes matched '{keyword}'. {len(NOTES)} note(s) stored."
    return "\n".join(f"- {n}" for n in hits)


if __name__ == "__main__":
    # stdio: the client starts this file as a subprocess and talks over pipes.
    # Use transport="streamable-http" instead to serve it over a network.
    mcp.run(transport="stdio")
