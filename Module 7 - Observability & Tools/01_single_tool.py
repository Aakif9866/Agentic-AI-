import re
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

SAFE_EXPR = re.compile(r"[0-9.\s+\-*/%()]+")


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression. Numbers and + - * / % ( ) ** only, e.g. '2**10'."""
    if not SAFE_EXPR.fullmatch(expression):
        return "error: only numbers and + - * / % ( ) are allowed"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        # Return the error as text so the model can see it and retry, instead of crashing the graph.
        return f"error: {e}"


tools = [calculator]
llm = init_chat_model("groq:openai/gpt-oss-120b").bind_tools(tools)


def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition)  # -> "tools" if the model asked, else END
graph.add_edge("tools", "chat")
agent = graph.compile(checkpointer=InMemorySaver())

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "t1"}}
    out = agent.invoke({"messages": [("user", "What's 17% of 2340, then add 50?")]}, cfg)
    print("Answer:", out["messages"][-1].content)

    print("\nFull message trail (this is the tool-calling loop):")
    for m in out["messages"]:
        tag = getattr(m, "type", "?")
        if getattr(m, "tool_calls", None):
            print(f"  {tag}: asked for tool -> {m.tool_calls[0]['name']}({m.tool_calls[0]['args']})")
        else:
            print(f"  {tag}: {str(m.content)[:80]}")
