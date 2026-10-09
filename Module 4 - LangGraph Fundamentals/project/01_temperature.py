from typing import TypedDict 
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    celsius: float
    fahrenheit: float
    label: str
    
def convert(s: State) -> dict:
    return {"fahrenheit": s["celsius"] * 9 / 5 + 32}

def label(s: State) -> dict:
    f = s["fahrenheit"]
    return {"label": "Cold" if f < 50 else "Mild" if f < 77 else "Hot"}


g = StateGraph(State)
g.add_node("convert", convert)
g.add_node("label", label)
g.add_edge(START, "convert")
g.add_edge("convert", "label")
g.add_edge("label", END)

app = g.compile()

if __name__ == "__main__":
    print(app.invoke({"celsius": 28.5}))
    # print(app.get_graph().draw_mermaid())   # paste into mermaid.live to see the diagram