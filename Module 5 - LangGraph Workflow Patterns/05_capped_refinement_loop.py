from typing import TypedDict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0.3)


class CodeReview(BaseModel):
    has_docstring: bool
    has_type_hints: bool
    handles_errors: bool
    feedback: str = Field(description="One sentence on what to fix, empty if nothing")


class CodeState(TypedDict):
    task: str
    code: str
    review: dict
    iteration: int
    max_iteration: int


def write_code(state: CodeState) -> dict:
    prior_feedback = state.get("review", {}).get("feedback")
    hint = f"\nAddress this feedback: {prior_feedback}" if prior_feedback else ""
    raw = llm.invoke(
        f"Write a Python function for: {state['task']}. "
        f"Include a docstring, type hints, and basic error handling.{hint}\n"
        f"Return ONLY the code, no markdown fences."
    ).content
    code = raw.strip().strip("`").removeprefix("python\n")
    return {"code": code, "iteration": state.get("iteration", 0) + 1}


def review_code(state: CodeState) -> dict:
    review = llm.with_structured_output(CodeReview, method="json_mode").invoke(
        "Review this code strictly. Respond with JSON of the exact form "
        '{"has_docstring": bool, "has_type_hints": bool, "handles_errors": bool, "feedback": str}.\n'
        f"Code:\n{state['code']}"
    )
    return {"review": review.model_dump()}


def all_criteria_met(review: dict) -> bool:
    return review["has_docstring"] and review["has_type_hints"] and review["handles_errors"]


def route_after_review(state: CodeState) -> Literal["done", "retry"]:
    if all_criteria_met(state["review"]) or state["iteration"] >= state["max_iteration"]:
        return "done"
    return "retry"


graph = StateGraph(CodeState)
graph.add_node("write_code", write_code)
graph.add_node("review_code", review_code)
graph.add_edge(START, "write_code")
graph.add_edge("write_code", "review_code")
graph.add_conditional_edges("review_code", route_after_review, {"done": END, "retry": "write_code"})
app = graph.compile()

if __name__ == "__main__":
    result = app.invoke(
        {"task": "parse an integer from user input safely", "iteration": 0, "max_iteration": 3},
        {"recursion_limit": 25},
    )
    print(f"Took {result['iteration']} iteration(s). All criteria met: {all_criteria_met(result['review'])}")
    print("\n" + result["code"])
