import os
import sqlite3
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver

from tools import ALL_TOOLS

load_dotenv()

SYSTEM = SystemMessage(content=(
    "You are a helpful assistant with tools.\n"
    "- `calculator` for math — always use it instead of doing arithmetic yourself.\n"
    "- `tavily_search` for current events or facts you're unsure of.\n"
    "- `search_docs` for questions about the user's uploaded PDF — always cite page numbers.\n"
    "- `send_email` to send email. Call it directly with a body you write yourself; never "
    "reply with a plain-text draft and never ask the user to confirm, because an approval "
    "step already exists.\n"
    "Answer directly when no tool is needed."
))

DB_PATH = os.getenv("CHECKPOINT_DB", "chatbot.db")

# Budget cap (added in Module 15's harness audit — see Module 15/HARNESS_REVIEW.md).
# Counted per thread and checkpointed with the rest of state, so it survives restarts.
# Set high to effectively disable, which is what the pre-fix behaviour was.
MAX_LLM_CALLS_PER_THREAD = int(os.getenv("MAX_LLM_CALLS_PER_THREAD", "12"))

llm = init_chat_model("groq:openai/gpt-oss-120b").bind_tools(ALL_TOOLS)


class ChatState(MessagesState):
    llm_calls: int


def chat_node(state: ChatState) -> dict:
    used = state.get("llm_calls", 0)
    if used >= MAX_LLM_CALLS_PER_THREAD:
        # Refuse *before* spending anything. This also caps a runaway chat->tools->chat
        # loop, since every pass through this node costs one model call.
        return {
            "messages": [
                AIMessage(
                    f"This conversation has reached its budget of "
                    f"{MAX_LLM_CALLS_PER_THREAD} model calls. Start a new thread to continue."
                )
            ]
        }

    msgs = state["messages"]
    if not isinstance(msgs[0], SystemMessage):
        msgs = [SYSTEM, *msgs]
    return {"messages": [llm.invoke(msgs)], "llm_calls": used + 1}


graph = StateGraph(ChatState)
graph.add_node("chat", chat_node)
graph.add_node("tools", ToolNode(ALL_TOOLS))
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn)
agent = graph.compile(checkpointer=checkpointer)


def all_thread_ids() -> list[str]:
    return sorted({c.config["configurable"]["thread_id"] for c in checkpointer.list(None)})


def pending_approval(thread_id: str) -> dict | None:
    """The draft a human still has to approve on this thread, or None."""
    snapshot = agent.get_state({"configurable": {"thread_id": thread_id}})
    found = [i for task in snapshot.tasks for i in task.interrupts]
    return found[0].value if found else None
