import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b")


def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)
bot = graph.compile(checkpointer=InMemorySaver())

if __name__ == "__main__":
    # run_name / tags / metadata are purely for making traces findable in the LangSmith UI.
    cfg = {
        "configurable": {"thread_id": "traced-1"},
        "run_name": "demo_chat_turn",
        "tags": ["module-6", "demo"],
        "metadata": {"user": "aakif"},
    }
    out = bot.invoke({"messages": [HumanMessage("Why is the sky blue?")]}, cfg)
    print(out["messages"][-1].content)

    if os.getenv("LANGSMITH_TRACING") == "true" and os.getenv("LANGSMITH_API_KEY"):
        project = os.getenv("LANGSMITH_PROJECT", "default")
        print(f"\nTraced. Open smith.langchain.com -> project '{project}'.")
        print("Filter by tag 'module-6' or metadata user=aakif to find this run.")
    else:
        print("\nTracing is OFF. To turn it on, add to .env:")
        print("  LANGSMITH_TRACING=true")
        print("  LANGSMITH_API_KEY=<your key from smith.langchain.com>")
        print("  LANGSMITH_PROJECT=agentic-ai-course")
        print("The graph code does not change at all — tracing is pure configuration.")
