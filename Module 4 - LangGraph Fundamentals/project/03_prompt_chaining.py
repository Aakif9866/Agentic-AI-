from typing import TypedDict
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)


class BlogState(TypedDict):
    title: str
    outline: str
    content: str


def make_outline(s: BlogState) -> dict:
    outline = llm.invoke(f"Write a 5-point outline for a blog titled: {s['title']}").content
    return {"outline": outline}


def write_blog(s: BlogState) -> dict:
    content = llm.invoke(
        f"Write a short blog '{s['title']}' following this outline:\n{s['outline']}"
    ).content
    return {"content": content}


g = StateGraph(BlogState)
g.add_node("outline", make_outline)
g.add_node("write", write_blog)
g.add_edge(START, "outline")
g.add_edge("outline", "write")
g.add_edge("write", END)
app = g.compile()

if __name__ == "__main__":
    out = app.invoke({"title": "Why every developer should learn LangGraph"})
    print("=== Outline ===")
    print(out["outline"])
    print("\n=== Blog ===")
    print(out["content"])
