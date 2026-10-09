import re
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

SYSTEM = SystemMessage(content=(
    "You are a helpful assistant with tools.\n"
    "- Use `calculator` for any math.\n"
    "- Use `tavily_search` only for current events or facts you're unsure of.\n"
    "Answer directly when no tool is needed."
))

SAFE_EXPR = re.compile(r"[0-9.\s+\-*/%()]+")


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression. Numbers and + - * / % ( ) ** only, e.g. '2**10'."""
    if not SAFE_EXPR.fullmatch(expression):
        return "error: only numbers and + - * / % ( ) are allowed"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


web_search = TavilySearch(max_results=3)
tools = [calculator, web_search]
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
    used = [m.tool_calls[0]["name"] for m in out["messages"] if getattr(m, "tool_calls", None)]
    print(f"Q: {question}")
    print(f"   tools used: {used or 'none'}")
    print(f"   A: {out['messages'][-1].content[:250]}\n")


if __name__ == "__main__":
    ask("What's 144 divided by 12?", "math-q")           # should pick calculator
    ask("Who won the most recent F1 world championship?", "news-q")  # should pick search
    ask("What does the word 'agentic' mean?", "plain-q")  # should use no tool at all
