from typing import TypedDict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)


class Sentiment(BaseModel):
    sentiment: Literal["positive", "negative"]


class ReviewState(TypedDict):
    review: str
    sentiment: str
    reply: str


def find_sentiment(s: ReviewState) -> dict:
    result = llm.with_structured_output(Sentiment).invoke(
        f"Determine if this review is positive or negative:\n{s['review']}"
    )
    return {"sentiment": result.sentiment}


def thank(s: ReviewState) -> dict:
    reply = llm.invoke(f"Write a 2-line thank you response for this positive review:\n{s['review']}").content
    return {"reply": reply}


def apologize(s: ReviewState) -> dict:
    reply = llm.invoke(
        f"Write a 2-line sincere apology and solution offer for this negative review:\n{s['review']}"
    ).content
    return {"reply": reply}


def route(s: ReviewState) -> Literal["thank", "apologize"]:
    return "thank" if s["sentiment"] == "positive" else "apologize"


g = StateGraph(ReviewState)
g.add_node("find_sentiment", find_sentiment)
g.add_node("thank", thank)
g.add_node("apologize", apologize)
g.add_edge(START, "find_sentiment")
g.add_conditional_edges("find_sentiment", route)
g.add_edge("thank", END)
g.add_edge("apologize", END)
app = g.compile()

if __name__ == "__main__":
    print("=== Negative Review ===")
    result1 = app.invoke({"review": "App crashes every time I upload a file. Fix it!"})
    print(result1["reply"])
    print("\n=== Positive Review ===")
    result2 = app.invoke({"review": "Love this app, works great!"})
    print(result2["reply"])
