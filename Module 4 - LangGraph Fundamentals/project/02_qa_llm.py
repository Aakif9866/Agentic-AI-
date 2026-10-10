from typing import TypedDict
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)

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