"""A LangGraph agent that gets its tools from the MCP server over stdio.

    uv run python client.py

This module is async, unlike every earlier one: MCP's client is async, so
the agent must be driven with `await agent.ainvoke(...)`.
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

load_dotenv()

SERVER = Path(__file__).parent / "notes_server.py"


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "notes": {
                # sys.executable = this venv's python, so the subprocess can import mcp.
                # Absolute path, because the subprocess's cwd is not guaranteed.
                "command": sys.executable,
                "args": [str(SERVER)],
                "transport": "stdio",
            }
        }
    )

    # client.get_tools() opens a NEW stdio session (= new subprocess) per tool call,
    # so the server's in-memory notes are lost between calls. Holding one session
    # open keeps a single server process alive for the whole conversation.
    async with client.session("notes") as session:
        tools = await load_mcp_tools(session)
        print(f"Tools discovered over MCP: {[t.name for t in tools]}\n")

        agent = create_agent(
            init_chat_model("groq:openai/gpt-oss-120b", temperature=0),
            tools,
            system_prompt=(
                "You manage the user's notes with the add_note and search_notes tools. "
                "Always use the tools — never claim to remember notes yourself."
            ),
        )

        # One conversation: save two notes, then search for one of them.
        for turn in [
            "Save a note: the Goa trip budget is 15000 rupees.",
            "Save a note: remember to renew my passport in March.",
            "Search my notes for anything about the budget.",
        ]:
            result = await agent.ainvoke({"messages": [("user", turn)]})
            used = [c["name"] for m in result["messages"] for c in getattr(m, "tool_calls", []) or []]
            print(f"> {turn}")
            print(f"  tools used: {used or 'none'}")
            print(f"  {result['messages'][-1].content}\n")


if __name__ == "__main__":
    asyncio.run(main())
