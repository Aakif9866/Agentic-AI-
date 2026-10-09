from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END, MessagesState

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b")


def chat_node(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)
bot = graph.compile()

if __name__ == "__main__":
    out = bot.invoke({"messages": [("user", "Hi, I'm Aakif.")]})
    print("Turn 1:", out["messages"][-1].content)

    # No checkpointer = no memory. This call starts from nothing.
    out2 = bot.invoke({"messages": [("user", "What's my name?")]})
    print("\nTurn 2 (fresh invoke, no memory):", out2["messages"][-1].content)
