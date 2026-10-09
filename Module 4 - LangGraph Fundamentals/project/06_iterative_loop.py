import operator
from typing import TypedDict, Annotated, Literal
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.7)


class Verdict(BaseModel):
    evaluation: Literal["approved", "needs_improvement"]
    feedback: str


class PostState(TypedDict):
    topic: str
    post: str
    evaluation: str
    feedback: str
    iteration: int
    max_iteration: int
    history: Annotated[list[str], operator.add]


def generate(s: PostState) -> dict:
    post = llm.invoke(
        f"Write a funny tweet (<280 chars, no Q&A format) about {s['topic']}"
    ).content
    return {"post": post, "history": [post]}


def evaluate(s: PostState) -> dict:
    verdict = llm.with_structured_output(Verdict).invoke(
        f"You are a harsh critic. Approve only if genuinely funny and original.\nTweet: {s['post']}"
    )
    return {"evaluation": verdict.evaluation, "feedback": verdict.feedback}


def optimize(s: PostState) -> dict:
    improved = llm.invoke(
        f"Improve this tweet based on feedback.\nFeedback: {s['feedback']}\nOriginal: {s['post']}"
    ).content
    return {"post": improved, "iteration": s["iteration"] + 1, "history": [improved]}


def should_continue(s: PostState) -> Literal["done", "again"]:
    if s["evaluation"] == "approved" or s["iteration"] >= s["max_iteration"]:
        return "done"
    return "again"


g = StateGraph(PostState)
g.add_node("generate", generate)
g.add_node("evaluate", evaluate)
g.add_node("optimize", optimize)
g.add_edge(START, "generate")
g.add_edge("generate", "evaluate")
g.add_conditional_edges("evaluate", should_continue, {"done": END, "again": "optimize"})
g.add_edge("optimize", "evaluate")
app = g.compile()

if __name__ == "__main__":
    out = app.invoke({"topic": "agentic AI", "iteration": 1, "max_iteration": 4})
    for i, p in enumerate(out["history"], 1):
        print(f"--- Attempt {i} ---")
        print(p)
        print()
