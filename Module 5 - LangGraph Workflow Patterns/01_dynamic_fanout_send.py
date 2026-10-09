import operator
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0.7)


class FanState(TypedDict):
    topics: list[str]
    jokes: Annotated[list[str], operator.add]


class JokePayload(TypedDict):
    topic: str


def dispatch(state: FanState) -> list[Send]:
    return [Send("write_joke", {"topic": t}) for t in state["topics"]]


def write_joke(payload: JokePayload) -> dict:
    joke = llm.invoke(f"One punchy one-liner joke about {payload['topic']}.").content
    return {"jokes": [joke]}


graph = StateGraph(FanState)
graph.add_node("write_joke", write_joke)
graph.add_conditional_edges(START, dispatch, ["write_joke"])
graph.add_edge("write_joke", END)
app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({"topics": ["Python", "Docker", "Kubernetes", "Git"]})
    for topic, joke in zip(result["topics"], result["jokes"]):
        print(f"{topic}: {joke}")
