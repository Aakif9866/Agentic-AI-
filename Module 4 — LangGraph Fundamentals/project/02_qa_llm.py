from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

class State(TypedDict):
    question: str
    answer: str

def llm_qa(s: State) -> dict:
    return {"answer": llm.invoke(f"Answer briefly: {s['question']}").content}

g = StateGraph(State)
g.add_node("llm_qa", llm_qa)
g.add_edge(START, "llm_qa")
g.add_edge("llm_qa", END)
app = g.compile()

if __name__ == "__main__":
    print(app.invoke({"question": "Who created Python?"})["answer"])