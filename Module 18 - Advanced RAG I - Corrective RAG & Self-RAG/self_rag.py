"""Self-RAG — grade your OWN ANSWER, twice, with two independent caps.

    decide_retrieval -> direct_answer                      (no retrieval needed)
                     -> retrieve -> grade_relevance -> generate | no_answer
    generate -> is_sup  -> supported     -> is_use
                        -> not_supported -> revise   (capped by MAX_RETRIES)
    is_use   -> useful     -> END
             -> not_useful -> rewrite_query (capped by MAX_REWRITE_TRIES) -> retrieve
                           -> exhausted    -> no_answer

Where CRAG asks "are these documents any good?", Self-RAG asks "is my answer
grounded?" and then "is my answer actually useful?" — two different questions,
so two independent counters.
"""
from functools import lru_cache
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

from kb import retrieve

load_dotenv()


# Built on first use, not at import. langchain_groq raises immediately when
# GROQ_API_KEY is missing, and test_caps.py imports this module to check the
# pure routers — which need no key and make no calls.
@lru_cache(maxsize=1)
def llm():
    return init_chat_model("groq:openai/gpt-oss-120b", temperature=0)

MAX_RETRIES = 2        # IsSUP: how many times we'll re-ground an answer
MAX_REWRITE_TRIES = 2  # IsUSE: how many times we'll re-query


class NeedRetrieval(BaseModel):
    retrieve: bool
    reason: str


class Relevance(BaseModel):
    relevant_indexes: list[int]


class IsSup(BaseModel):
    supported: Literal["supported", "not_supported"]
    reason: str


class IsUse(BaseModel):
    useful: Literal["useful", "not_useful"]
    reason: str


class Rewritten(BaseModel):
    query: str


class SelfRagState(TypedDict):
    question: str
    query: str
    docs: list[str]
    relevant: list[str]
    answer: str
    sup: str
    use: str
    retries: int
    rewrite_tries: int
    source: str
    trace: list[str]


def structured(schema, prompt: str):
    return llm().with_structured_output(schema, method="json_mode").invoke(prompt)


def _log(state: SelfRagState, step: str) -> list[str]:
    return state.get("trace", []) + [step]


# -------------------------------------------------------------------- nodes
def decide_retrieval(state: SelfRagState) -> dict:
    # The first version asked "do you need to look this up?" and the model answered
    # "no" to everything — it felt it knew the topics generally, and happily explained
    # a *Redux* reducer instead of LangGraph's. The gate must describe the corpus, and
    # default to retrieving whenever the question could plausibly be in it.
    out = structured(
        NeedRetrieval,
        "We hold ONE private document: course notes on LangGraph (state, nodes, edges, "
        "checkpointers, thread_id, Send, dynamic fan-out, reducers, interrupts). "
        "Should we search it to answer this question?\n"
        "- true if the question could plausibly be answered by that document, even partly.\n"
        "- false ONLY for small talk or topics clearly outside that subject.\n"
        'Respond with JSON of the exact form {"retrieve": bool, "reason": str}.\n\n'
        f'QUESTION: {state["question"]}',
    )
    return {
        "query": state["question"],
        "retries": 0,
        "rewrite_tries": 0,
        "trace": _log(state, f"decide_retrieval={out.retrieve}"),
        "source": "" if out.retrieve else "parametric",
        "sup": "" if out.retrieve else "n/a",
    }


def route_retrieval(state: SelfRagState) -> Literal["retrieve", "direct_answer"]:
    return "direct_answer" if state["source"] == "parametric" else "retrieve"


def direct_answer(state: SelfRagState) -> dict:
    ans = llm().invoke(
        f'Answer concisely. If you are not confident, say you do not know.\n\nQ: {state["question"]}'
    ).content
    return {"answer": ans, "use": "useful", "trace": _log(state, "direct_answer")}


def retrieve_node(state: SelfRagState) -> dict:
    docs = retrieve(state["query"], k=4)
    return {"docs": docs, "trace": _log(state, f"retrieve({len(docs)} docs)")}


def grade_relevance(state: SelfRagState) -> dict:
    if not state["docs"]:
        return {"relevant": [], "trace": _log(state, "grade_relevance=0")}
    numbered = "\n\n".join(f"[{i}] {d}" for i, d in enumerate(state["docs"]))
    out = structured(
        Relevance,
        'List the indexes of documents that genuinely help answer the question. '
        'Respond with JSON of the exact form {"relevant_indexes": [int, ...]}. '
        'Empty list if none are relevant.\n\n'
        f'QUESTION: {state["question"]}\n\nDOCUMENTS:\n{numbered}',
    )
    rel = [state["docs"][i] for i in out.relevant_indexes if 0 <= i < len(state["docs"])]
    return {"relevant": rel, "trace": _log(state, f"grade_relevance={len(rel)}")}


def route_relevance(state: SelfRagState) -> Literal["generate", "no_answer"]:
    return "generate" if state["relevant"] else "no_answer"


def generate(state: SelfRagState) -> dict:
    ans = llm().invoke(
        "Answer using ONLY the context. Cite page numbers shown in the context. "
        "If the context is insufficient, say so plainly.\n\n"
        f'QUESTION: {state["question"]}\n\nCONTEXT:\n' + "\n\n".join(state["relevant"])
    ).content
    return {"answer": ans, "source": "kb", "trace": _log(state, "generate")}


def check_sup(state: SelfRagState) -> dict:
    out = structured(
        IsSup,
        'Is every claim in the answer supported by the context? '
        'Respond with JSON of the exact form '
        '{"supported": "supported"|"not_supported", "reason": str}.\n\n'
        f'CONTEXT:\n' + "\n\n".join(state["relevant"])[:3000] + f'\n\nANSWER:\n{state["answer"]}',
    )
    return {"sup": out.supported, "trace": _log(state, f"is_sup={out.supported}")}


def route_sup(state: SelfRagState) -> Literal["check_use", "revise", "no_answer"]:
    if state["sup"] == "supported":
        return "check_use"
    return "revise" if state["retries"] < MAX_RETRIES else "no_answer"


def revise(state: SelfRagState) -> dict:
    ans = llm().invoke(
        "Your previous answer contained claims the context does not support. Rewrite it so "
        "every claim is traceable to the context. Drop anything unsupported.\n\n"
        f'QUESTION: {state["question"]}\n\nCONTEXT:\n'
        + "\n\n".join(state["relevant"])[:3000]
        + f'\n\nPREVIOUS:\n{state["answer"]}'
    ).content
    n = state["retries"] + 1
    return {"answer": ans, "retries": n, "trace": _log(state, f"revise#{n}")}


def check_use(state: SelfRagState) -> dict:
    out = structured(
        IsUse,
        'Does this answer actually address what was asked? '
        'Respond with JSON of the exact form '
        '{"useful": "useful"|"not_useful", "reason": str}.\n\n'
        f'QUESTION: {state["question"]}\n\nANSWER:\n{state["answer"]}',
    )
    return {"use": out.useful, "trace": _log(state, f"is_use={out.useful}")}


def route_use(state: SelfRagState) -> Literal["__end__", "rewrite_query", "no_answer"]:
    if state["use"] == "useful":
        return "__end__"
    return "rewrite_query" if state["rewrite_tries"] < MAX_REWRITE_TRIES else "no_answer"


def rewrite_query(state: SelfRagState) -> dict:
    out = structured(
        Rewritten,
        'The answer was not useful. Rewrite the search query to find better passages. '
        'Respond with JSON of the exact form {"query": str}.\n\n'
        f'ORIGINAL QUESTION: {state["question"]}\nPREVIOUS QUERY: {state["query"]}',
    )
    n = state["rewrite_tries"] + 1
    return {"query": out.query, "rewrite_tries": n, "trace": _log(state, f"rewrite#{n}")}


def no_answer(state: SelfRagState) -> dict:
    return {
        "answer": "I don't know — the document doesn't cover this and I won't guess.",
        "source": "none",
        "trace": _log(state, "no_answer"),
    }


g = StateGraph(SelfRagState)
for name, fn in [
    ("decide_retrieval", decide_retrieval), ("direct_answer", direct_answer),
    ("retrieve", retrieve_node), ("grade_relevance", grade_relevance),
    ("generate", generate), ("check_sup", check_sup), ("revise", revise),
    ("check_use", check_use), ("rewrite_query", rewrite_query), ("no_answer", no_answer),
]:
    g.add_node(name, fn)

g.add_edge(START, "decide_retrieval")
g.add_conditional_edges("decide_retrieval", route_retrieval,
                        {"retrieve": "retrieve", "direct_answer": "direct_answer"})
g.add_edge("direct_answer", END)
g.add_edge("retrieve", "grade_relevance")
g.add_conditional_edges("grade_relevance", route_relevance,
                        {"generate": "generate", "no_answer": "no_answer"})
g.add_edge("generate", "check_sup")
g.add_conditional_edges("check_sup", route_sup,
                        {"check_use": "check_use", "revise": "revise", "no_answer": "no_answer"})
g.add_edge("revise", "check_sup")            # IsSUP loop
g.add_conditional_edges("check_use", route_use,
                        {"__end__": END, "rewrite_query": "rewrite_query", "no_answer": "no_answer"})
g.add_edge("rewrite_query", "retrieve")      # IsUSE loop
g.add_edge("no_answer", END)

app = g.compile()

QUESTIONS = [
    "What does a checkpointer do?",
    "What is a reducer and why is it needed?",
    "What is the capital of Peru?",
]

if __name__ == "__main__":
    for q in QUESTIONS:
        out = app.invoke({"question": q}, {"recursion_limit": 25})
        print("=" * 76)
        print(f"Q: {q}")
        print(f"   path    : {' -> '.join(out.get('trace', []))}")
        print(f"   caps    : retries={out.get('retries')}/{MAX_RETRIES} "
              f"rewrites={out.get('rewrite_tries')}/{MAX_REWRITE_TRIES}  source={out.get('source')}")
        print(f"   A: {out['answer'][:300]}")
