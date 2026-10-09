"""TripMate AI — a supervisor routing a trip request to three specialists.

Flow:
    START -> parse_request -> supervisor -> weather -> supervisor
                                         -> places  -> supervisor
                                         -> budget  -> supervisor
                                         -> assemble -> END

The supervisor uses Command(goto=...) (Module 5's pattern) and reads a
`visited` list so each specialist runs exactly once.
"""
import json
import operator
import os
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

load_dotenv()
llm = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)
web_search = TavilySearch(max_results=3)

SPECIALISTS = ["weather", "places", "budget"]


# ---------------------------------------------------------------- schemas
class TripParams(BaseModel):
    destination: str
    days: int = Field(ge=1, le=14)
    budget: int
    currency: str


class Places(BaseModel):
    names: list[str]
    why: list[str]


class CostItem(BaseModel):
    item: str
    amount: int


class BudgetPlan(BaseModel):
    items: list[CostItem]


class DayPlan(BaseModel):
    day: int
    morning: str
    afternoon: str
    evening: str


class Itinerary(BaseModel):
    summary: str
    days: list[DayPlan]


class TripState(MessagesState):
    request: str
    destination: str
    days: int
    budget: int
    currency: str
    weather: str
    places: list[str]
    places_why: list[str]
    cost_items: list[dict]
    cost_total: int
    itinerary: dict
    visited: Annotated[list[str], operator.add]
    route_log: Annotated[list[str], operator.add]


# ---------------------------------------------------------------- helpers
def structured(schema, prompt: str):
    """json_mode + explicit field names — gpt-oss fails on default tool-calling mode."""
    return llm.with_structured_output(schema, method="json_mode").invoke(prompt)


def search(query: str) -> str:
    """Tavily, flattened to text. Returns an error string, never raises."""
    try:
        raw = web_search.invoke({"query": query})
    except Exception as e:
        return f"(search unavailable: {e})"
    if isinstance(raw, dict):
        hits = raw.get("results", [])
        return "\n".join(f"- {h.get('title','')}: {h.get('content','')}" for h in hits)[:2500]
    return str(raw)[:2500]


# ---------------------------------------------------------------- nodes
def parse_request(state: TripState) -> dict:
    p = structured(
        TripParams,
        'Extract the trip details. Respond with JSON of the exact form '
        '{"destination": str, "days": int, "budget": int, "currency": str}. '
        'Use the currency symbol or code the user wrote.\n'
        f"Request: {state['request']}",
    )
    return {
        "destination": p.destination,
        "days": p.days,
        "budget": p.budget,
        "currency": p.currency,
    }


def supervisor(state: TripState) -> Command[Literal["weather", "places", "budget", "assemble"]]:
    """Deterministic routing: send work to whichever specialist hasn't reported yet."""
    done = state.get("visited", [])
    nxt = next((s for s in SPECIALISTS if s not in done), "assemble")
    return Command(update={"route_log": [nxt]}, goto=nxt)


def weather(state: TripState) -> dict:
    dest = state["destination"]
    key = os.getenv("OPENWEATHER_API_KEY")
    if key:
        import urllib.request

        try:
            url = (
                "https://api.openweathermap.org/data/2.5/weather"
                f"?q={urllib.parse.quote(dest)}&appid={key}&units=metric"
            )
            with urllib.request.urlopen(url, timeout=10) as r:
                d = json.load(r)
            note = f"{d['weather'][0]['description']}, {d['main']['temp']}°C (OpenWeatherMap)"
            return {"weather": note, "visited": ["weather"]}
        except Exception as e:
            # Fall through to search rather than crashing the graph.
            print(f"    [weather] OpenWeatherMap failed ({e}) — falling back to search")

    raw = search(f"typical weather and best time to visit {dest}")
    note = llm.invoke(
        f"In two sentences, summarise the weather a traveller should expect in {dest}, "
        f"and what to pack. Source notes:\n{raw}"
    ).content
    return {"weather": f"{note} (via web search — no weather API key set)", "visited": ["weather"]}


def places(state: TripState) -> dict:
    dest, days = state["destination"], state["days"]
    raw = search(f"top attractions and things to do in {dest}")
    p = structured(
        Places,
        f'Pick the {max(3, days)} best attractions in {dest} for a {days}-day trip. '
        'Respond with JSON of the exact form {"names": [str], "why": [str]} where the two '
        'lists are the same length and aligned. Use real place names only.\n'
        f"Source notes:\n{raw}",
    )
    return {"places": p.names, "places_why": p.why, "visited": ["places"]}


def budget(state: TripState) -> dict:
    """LLM proposes line items; Python does the arithmetic (never trust the model to sum)."""
    cur, total_budget, days = state["currency"], state["budget"], state["days"]
    names = ", ".join(state.get("places", []))
    feedback = ""

    for _ in range(2):  # capped: one retry if the model overshoots
        plan = structured(
            BudgetPlan,
            f'Build a {days}-day budget for {state["destination"]} totalling AT MOST '
            f'{total_budget} {cur}. Cover stay, food, local transport and entry fees for: {names}. '
            'Respond with JSON of the exact form {"items": [{"item": str, "amount": int}]}. '
            f'Amounts are whole numbers in {cur}.{feedback}',
        )
        items = [i.model_dump() for i in plan.items]
        total = sum(i["amount"] for i in items)  # deterministic, not LLM arithmetic
        if total <= total_budget:
            break
        feedback = f" Your previous attempt totalled {total}, which is over by {total - total_budget}. Cut it down."

    return {"cost_items": items, "cost_total": total, "visited": ["budget"]}


def assemble(state: TripState) -> dict:
    lines = "\n".join(f"- {i['item']}: {i['amount']}" for i in state["cost_items"])
    it = structured(
        Itinerary,
        f'Write a {state["days"]}-day itinerary for {state["destination"]}. '
        'Respond with JSON of the exact form {"summary": str, "days": '
        '[{"day": int, "morning": str, "afternoon": str, "evening": str}]}. '
        f'Include exactly {state["days"]} day objects.\n'
        f"Weather: {state['weather']}\n"
        f"Places to use: {', '.join(state['places'])}\n"
        f"Budget ({state['currency']}):\n{lines}",
    )
    return {"itinerary": it.model_dump()}


# ---------------------------------------------------------------- graph
g = StateGraph(TripState)
g.add_node("parse_request", parse_request)
g.add_node("supervisor", supervisor)
g.add_node("weather", weather)
g.add_node("places", places)
g.add_node("budget", budget)
g.add_node("assemble", assemble)

g.add_edge(START, "parse_request")
g.add_edge("parse_request", "supervisor")
for s in SPECIALISTS:
    g.add_edge(s, "supervisor")  # every specialist reports back
g.add_edge("assemble", END)

app = g.compile(checkpointer=InMemorySaver())


def plan_trip(request: str, thread: str = "trip-1") -> dict:
    return app.invoke(
        {"request": request, "messages": [("user", request)]},
        {"configurable": {"thread_id": thread}, "recursion_limit": 25},
    )


if __name__ == "__main__":
    out = plan_trip("Plan a 3-day trip to Goa, budget ₹15000")

    print(f"\nDestination : {out['destination']}  ({out['days']} days)")
    print(f"Budget      : {out['budget']} {out['currency']}")
    print(f"Route taken : {' -> '.join(out['route_log'])}")
    print(f"\nWeather: {out['weather']}")

    print(f"\nPlaces ({len(out['places'])}):")
    for n, w in zip(out["places"], out["places_why"]):
        print(f"  - {n}: {w}")

    print(f"\nBudget breakdown ({out['currency']}):")
    for i in out["cost_items"]:
        print(f"  {i['item']:<28} {i['amount']:>7}")
    ok = "OK" if out["cost_total"] <= out["budget"] else "OVER BUDGET"
    print(f"  {'TOTAL':<28} {out['cost_total']:>7}   [{ok}, limit {out['budget']}]")

    print(f"\nItinerary: {out['itinerary']['summary']}")
    for d in out["itinerary"]["days"]:
        print(f"\n  Day {d['day']}")
        print(f"    morning   : {d['morning']}")
        print(f"    afternoon : {d['afternoon']}")
        print(f"    evening   : {d['evening']}")
