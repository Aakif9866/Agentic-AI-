"""A customer-support supervisor with four guardrail layers.

    uv run python main.py          # one request end to end
    uv run python test_guards.py   # the 5-case adversarial eval
"""
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, PIIMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from guardrails import InputGuard, OutputSafety

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)


def _specialist(role: str):
    sub = create_agent(llm, [], system_prompt=f"You are a {role}. Reply in 2-3 sentences.")

    def run(question: str) -> str:
        try:
            r = sub.invoke({"messages": [("user", question)]})
            return r["messages"][-1].content
        except Exception as e:
            return f"error: {e}"  # tools return errors, never raise

    return run


_billing = _specialist("billing support specialist handling invoices, charges and refunds")
_technical = _specialist("technical support engineer handling bugs, crashes and setup")
_escalation = _specialist("senior escalation manager who acknowledges and takes ownership")


@tool
def billing_agent(question: str) -> str:
    """Handle billing: invoices, charges, refunds, subscriptions, payment failures."""
    return _billing(question)


@tool
def technical_agent(question: str) -> str:
    """Handle technical problems: crashes, bugs, errors, login issues, setup, performance."""
    return _technical(question)


@tool
def escalation_agent(question: str) -> str:
    """Escalate to a human manager. Use when the customer demands a human or is seriously upset."""
    return _escalation(question)


# Order matters: free/deterministic first, paid/fuzzy last.
MIDDLEWARE = [
    InputGuard(),                                                   # 1. regex, no LLM cost
    PIIMiddleware("email", strategy="redact", apply_to_input=True),  # 2. redact before the model
    PIIMiddleware("credit_card", strategy="redact", apply_to_input=True),
    HumanInTheLoopMiddleware(interrupt_on={"escalation_agent": True}),  # 3. always pause
    OutputSafety(),                                                 # 4. LLM judge, last
]

supervisor = create_agent(
    llm,
    [billing_agent, technical_agent, escalation_agent],
    system_prompt=(
        "You are a support supervisor. Route the customer to exactly one specialist tool, "
        "then relay its answer. Never answer billing or technical questions yourself."
    ),
    middleware=MIDDLEWARE,
    checkpointer=InMemorySaver(),  # required: HumanInTheLoopMiddleware needs to save the pause
)


def ask(text: str, thread: str) -> dict:
    return supervisor.invoke(
        {"messages": [("user", text)]},
        {"configurable": {"thread_id": thread}, "recursion_limit": 25},
    )


if __name__ == "__main__":
    out = ask("The app crashes every time I upload a file.", "demo-1")
    used = [c["name"] for m in out["messages"] for c in getattr(m, "tool_calls", []) or []]
    print(f"tools used : {used}")
    print(f"reply      : {out['messages'][-1].content[:400]}")
