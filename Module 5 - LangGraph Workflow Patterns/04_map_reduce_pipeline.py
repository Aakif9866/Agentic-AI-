import operator
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)

DOCUMENTS = {
    "doc1": "LangGraph models agents as graphs: state, nodes, and edges. Nodes are plain functions.",
    "doc2": "Checkpointers persist state after every node, keyed by thread_id, enabling memory and HITL.",
    "doc3": "Send() enables dynamic fan-out: the router decides branch count at runtime, not compile time.",
}


class MapReduceState(TypedDict):
    doc_ids: list[str]
    summaries: Annotated[list[str], operator.add]
    final_summary: str


class SummarizePayload(TypedDict):
    doc_id: str
    text: str


def dispatch_summaries(state: MapReduceState) -> list[Send]:
    return [Send("summarize_one", {"doc_id": d, "text": DOCUMENTS[d]}) for d in state["doc_ids"]]


def summarize_one(payload: SummarizePayload) -> dict:
    summary = llm.invoke(f"Summarize in one sentence:\n{payload['text']}").content
    return {"summaries": [f"[{payload['doc_id']}] {summary}"]}


def reduce_summaries(state: MapReduceState) -> dict:
    joined = "\n".join(state["summaries"])
    final = llm.invoke(f"Combine these per-document summaries into one short overview:\n{joined}").content
    return {"final_summary": final}


graph = StateGraph(MapReduceState)
graph.add_node("summarize_one", summarize_one)
graph.add_node("reduce_summaries", reduce_summaries)
graph.add_conditional_edges(START, dispatch_summaries, ["summarize_one"])
graph.add_edge("summarize_one", "reduce_summaries")
graph.add_edge("reduce_summaries", END)
app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({"doc_ids": ["doc1", "doc2", "doc3"]})
    print("Per-doc summaries:")
    for s in result["summaries"]:
        print(" -", s)
    print("\nFinal overview:\n", result["final_summary"])
