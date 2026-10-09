from dotenv import load_dotenv
from langchain_core.messages import trim_messages, SystemMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b")

# token_counter=len counts MESSAGES, not tokens — no extra dependency needed.
# (token_counter=llm would need `transformers` installed just to tokenize.)
MAX_MESSAGES = 6


def chat_node(state: MessagesState) -> dict:
    trimmed = trim_messages(
        state["messages"],
        max_tokens=MAX_MESSAGES,
        strategy="last",          # keep the most recent, drop the oldest
        token_counter=len,
        start_on="human",         # never start the window mid tool-call
        include_system=True,      # always keep the system message
    )
    print(f"    [model sees {len(trimmed)} of {len(state['messages'])} messages]")
    return {"messages": [llm.invoke(trimmed)]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)
bot = graph.compile(checkpointer=InMemorySaver())

if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "trim-demo"}}
    bot.invoke({"messages": [SystemMessage("You are concise. One sentence per answer.")]}, cfg)

    for i in range(1, 7):
        out = bot.invoke({"messages": [("user", f"Give me fact #{i} about space.")]}, cfg)
        print(f"turn {i}: {out['messages'][-1].content[:100]}")

    full = bot.get_state(cfg).values["messages"]
    print(f"\nFull checkpoint still holds {len(full)} messages — nothing was deleted.")
    print(f"Only the model's per-turn view was capped at {MAX_MESSAGES}.")
