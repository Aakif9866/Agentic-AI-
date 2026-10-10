"""Corrective RAG (CRAG) — grade the DOCUMENTS, then correct course.

    retrieve -> grade_docs -> CORRECT   : refine -> generate          (kb)
                           -> AMBIGUOUS : refine + web -> generate    (kb+web)
                           -> INCORRECT : rewrite -> web -> generate  (web)

The decision comes from a float score per document against two thresholds.
"""
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from kb import retrieve

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)
web = TavilySearch(max_results=3)

UPPER, LOWER = 0.7, 0.3  # tuned against real output; tighter and everything is AMBIGUOUS


# ------------------------------------------------------------------ schemas
class DocScores(BaseModel):
    scores: list[float] = Field(description="one relevance score 0-1 per document, in order")


class Sentences(BaseModel):
    kept: list[str]


class Rewritten(BaseModel):
    query: str


class CragState(TypedDict):
    question: str
    docs: list[str]
    scores: list[float]
    decision: str
    rewritten: str
    web: str
    context: str
    answer: str
    source: str


def structured(schema, prompt: str):
    """json_mode + explicit field names — see ../AGENT_RULES.md #2."""
    return llm.with_structured_output(schema, method="json_mode").invoke(prompt)


def _search(query: str) -> str:
    try:
        raw = web.invoke({"query": query})
    except Exception as e:
        return f"(web search unavailable: {e})"
    hits = raw.get("results", []) if isinstance(raw, dict) else []
    return "\n".join(f"- {h.get('title','')}: {h.get('content','')}" for h in hits)[:3000]


# -------------------------------------------------------------------- nodes
def retrieve_node(state: CragState) -> dict:
    return {"docs": retrieve(state["question"], k=4)}


def grade_docs(state: CragState) -> dict:
    """One call scores every document, so cost doesn't grow with k."""
    if not state["docs"]:
        return {"scores": [], "decision": "INCORRECT"}

    numbered = "\n\n".join(f"[{i}] {d}" for i, d in enumerate(state["docs"]))
    out = structured(
        DocScores,
        f'Score how well each document answers the question, 0.0 (irrelevant) to '
        f'1.0 (fully answers it). Respond with JSON of the exact form '
        f'{{"scores": [float, ...]}} with exactly {len(state["docs"])} scores, in order.\n\n'
        f'QUESTION: {state["question"]}\n\nDOCUMENTS:\n{numbered}',
    )
    scores = (out.scores + [0.0] * len(state["docs"]))[: len(state["docs"])]
    best = max(scores)
    decision = "CORRECT" if best >= UPPER else "INCORRECT" if best < LOWER else "AMBIGUOUS"
    return {"scores": scores, "decision": decision}


def route(state: CragState) -> Literal["refine", "refine_and_web", "rewrite"]:
    return {
        "CORRECT": "refine",
        "AMBIGUOUS": "refine_and_web",
        "INCORRECT": "rewrite",
    }[state["decision"]]


def _refine(question: str, text: str) -> str:
    """Sentence-level refine: keep only the sentences that bear on the question."""
    out = structured(
        Sentences,
        'Keep only the sentences that help answer the question. Drop everything else. '
        'Respond with JSON of the exact form {"kept": [str, ...]}. '
        'If nothing is relevant, return an empty list.\n\n'
        f"QUESTION: {question}\n\nTEXT:\n{text[:4000]}",
    )
    return "\n".join(out.kept)


def refine(state: CragState) -> dict:
    return {"context": _refine(state["question"], "\n\n".join(state["docs"])), "source": "kb"}


def refine_and_web(state: CragState) -> dict:
    kb = _refine(state["question"], "\n\n".join(state["docs"]))
    w = _search(state["question"])
    return {"web": w, "context": f"FROM DOCUMENTS:\n{kb}\n\nFROM WEB:\n{w}", "source": "kb+web"}


def rewrite(state: CragState) -> dict:
    out = structured(
        Rewritten,
        'The document store had nothing useful, so rewrite this into a better standalone '
        'web search query. Respond with JSON of the exact form {"query": str}.\n\n'
        f'QUESTION: {state["question"]}',
    )
    return {"rewritten": out.query}


def web_node(state: CragState) -> dict:
    w = _search(state["rewritten"])
    return {"web": w, "context": f"FROM WEB:\n{w}", "source": "web"}


def generate(state: CragState) -> dict:
    ctx = state.get("context", "").strip()
    if not ctx:
        return {"answer": "I don't know — I couldn't find anything relevant."}
    ans = llm.invoke(
        "Answer the question using ONLY the context. If the context does not contain the "
        "answer, say you don't know. Cite page numbers when the context shows them.\n\n"
        f'QUESTION: {state["question"]}\n\nCONTEXT:\n{ctx}'
    ).content
    return {"answer": ans}


g = StateGraph(CragState)
for name, fn in [
    ("retrieve", retrieve_node), ("grade_docs", grade_docs), ("refine", refine),
    ("refine_and_web", refine_and_web), ("rewrite", rewrite), ("web", web_node),
    ("generate", generate),
]:
    g.add_node(name, fn)

g.add_edge(START, "retrieve")
g.add_edge("retrieve", "grade_docs")
g.add_conditional_edges("grade_docs", route, {
    "refine": "refine", "refine_and_web": "refine_and_web", "rewrite": "rewrite",
})
g.add_edge("refine", "generate")
g.add_edge("refine_and_web", "generate")
g.add_edge("rewrite", "web")
g.add_edge("web", "generate")
g.add_edge("generate", END)

app = g.compile()

QUESTIONS = [
    "What does a checkpointer do?",                 # clearly in the document
    "What is a reducer and why is it needed?",      # partially covered -> expect AMBIGUOUS
    "What is the capital of Peru?",                 # not in the document at all
]

if __name__ == "__main__":
    for q in QUESTIONS:
        out = app.invoke({"question": q}, {"recursion_limit": 25})
        print("=" * 76)
        print(f"Q: {q}")
        print(f"   scores   : {[round(s, 2) for s in out.get('scores', [])]}")
        print(f"   decision : {out.get('decision')}  ->  source: {out.get('source', '-')}")
        if out.get("rewritten"):
            print(f"   rewritten: {out['rewritten']}")
        print(f"   A: {out['answer'][:320]}")
