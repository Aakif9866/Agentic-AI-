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
    cfg = {"configurable": {"thread_id": "aakif-1"}}

    bot.invoke({"messages": [HumanMessage("Hi, I'm Aakif.")]}, cfg)
    reply = bot.invoke({"messages": [HumanMessage("What's my name?")]}, cfg)
    print("Same thread remembers:", reply["messages"][-1].content)

    other_cfg = {"configurable": {"thread_id": "someone-else"}}
    reply2 = bot.invoke({"messages": [HumanMessage("What's my name?")]}, other_cfg)
    print("\nDifferent thread doesn't:", reply2["messages"][-1].content)

    snapshot = bot.get_state(cfg)
    print(f"\nLatest state holds {len(snapshot.values['messages'])} messages")

    history = list(bot.get_state_history(cfg))
    print(f"Checkpoints saved for this thread: {len(history)}")

    # Time travel: rewind to an earlier checkpoint and continue from there.
    earlier = history[1].config
    replayed = bot.invoke(None, earlier)  # None = "resume from this checkpoint", not new input
    print("\nReplayed from an earlier checkpoint:", replayed["messages"][-1].content)
