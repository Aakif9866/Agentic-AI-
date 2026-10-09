"""The graph, deliberately kept free of any web-framework code.

Keeping this separate from api.py means you can import and test the agent
without starting a server, and swap the web layer without touching the graph.
"""
import os
import sqlite3
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b")

DB_PATH = os.getenv("CHECKPOINT_DB", "chatbot.db")


def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn)
agent = graph.compile(checkpointer=checkpointer)


def all_thread_ids() -> list[str]:
    return sorted({c.config["configurable"]["thread_id"] for c in checkpointer.list(None)})
