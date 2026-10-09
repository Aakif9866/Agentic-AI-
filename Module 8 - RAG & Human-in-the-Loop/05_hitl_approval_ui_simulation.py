from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command

load_dotenv()

# Without this, the model helpfully writes the email as chat text and never calls the
# tool — so the approval step never triggers. Tell it plainly to use the tool.
SYSTEM = SystemMessage(content=(
    "You send email using the `send_email` tool. When the user asks you to email "
    "someone, call `send_email` with a body you write yourself. Never reply with a "
    "plain-text draft and never ask the user to confirm — an approval step already exists."
))


@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email. Requires human approval; the human may edit the body before it sends."""
    decision = interrupt({"action": "send_email", "to": to, "subject": subject, "body": body})
    if decision.get("approved"):
        final_body = decision.get("edited_body", body)  # pattern 2: human EDITED the args
        return {"status": "sent", "to": to, "subject": subject, "body": final_body}
    return {"status": "cancelled"}


tools = [send_email]
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


def pending_approval(cfg: dict) -> dict | None:
    """What a web UI would poll to find out if this thread is waiting on a human."""
    snapshot = agent.get_state(cfg)
    found = [i for task in snapshot.tasks for i in task.interrupts]
    return found[0].value if found else None


if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "hitl-3"}}
    agent.invoke(
        {"messages": [("user", "Email team@company.com about the Q4 results, subject 'Q4 Results'.")]},
        cfg,
    )

    payload = pending_approval(cfg)
    print(f"[UI] Pending approval -> to: {payload['to']} | subject: {payload['subject']}")
    print(f"[UI] Draft body: {payload['body'][:200]}")

    # Simulate the human editing the draft, then approving.
    edited = payload["body"] + "\n\n-- reviewed and approved by a human"
    agent.invoke(Command(resume={"approved": True, "edited_body": edited}), cfg)

    print(f"\n[UI] Still pending? {pending_approval(cfg)}")
    for m in agent.get_state(cfg).values["messages"]:
        if m.type == "tool":
            print("\nWhat the tool actually returned (note the edit took effect):")
            print(m.content[:350])
