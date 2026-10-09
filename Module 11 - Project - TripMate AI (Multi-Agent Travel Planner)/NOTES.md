# Module 11 — TripMate AI (Multi-Agent Travel Planner)

Your first **multi-agent** system: a supervisor that hands a trip request to three specialists, then assembles their answers into an itinerary.

## Run it

```bash
uv sync
uv run python main.py
```

Needs `GROQ_API_KEY` and `TAVILY_API_KEY`. `OPENWEATHER_API_KEY` is **optional** on purpose (see below).

---

## The idea: a boss and three workers

Modules 7–10 had *one* agent holding several tools. Here there are four separate workers, each with one job, and a **supervisor** deciding who works next.

```
START → parse_request → supervisor ⇄ weather
                                   ⇄ places
                                   ⇄ budget
                                   → assemble → END
```

The `⇄` matters: each specialist runs, writes its finding into state, and **returns to the supervisor**, which then picks the next one. That loop back is one line:

```python
for s in SPECIALISTS:
    g.add_edge(s, "supervisor")
```

**Why split one agent into four?** Each specialist gets a short, focused prompt and only the context it needs. One agent with four jobs and twelve instructions does all four worse — the same reason you'd split a 200-line function.

---

## 1. `parse_request` — turn a sentence into fields

`"Plan a 3-day trip to Goa, budget ₹15000"` is a string. The rest of the graph needs `destination`, `days`, `budget`, `currency`. One structured-output call does it:

```python
structured(TripParams,
  'Extract the trip details. Respond with JSON of the exact form '
  '{"destination": str, "days": int, "budget": int, "currency": str}...')
```

Do this **once at the start** rather than re-parsing the user's sentence in every node. Parse at the edge, pass structured data inward.

---

## 2. `supervisor` — `Command(goto=...)` and why it's deterministic here

```python
def supervisor(state) -> Command[Literal["weather", "places", "budget", "assemble"]]:
    done = state.get("visited", [])
    nxt = next((s for s in SPECIALISTS if s not in done), "assemble")
    return Command(update={"route_log": [nxt]}, goto=nxt)
```

`Command(update=..., goto=...)` is Module 5's pattern: update state **and** choose the next node in one return. No `add_conditional_edges` needed for the supervisor at all — the `Command` *is* the edge.

**A deliberate design choice:** this supervisor doesn't ask an LLM who should go next. It reads the `visited` list and routes to whoever hasn't reported. Reasons:

- **It cannot loop forever.** An LLM supervisor can re-pick a specialist that already ran, and you burn credits spinning. That's the #1 failure mode in multi-agent systems.
- **"Visit each specialist exactly once" becomes a guarantee**, not a hope. The `route_log` output proves it: `weather -> places -> budget -> assemble`.
- **The pattern being taught is identical.** `Command(goto=...)` works the same whether a `Literal` came from a model or from a list comparison.

Use an LLM supervisor when the route genuinely depends on the request ("this trip needs no budget agent"). When all specialists always run, deterministic is simply better engineering. `recursion_limit=25` is still passed as a backstop.

### How `visited` works

```python
visited: Annotated[list[str], operator.add]
```

Module 4's reducer, reused. Each specialist returns `{"visited": ["weather"]}` — a one-item list — and the reducer concatenates. The supervisor reads the accumulated list. Without the reducer each specialist would *overwrite* the others and the supervisor would never know anyone had run.

---

## 3. `weather` — graceful degradation, actually tested

The requirement was to handle a missing API key without crashing. Two paths:

```python
key = os.getenv("OPENWEATHER_API_KEY")
if key:
    ... urllib call to OpenWeatherMap ...
    except Exception as e:
        print(f"    [weather] OpenWeatherMap failed ({e}) — falling back to search")
# falls through to Tavily search + LLM summary
```

Note the `except` **falls through** rather than returning. A key that exists but is expired or rate-limited is a different failure from no key at all, and both should end up on the same fallback. A graph that dies because a weather API had a bad minute is a bad graph.

The output labels which path ran — `"(via web search — no weather API key set)"` — so you're never guessing whether you got real data.

---

## 4. `budget` — never let the model do the arithmetic

This is the most important lesson in the module.

```python
items = [i.model_dump() for i in plan.items]
total = sum(i["amount"] for i in items)   # Python, not the LLM
```

The LLM proposes *line items* — a judgement task, which it's good at. **Python sums them** — an arithmetic task, which it's unreliable at. If you ask the model for the total too, it will sometimes hand you a number that doesn't match its own list, and you'd have no way to notice.

And because the total is computed for real, the budget check is real:

```
TOTAL    7000   [OK, limit 15000]
```

There's also a **capped retry** — if the total exceeds the budget, it re-prompts once with the exact overage, then gives up:

```python
for _ in range(2):   # one retry, Module 5's capped-loop habit
    ...
    if total <= total_budget: break
    feedback = f" Your previous attempt totalled {total}, which is over by {total - total_budget}..."
```

Specific feedback ("over by 2300") works far better than "try again".

**The general rule:** let the model decide *what*, let code compute *how much*. Any time a number must be correct, compute it.

---

## 5. `assemble` — nested structured output

The itinerary is the one genuinely nested schema here (`Itinerary` contains a list of `DayPlan`). With `json_mode` you must spell the whole shape out, nesting included:

```python
'Respond with JSON of the exact form {"summary": str, "days": '
'[{"day": int, "morning": str, "afternoon": str, "evening": str}]}. '
f'Include exactly {state["days"]} day objects.'
```

The `"Include exactly N day objects"` line is load-bearing — without a count the model picks its own number of days.

---

## Verified output

```
Route taken : weather -> places -> budget -> assemble    <- each specialist exactly once
Weather     : warm, humid, ~29°C ... (via web search — no weather API key set)
Places (3)  : Baga Beach / Dudhsagar Falls / Basilica of Bom Jesus
TOTAL       : 7000   [OK, limit 15000]
Itinerary   : 3 days, each with morning / afternoon / evening
```

Worth noticing: the itinerary **used** the weather ("pack lightweight clothing... rain-poncho") and **used** the places and the budget figures. The specialists' outputs genuinely flowed into the final answer rather than being collected and ignored.

---

## Quick reference

| Node | Job | Key technique |
|---|---|---|
| `parse_request` | sentence → structured fields | one structured-output call at the edge |
| `supervisor` | pick who works next | `Command(update=..., goto=...)` + `visited` reducer |
| `weather` | conditions + packing advice | API with search fallback, error falls through |
| `places` | ≥3 real attractions | Tavily → structured extraction |
| `budget` | costed breakdown within budget | LLM for items, **Python for the sum**, one capped retry |
| `assemble` | day-by-day plan | nested `json_mode` schema with an explicit day count |

## Gotchas hit building this

- **`json_mode` everywhere.** Every structured call here needs `method="json_mode"` plus the exact field names in the prompt, or `gpt-oss-120b` fails. There are five such calls, so they're wrapped in one `structured()` helper rather than repeated five times — see `AGENT_RULES.md` #2.
- **`search()` returns a string and never raises.** `TavilySearch.invoke()` gives back a dict (`{"results": [...]}`), not text, and it can throw on a network blip. Flattening and catching inside one helper keeps every caller simple — the same "tools return errors as text" rule from Module 7.
- **Two aligned lists is a fragile schema.** `Places` uses `names: list[str]` + `why: list[str]` and relies on them being the same length. A `list[Place]` of objects would be safer; the prompt says "aligned" as a workaround. If you see a `zip()` silently dropping entries, this is why.
- **A specialist that forgets `"visited"`** will be re-selected forever by the supervisor. If you add a fourth specialist, add it to `SPECIALISTS` *and* return `{"visited": ["name"]}` from it.

## Not verified

The **OpenWeatherMap path has never run** — no key is set, so only the search fallback is exercised. The fallback is the tested path; if you add a key, test the real one and the expired-key case.

## Where to go next

- Add a 4th specialist (`transport` or `visa`): add to `SPECIALISTS`, return `{"visited": [...]}`, add one `add_edge`. Nothing else changes — that's the payoff of this shape.
- Make the supervisor LLM-driven and watch it loop. Then add the `visited` guard back. Best possible demo of why the guard exists.
- Swap `InMemorySaver` → `SqliteSaver` and reuse Module 10's `ui_streamlit.py` nearly as-is.
- Add human approval before "booking" — Module 8's `interrupt()` drops straight in.
- Stream with `stream_mode="updates"` to show "now asking the weather agent…" live.
