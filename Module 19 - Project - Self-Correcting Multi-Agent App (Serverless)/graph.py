"""Writer agent + Reviewer agent in a capped loop.

    writer -> reviewer -> approved?        -> END
                       -> needs_revision   -> writer   (up to max_iteration)

Module 13 had one agent revising itself — a bit like proofreading your own
writing. Here the critic is a SEPARATE agent with separate instructions, which
catches more.

Design note (Module 15's lesson): two of the three review criteria are checked
by PYTHON, not by the model. Word count and banned buzzwords are exactly
measurable, so measuring them is strictly better than asking an LLM's opinion.
Only "is there a concrete example?" genuinely needs judgement.
"""
import operator
import os
import re
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

load_dotenv()
writer_llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0.6)
reviewer_llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)

# 60 is deliberately tight. At 120 the writer passed on the first try every time,
# which makes the loop look like it works while proving nothing (the exact trap this
# module's spec warns about). A limit the writer actually struggles to hit is what
# makes iterations-to-approval a real measurement.
MAX_WORDS = int(os.getenv("MAX_WORDS", "60"))
# A real plain-language rule, and the one the writer actually struggles with.
# Without it the reviewer approved 6/6 on the first pass and the loop never ran.
MAX_SENTENCE_WORDS = int(os.getenv("MAX_SENTENCE_WORDS", "15"))
# LLMs reach for these unprompted. A deterministic ban makes the reviewer's
# verdict reproducible, and makes the loop actually fire.
BANNED = [
    "leverage", "seamless", "seamlessly", "robust", "cutting-edge", "unlock",
    "empower", "game-changer", "revolutionize", "revolutionary", "synergy",
    "harness", "paradigm", "elevate", "supercharge", "best-in-class",
]


class HasExample(BaseModel):
    has_concrete_example: Literal["yes", "no"]
    reason: str


class PostState(TypedDict):
    topic: str
    draft: str
    feedback: str
    verdict: str
    word_count: int
    banned_found: list[str]
    long_sentences: int
    iteration: int
    max_iteration: int
    drafts: Annotated[list[str], operator.add]


def _words(text: str) -> int:
    return len(text.split())


def _banned_in(text: str) -> list[str]:
    low = text.lower()
    return [w for w in BANNED if re.search(rf"\b{re.escape(w)}\b", low)]


def _long_sentences(text: str) -> list[str]:
    """Sentences over the word limit. Deterministic, so the verdict is reproducible."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    return [p for p in parts if len(p.split()) > MAX_SENTENCE_WORDS]


def writer(state: PostState) -> dict:
    fix = f"\n\nThe reviewer rejected your last draft. Fix exactly this:\n{state['feedback']}" \
        if state.get("feedback") else ""
    draft = writer_llm.invoke(
        f"Write a short explainer (STRICTLY under {MAX_WORDS} words) about: {state['topic']}\n"
        f"Rules: include one concrete example; every sentence must be "
        f"{MAX_SENTENCE_WORDS} words or fewer; plain language, no buzzwords. "
        "Return only the explainer text." + fix
    ).content.strip()
    n = state.get("iteration", 0) + 1
    return {"draft": draft, "iteration": n, "drafts": [draft]}


def reviewer(state: PostState) -> dict:
    """Two deterministic checks + one judgement call. All three must pass."""
    draft = state["draft"]
    wc = _words(draft)
    banned = _banned_in(draft)

    verdict_parts: list[str] = []
    if wc > MAX_WORDS:
        verdict_parts.append(f"Too long: {wc} words, limit is {MAX_WORDS}. Cut {wc - MAX_WORDS}+ words.")
    if banned:
        verdict_parts.append(f"Remove these buzzwords and say it plainly: {', '.join(banned)}.")
    long_s = _long_sentences(draft)
    if long_s:
        verdict_parts.append(
            f"Split these sentences; each must be {MAX_SENTENCE_WORDS} words or fewer: "
            + " | ".join(f'"{s_[:70]}" ({len(s_.split())} words)' for s_ in long_s[:2])
        )

    ex = reviewer_llm.with_structured_output(HasExample, method="json_mode").invoke(
        'Does this text contain a CONCRETE example - a specific named case, number, or '
        'scenario, not a generic statement? Respond with JSON of the exact form '
        '{"has_concrete_example": "yes"|"no", "reason": str}.\n\nTEXT:\n' + draft
    )
    if ex.has_concrete_example == "no":
        verdict_parts.append(f"Add one concrete example. {ex.reason}")

    approved = not verdict_parts
    return {
        "verdict": "approved" if approved else "needs_revision",
        "feedback": "" if approved else " ".join(verdict_parts),
        "word_count": wc,
        "banned_found": banned,
        "long_sentences": len(long_s),
    }


def route(state: PostState) -> Literal["done", "revise"]:
    if state["verdict"] == "approved" or state["iteration"] >= state["max_iteration"]:
        return "done"
    return "revise"


g = StateGraph(PostState)
g.add_node("writer", writer)
g.add_node("reviewer", reviewer)
g.add_edge(START, "writer")
g.add_edge("writer", "reviewer")
g.add_conditional_edges("reviewer", route, {"done": END, "revise": "writer"})

app = g.compile()


def generate(topic: str, max_iteration: int = 3) -> dict:
    """Run the loop. recursion_limit is the backstop behind max_iteration."""
    return app.invoke(
        {"topic": topic, "iteration": 0, "max_iteration": max_iteration},
        {"recursion_limit": 25},
    )


if __name__ == "__main__":
    out = generate("why a reducer is needed when graph nodes run in parallel")
    print(f"verdict    : {out['verdict']} after {out['iteration']} iteration(s)")
    print(f"word count : {out['word_count']} (limit {MAX_WORDS})")
    print(f"buzzwords  : {out['banned_found'] or 'none'}")
    print(f"\n--- final draft ---\n{out['draft']}")
    if len(out["drafts"]) > 1:
        print(f"\n({len(out['drafts'])} drafts produced — the loop fired)")
