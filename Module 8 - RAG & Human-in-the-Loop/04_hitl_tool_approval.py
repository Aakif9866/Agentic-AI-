from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

load_dotenv()


@tool
def purchase_stock(symbol: str, quantity: int) -> dict:
    """Buy shares of a stock. Requires human approval before executing."""
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}? (yes/no)")
    if str(decision).lower() != "yes":
        return {"status": "cancelled", "reason": "declined by human",
                "symbol": symbol, "quantity": quantity}
    # The real side effect lives AFTER the interrupt, so a resume can't double-execute it.
    return {"status": "success", "symbol": symbol, "quantity": quantity}


tools = [purchase_stock]
llm = init_chat_model("groq:openai/gpt-oss-120b").bind_tools(tools)


def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "chat")
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")
agent = graph.compile(checkpointer=InMemorySaver())


def run(answer: str, thread: str) -> None:
    cfg = {"configurable": {"thread_id": thread}}
    result = agent.invoke({"messages": [("user", "Buy 10 shares of AAPL for me.")]}, cfg)
    if "__interrupt__" not in result:
        print("No approval was requested:", result["messages"][-1].content[:150])
        return
    print(f"Paused inside the tool, asking: {result['__interrupt__'][0].value}")
    final = agent.invoke(Command(resume=answer), cfg)
    print(f"Human said '{answer}' -> {final['messages'][-1].content[:200]}\n")


if __name__ == "__main__":
    run("yes", "hitl-2-approved")
    run("no", "hitl-2-declined")
