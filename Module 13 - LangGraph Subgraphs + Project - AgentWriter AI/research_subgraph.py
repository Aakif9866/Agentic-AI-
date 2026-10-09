"""A self-contained research pipeline, compiled on its own.

Its schema is deliberately narrow — `topic` in, `notes` out — so it knows
nothing about articles, drafts or whoever is calling it. That's what makes
it reusable.

Run it standalone to prove it isn't hardcoded to the parent:

    uv run python research_subgraph.py
"""
from typing import TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)
web_search = TavilySearch(max_results=3)


class Queries(BaseModel):
    queries: list[str]


class ResearchState(TypedDict):
    topic: str          # input
    queries: list[str]  # internal
    raw: str            # internal
    notes: str          # output


def plan_queries(state: ResearchState) -> dict:
    q = llm.with_structured_output(Queries, method="json_mode").invoke(
        f'Write 3 web search queries that would research "{state["topic"]}". '
        'Respond with JSON of the exact form {"queries": [str, str, str]}.'
    )
    return {"queries": q.queries[:3]}


def gather(state: ResearchState) -> dict:
    chunks = []
    for q in state["queries"]:
        try:
            raw = web_search.invoke({"query": q})
        except Exception as e:
            chunks.append(f"({q}: search failed: {e})")
            continue
        hits = raw.get("results", []) if isinstance(raw, dict) else []
        chunks.append(
            f"## {q}\n"
            + "\n".join(f"- {h.get('title','')}: {h.get('content','')}" for h in hits)
        )
    return {"raw": "\n\n".join(chunks)[:6000]}


def synthesize(state: ResearchState) -> dict:
    notes = llm.invoke(
        f'Turn these search results into 6-8 factual bullet-point notes on '
        f'"{state["topic"]}". Notes only, no intro, no conclusion.\n\n{state["raw"]}'
    ).content
    return {"notes": notes}


_g = StateGraph(ResearchState)
_g.add_node("plan_queries", plan_queries)
_g.add_node("gather", gather)
_g.add_node("synthesize", synthesize)
_g.add_edge(START, "plan_queries")
_g.add_edge("plan_queries", "gather")
_g.add_edge("gather", "synthesize")
_g.add_edge("synthesize", END)

research_subgraph = _g.compile()


if __name__ == "__main__":
    out = research_subgraph.invoke({"topic": "why LangGraph uses reducers"})
    print("Queries it chose:")
    for q in out["queries"]:
        print("  -", q)
    print("\nNotes:\n")
    print(out["notes"])
