from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessageChunk
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
    question = {"messages": [HumanMessage("Explain RAG in 2 sentences.")]}

    print("--- stream_mode='messages' (token by token, what a chat UI shows) ---")
    for chunk, meta in bot.stream(question, {"configurable": {"thread_id": "s1"}}, stream_mode="messages"):
        if isinstance(chunk, AIMessageChunk):
            print(chunk.content, end="", flush=True)
    print("\n")

    print("--- stream_mode='updates' (what each node returned) ---")
    for update in bot.stream(question, {"configurable": {"thread_id": "s2"}}, stream_mode="updates"):
        for node_name, payload in update.items():
            print(f"  node '{node_name}' returned {len(payload['messages'])} message(s)")

    print("\n--- stream_mode='values' (full state after each step) ---")
    for state in bot.stream(question, {"configurable": {"thread_id": "s3"}}, stream_mode="values"):
        print("  messages in state so far:", len(state["messages"]))
