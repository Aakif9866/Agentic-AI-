# Module 11 — TripMate AI (Multi-Agent Travel Planner)

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

A **supervisor** agent that routes a trip request to three specialists (weather, places, budget) and then assembles a day-by-day itinerary.

## Why this module exists

Modules 4–10 had one agent with tools. This is your first **multi-agent** system: several agents with different jobs, and a boss deciding who works next. Everything here reuses patterns you already have — `Command(goto=...)` from Module 5, tool loops from Module 7, `with_structured_output` from Module 5.

## Setup

```bash
cd "Module 11 - Project - TripMate AI (Multi-Agent Travel Planner)"
uv init --no-readme --name module11-tripmate --python 3.12
rm main.py
uv add langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv pydantic langchain-tavily
cp "../Module 10 - Project - Build Your Own ChatGPT Agent/.env" .env
```

## Files to create

```
main.py          supervisor graph + all nodes (keep it one file first; split later if it grows)
agents.py        the three specialist nodes (optional split)
NOTES.md         write this yourself afterwards — see ../LEARNPLAN.md
```

## Requirements

- `StateGraph` on `MessagesState`, checkpointed with `InMemorySaver`.
- A **`supervisor` node using `Command(goto=...)`** to pick the next specialist. Not a chain of `add_conditional_edges` — this is the Module 5 file-02 pattern.
- Three specialists:
  - **`weather_agent`** — real weather via OpenWeatherMap, **falling back to Tavily search if no key is set**. Must not crash when the key is missing.
  - **`places_agent`** — Tavily search for attractions in the destination.
  - **`budget_agent`** — a calculator tool that totals estimated costs from the other two agents' output.
- An **`assemble_itinerary`** node the supervisor routes to once all three have reported. Output must be a **Pydantic schema** via `with_structured_output`, not parsed free text.
- Track in state which specialists have already reported, so the supervisor visits each **exactly once** and doesn't loop forever.

## Acceptance criteria

- [ ] Input `"Plan a 3-day trip to Goa, budget ₹15000"` returns weather-aware suggestions, **≥3 named places**, and a budget breakdown summing to **≤ the stated budget**.
- [ ] Each specialist is visited exactly once before assembly (print the visit order to prove it).
- [ ] **Actually unset the weather key** (`unset OPENWEATHER_API_KEY` or blank it in `.env`) and re-run — it degrades to Tavily instead of crashing. Don't assume this; test it.

## Pitfalls specific to this module

- **Supervisor infinite loops are the #1 failure here.** If the supervisor re-picks a specialist that already reported, you'll burn credits in a loop. Keep a `visited: list[str]` in state, have the supervisor read it, and pass `recursion_limit` to `invoke` as a backstop.
- The itinerary schema will fail on `gpt-oss-120b` unless you use `method="json_mode"` **and** spell out the field names in the prompt. See `AGENT_RULES.md` #2 — a nested day-by-day schema is exactly the case where this bites.
- ₹ and other non-ASCII currency symbols in prompts are fine, but don't rely on the model doing currency conversion silently. State the currency in the schema.

## Further steps & ideas

- Add a 4th specialist: `visa_agent` or `transport_agent` (flights/trains via Tavily).
- Swap `InMemorySaver` → `SqliteSaver` and build a Streamlit UI (reuse `ui_streamlit.py` from Module 10 nearly as-is).
- Add human approval before "booking" anything — Module 8's `interrupt()` pattern drops straight in.
- Make the supervisor's choice visible in the UI ("now asking the weather agent...") using `stream_mode="updates"`.
