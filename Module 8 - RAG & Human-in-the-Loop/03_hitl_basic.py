from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b")


def chat_node(state: MessagesState) -> dict:
    question = state["messages"][-1].content
    # Execution stops HERE and a checkpoint is saved. Nothing below runs yet.
    decision = interrupt({"question": question, "ask": "Approve answering this? yes/no"})
    if decision != "yes":
        return {"messages": [AIMessage("Not approved by reviewer.")]}
    return {"messages": [llm.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)
app = graph.compile(checkpointer=InMemorySaver())  # a checkpointer is REQUIRED for interrupt()

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "hitl-1"}}
    result = app.invoke({"messages": [("user", "Explain gradient descent simply.")]}, cfg)

    print("Graph paused. It is asking:", result["__interrupt__"][0].value)
    final = app.invoke(Command(resume="yes"), cfg)
    print("\nAfter approval:", final["messages"][-1].content[:300])

    # Same graph, a 'no' answer this time.
    cfg2 = {"configurable": {"thread_id": "hitl-1-rejected"}}
    app.invoke({"messages": [("user", "Explain gradient descent simply.")]}, cfg2)
    rejected = app.invoke(Command(resume="no"), cfg2)
    print("\nAfter rejection:", rejected["messages"][-1].content)
