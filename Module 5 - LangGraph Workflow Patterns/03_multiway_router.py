from typing import TypedDict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)


class Priority(BaseModel):
    level: Literal["critical", "high", "medium", "low"]


class TicketState(TypedDict):
    description: str
    level: str
    action: str


def classify(state: TicketState) -> dict:
    p = llm.with_structured_output(Priority, method="json_mode").invoke(
        f"Classify incident severity. "
        f'Respond with JSON of the exact form {{"level": "critical"|"high"|"medium"|"low"}}.\n'
        f"Incident: {state['description']}"
    )
    return {"level": p.level}


def page_oncall(state: TicketState) -> dict:
    return {"action": "Paged on-call engineer immediately."}


def notify_team(state: TicketState) -> dict:
    return {"action": "Posted to team channel, response within the hour."}


def log_ticket(state: TicketState) -> dict:
    return {"action": "Logged for next business day triage."}


def route_by_level(state: TicketState) -> str:
    return state["level"]


graph = StateGraph(TicketState)
graph.add_node("classify", classify)
graph.add_node("page_oncall", page_oncall)
graph.add_node("notify_team", notify_team)
graph.add_node("log_ticket", log_ticket)
graph.add_edge(START, "classify")
graph.add_conditional_edges(
    "classify",
    route_by_level,
    {
        "critical": "page_oncall",
        "high": "notify_team",
        "medium": "notify_team",
        "low": "log_ticket",
    },
)
graph.add_edge("page_oncall", END)
graph.add_edge("notify_team", END)
graph.add_edge("log_ticket", END)
app = graph.compile()

if __name__ == "__main__":
    print(app.invoke({"description": "Production database is down, all customers affected."})["action"])
    print(app.invoke({"description": "A user can't change their profile picture."})["action"])
