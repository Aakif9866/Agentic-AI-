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
    """Evaluate an arithmetic expression. Numbers and + - * / % ( ) ** only."""
    if not SAFE_EXPR.fullmatch(expression):
        return "error: only numbers and + - * / % ( ) are allowed"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


@tool
def get_fact(topic: str) -> str:
    """Return one fun fact about a topic (mocked, no API needed)."""
    facts = {
        "python": "Python was named after Monty Python's Flying Circus, not the snake.",
        "docker": "Docker containers share the host kernel, which is why they start in milliseconds.",
    }
    return facts.get(topic.lower(), f"No fact on file for '{topic}'.")


tools = [calculator, get_fact]

# Model choice matters for THIS lesson. openai/gpt-oss-120b serializes: it calls one
# tool, waits, then calls the next. qwen emits both tool_calls in a single turn, which
# is what lets ToolNode run them together. The graph is identical either way — whether
# tools run in parallel is the model's decision, not the graph's.
llm = init_chat_model("groq:qwen/qwen3.8-27b").bind_tools(tools)


def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")
agent = graph.compile(checkpointer=InMemorySaver())

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "t3"}}
    out = agent.invoke(
        # Big ugly numbers on purpose: the model can't do this in its head, so it
        # must call the calculator — and it needs get_fact in the same turn.
        {"messages": [("user", "What's 18473 * 29361? Also give me a fact about Docker.")]}, cfg
    )

    # The interesting part: ONE AIMessage should contain TWO tool_calls.
    for m in out["messages"]:
        calls = getattr(m, "tool_calls", None)
        if calls:
            print(f"One model turn requested {len(calls)} tool(s) at once:")
            for c in calls:
                print(f"  - {c['name']}({c['args']})")

    print("\nAnswer:", out["messages"][-1].content)
