"""AgentWriter AI — plan -> research (subgraph) -> write -> edit, with a capped revision loop.

    uv run python main.py
"""
import operator
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from research_subgraph import research_subgraph

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0.4)


class Critique(BaseModel):
    verdict: Literal["approved", "needs_revision"]
    feedback: str


class ArticleState(TypedDict):
    topic: str
    word_count: int
    tone: str
    outline: str
    research_notes: str
    draft: str
    feedback: str
    verdict: str
    iteration: int
    max_iteration: int
    drafts: Annotated[list[str], operator.add]


def plan(state: ArticleState) -> dict:
    outline = llm.invoke(
        f'Write a 4-point outline for a {state["word_count"]}-word article on '
        f'"{state["topic"]}" in a {state["tone"]} tone. Outline only.'
    ).content
    return {"outline": outline}


def research(state: ArticleState) -> dict:
    """Call the subgraph. Note the EXPLICIT mapping in both directions."""
    sub_in = {"topic": state["topic"]}                 # parent state -> subgraph input
    sub_out = research_subgraph.invoke(sub_in)         # separate schema, separate graph
    return {"research_notes": sub_out["notes"]}        # subgraph output -> parent state


def write(state: ArticleState) -> dict:
    fix = f"\n\nAddress this editor feedback:\n{state['feedback']}" if state.get("feedback") else ""
    draft = llm.invoke(
        f'Write a ~{state["word_count"]}-word article on "{state["topic"]}" in a '
        f'{state["tone"]} tone.\n\nOutline:\n{state["outline"]}\n\n'
        f'Use these research notes:\n{state["research_notes"]}{fix}'
    ).content
    return {
        "draft": draft,
        "iteration": state.get("iteration", 0) + 1,
        "drafts": [draft],
    }


def edit(state: ArticleState) -> dict:
    c = llm.with_structured_output(Critique, method="json_mode").invoke(
        f'You are a strict editor. Judge this draft against the brief. '
        'Respond with JSON of the exact form '
        '{"verdict": "approved"|"needs_revision", "feedback": str}. '
        'Approve only if it matches the tone, follows the outline and uses the research.\n\n'
        f'Brief: ~{state["word_count"]} words, {state["tone"]} tone, topic "{state["topic"]}"\n'
        f'Outline:\n{state["outline"]}\n\nDraft:\n{state["draft"][:4000]}'
    )
    return {"verdict": c.verdict, "feedback": c.feedback}


def route(state: ArticleState) -> Literal["done", "revise"]:
    if state["verdict"] == "approved" or state["iteration"] >= state["max_iteration"]:
        return "done"
    return "revise"


g = StateGraph(ArticleState)
g.add_node("plan", plan)
g.add_node("research", research)
g.add_node("write", write)
g.add_node("edit", edit)
g.add_edge(START, "plan")
g.add_edge("plan", "research")
g.add_edge("research", "write")
g.add_edge("write", "edit")
g.add_conditional_edges("edit", route, {"done": END, "revise": "write"})

app = g.compile()


if __name__ == "__main__":
    brief = {
        "topic": "why LangGraph uses reducers",
        "word_count": 300,
        "tone": "plain and practical",
        "iteration": 0,
        "max_iteration": 3,
    }

    print("--- stages as they finish (stream_mode='updates') ---")
    final = None
    for update in app.stream(brief, {"recursion_limit": 25}):
        for node, payload in update.items():
            extra = ""
            if node == "edit":
                extra = f" -> {payload['verdict']}"
            if node == "research":
                extra = f" -> {len(payload['research_notes'])} chars of notes"
            print(f"  [{node}]{extra}")
            final = {**(final or {}), **payload}

    out = final or {}   # accumulated from the stream — never invoke twice, it doubles the cost

    print(f"\nRevisions: {out['iteration']} (cap {brief['max_iteration']}) | verdict: {out['verdict']}")
    print(f"\n=== RESEARCH NOTES (from the subgraph, inspectable separately) ===")
    print(out["research_notes"][:700])
    print(f"\n=== FINAL ARTICLE ({len(out['draft'].split())} words) ===")
    print(out["draft"])
