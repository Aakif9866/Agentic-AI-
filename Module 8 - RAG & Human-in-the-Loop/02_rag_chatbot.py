from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver

from rag_shared import search_docs

load_dotenv()

SYSTEM = SystemMessage(content=(
    "You answer questions about the user's ingested PDF using `search_docs`. "
    "Always cite the page number. If the document doesn't cover it, say so plainly. "
    "Don't call the tool for greetings or small talk."
))

tools = [search_docs]
llm = init_chat_model("groq:openai/gpt-oss-120b").bind_tools(tools)


def chat_node(state: MessagesState) -> dict:
    msgs = state["messages"]
    if not isinstance(msgs[0], SystemMessage):
        msgs = [SYSTEM, *msgs]
    return {"messages": [llm.invoke(msgs)]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")
agent = graph.compile(checkpointer=InMemorySaver())


def ask(question: str, thread: str) -> None:
    out = agent.invoke({"messages": [("user", question)]}, {"configurable": {"thread_id": thread}})
    searched = any(getattr(m, "tool_calls", None) for m in out["messages"])
    print(f"Q: {question}")
    print(f"   searched the PDF: {searched}")
    print(f"   A: {out['messages'][-1].content[:300]}\n")


if __name__ == "__main__":
    # Run 01_rag_tool.py first so faiss_db/ exists.
    ask("What does a checkpointer give me, according to the document?", "rag-1")
    ask("Hi there!", "rag-2")  # should NOT hit the vector store
