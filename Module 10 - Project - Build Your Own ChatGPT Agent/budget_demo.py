"""Before/after demo for Module 15's budget fix.

The cap is read from the env, so the pre-fix behaviour is reproducible:

    MAX_LLM_CALLS_PER_THREAD=999 uv run python budget_demo.py   # before (unbounded)
    MAX_LLM_CALLS_PER_THREAD=3   uv run python budget_demo.py   # after  (capped)
"""
import uuid

from backend import MAX_LLM_CALLS_PER_THREAD, agent

TURNS = ["Say hi.", "Say hi.", "Say hi.", "Say hi.", "Say hi.", "Say hi."]

if __name__ == "__main__":
    thread = f"budget-{uuid.uuid4().hex[:6]}"
    cfg = {"configurable": {"thread_id": thread}, "recursion_limit": 25}
    print(f"cap = {MAX_LLM_CALLS_PER_THREAD} | thread = {thread}\n")

    for i, t in enumerate(TURNS, 1):
        out = agent.invoke({"messages": [("user", t)]}, cfg)
        reply = str(out["messages"][-1].content)
        refused = "reached its budget" in reply
        print(
            f"turn {i}: llm_calls={out.get('llm_calls', 0):<3} "
            f"{'REFUSED (no model call spent)' if refused else 'answered'}"
        )

    spent = agent.get_state(cfg).values.get("llm_calls", 0)
    print(f"\ntotal model calls charged to this thread: {spent}")
