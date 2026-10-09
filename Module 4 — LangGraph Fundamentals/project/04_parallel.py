import operator
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)


class Score(BaseModel):
    feedback: str
    score: int = Field(ge=0, le=10)


judge = llm.with_structured_output(Score)


class EssayState(TypedDict):
    essay: str
    scores: Annotated[list[int], operator.add]
    feedback: Annotated[list[str], operator.add]
    final: str


def make_judge(aspect: str):
    def node(s: EssayState) -> dict:
        r = judge.invoke(
            f"Rate the {aspect} of this essay 0-10 with brief feedback:\n{s['essay']}"
        )
        return {"scores": [r.score], "feedback": [f"{aspect}: {r.feedback}"]}

    return node


def summarize(s: EssayState) -> dict:
    avg = sum(s["scores"]) / len(s["scores"]) if s["scores"] else 0
    feedback_text = "\n".join(s["feedback"])
    return {"final": f"Average: {avg:.1f}/10\n{feedback_text}"}


g = StateGraph(EssayState)
for aspect in ["language", "analysis", "clarity"]:
    g.add_node(aspect, make_judge(aspect))
    g.add_edge(START, aspect)
    g.add_edge(aspect, "summarize")

g.add_node("summarize", summarize)
g.add_edge("summarize", END)
app = g.compile()

if __name__ == "__main__":
    essay = "AI agents are changing how we work by automating decisions, not just answering questions."
    result = app.invoke({"essay": essay})
    print(result["final"])
