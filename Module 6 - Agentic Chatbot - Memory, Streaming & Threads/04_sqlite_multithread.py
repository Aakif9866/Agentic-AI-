import sqlite3
import uuid
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b")


def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

# check_same_thread=False is required when a web framework (Streamlit, FastAPI)
# touches the same connection from different threads.
conn = sqlite3.connect("chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
bot = graph.compile(checkpointer=checkpointer)


def all_thread_ids() -> list[str]:
    """Every thread_id that has at least one checkpoint in chatbot.db."""
    return sorted({c.config["configurable"]["thread_id"] for c in checkpointer.list(None)})


def history_for(thread_id: str) -> list[tuple[str, str]]:
    cfg = {"configurable": {"thread_id": thread_id}}
    msgs = bot.get_state(cfg).values.get("messages", [])
    return [("user" if m.type == "human" else "assistant", m.content) for m in msgs]


if __name__ == "__main__":
    thread_id = str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}

    bot.invoke({"messages": [HumanMessage("What's the capital of Japan?")]}, cfg)
    bot.invoke({"messages": [HumanMessage("And its population?")]}, cfg)

    threads = all_thread_ids()
    print(f"Threads stored in chatbot.db: {len(threads)}")
    for t in threads:
        print("  -", t)

    print(f"\nHistory for this run's thread ({thread_id[:8]}...):")
    for role, text in history_for(thread_id):
        print(f"  {role}: {text[:90]}")

    print("\nRun this file again — the thread count grows, because SQLite survives restarts.")
