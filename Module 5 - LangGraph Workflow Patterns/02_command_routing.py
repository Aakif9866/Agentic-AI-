from typing import Literal
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.types import Command

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)


class Triage(BaseModel):
    category: Literal["billing", "technical", "general"]


def triage_node(state: MessagesState) -> Command[Literal["billing", "technical", "general"]]:
    last_user_msg = state["messages"][-1].content
    result = llm.with_structured_output(Triage, method="json_mode").invoke(
        f"Classify this support ticket. "
        f'Respond with JSON of the exact form {{"category": "billing"|"technical"|"general"}}.\n'
        f"Ticket: {last_user_msg}"
    )
    return Command(
        update={"messages": [("system", f"[routed as: {result.category}]")]},
        goto=result.category,
    )


def billing_node(state: MessagesState) -> dict:
    reply = llm.invoke([*state["messages"], ("user", "Write a short billing support reply.")]).content
    return {"messages": [("assistant", reply)]}


def technical_node(state: MessagesState) -> dict:
    reply = llm.invoke([*state["messages"], ("user", "Write a short technical support reply.")]).content
    return {"messages": [("assistant", reply)]}


def general_node(state: MessagesState) -> dict:
    reply = llm.invoke([*state["messages"], ("user", "Write a short general support reply.")]).content
    return {"messages": [("assistant", reply)]}


graph = StateGraph(MessagesState)
graph.add_node("triage", triage_node)
graph.add_node("billing", billing_node)
graph.add_node("technical", technical_node)
graph.add_node("general", general_node)
graph.add_edge(START, "triage")
app = graph.compile()

if __name__ == "__main__":
    out = app.invoke({"messages": [("user", "I was charged twice for my subscription this month.")]})
    for m in out["messages"]:
        print(getattr(m, "type", "unknown"), ":", getattr(m, "content", m))
