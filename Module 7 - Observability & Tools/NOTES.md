# Module 7 — Observability & Tools

Module 6's chatbot could only talk. This module lets it *do things* — call a calculator, search the web — and keeps the conversation from outgrowing the model's context window.

## Run it

```bash
uv sync
uv run python 01_single_tool.py
```

Needs `GROQ_API_KEY`; file 02 also needs `TAVILY_API_KEY` (free at tavily.com).

---

## 1. `01_single_tool.py` — the tool-calling loop, drawn as a graph

**The idea:** a tool-using agent is a **loop between two nodes**.

```
chat → did the model ask for a tool? → tools → chat → ... → END
```

Two prebuilt pieces do the work:

- `ToolNode(tools)` — runs whatever tools the last AI message requested.
- `tools_condition` — the router: sends you to `"tools"` if the model asked for one, otherwise to `END`.

```python
graph.add_conditional_edges("chat", tools_condition)
graph.add_edge("tools", "chat")       # the loop: results go back to the model
```

Running it prints the real message trail, which is the clearest way to see the loop:

```
human: What's 17% of 2340, then add 50?
ai:    asked for tool -> calculator({'expression': '0.17*2340+50'})
tool:  447.8
ai:    The answer is 447.8
```

**One rule that matters:** a tool returns its errors **as text**, never by raising.

```python
except Exception as e:
    return f"error: {e}"
```

A raised exception kills the graph. A returned error string goes back to the model, which can read it and try again.

**Takeaway:** the loop is `chat → tools → chat`. `tools_condition` decides when to stop.

---

## 2. `02_multi_tool_agent.py` — several tools, and the model picks

**The idea:** you don't write routing logic for tools. The model chooses, based on **the tool's docstring**. A vague docstring is a bug — it's literally the prompt the model reads to decide.

Back that up with a system message that says when to use what:

```python
SYSTEM = SystemMessage(content=(
    "- Use `calculator` for any math.\n"
    "- Use `tavily_search` only for current events or facts you're unsure of.\n"
    "Answer directly when no tool is needed."
))
```

The file asks three questions and prints which tool got picked:

| Question | Tool used |
|---|---|
| "What's 144 divided by 12?" | `calculator` |
| "Who won the most recent F1 championship?" | `tavily_search` |
| "What does 'agentic' mean?" | *none* — answered directly |

That third row is the important one. A good agent knows when **not** to use a tool.

**Takeaway:** docstrings are prompts. Write them for the model, not for yourself.

---

## 3. `03_parallel_tool_calls.py` — two tools in one turn

**The idea:** if a model requests two tools in a single turn, `ToolNode` runs them **together** rather than one after the other.

```
One model turn requested 2 tool(s) at once:
  - calculator({'expression': '18473 * 29361'})
  - get_fact({'topic': 'Docker'})
```

**The catch we discovered:** whether this happens is the **model's** choice, not the graph's. `openai/gpt-oss-120b` always serializes — it calls one tool, waits, then calls the next, even when explicitly told to do both at once. So this file uses `qwen/qwen3.8-27b`, which does emit both in one turn.

**Takeaway:** your graph supports parallel tool calls for free. Whether you get them depends on the model. If latency matters, test your specific model.

---

## 4. `04_trim_long_history.py` — keeping context bounded

**The problem:** conversations grow forever. Context windows don't.

**The fix:** trim what the **model sees** per turn, while the checkpoint keeps everything.

```python
trimmed = trim_messages(
    state["messages"],
    max_tokens=6,
    strategy="last",      # keep newest, drop oldest
    token_counter=len,
    start_on="human",     # never start mid tool-call
    include_system=True,  # always keep the system message
)
return {"messages": [llm.invoke(trimmed)]}
```

Output shows both numbers at once:

```
[model sees 6 of 13 messages]
...
Full checkpoint still holds 14 messages — nothing was deleted.
```

Two options worth understanding:

- `start_on="human"` — prevents a window that begins with a tool result whose request got cut off (which confuses the model).
- `include_system=True` — the system message is your instructions; losing it changes the agent's behaviour.

**`token_counter=len` counts messages, not tokens.** `token_counter=llm` would count real tokens but needs `transformers` installed just to tokenize — not worth a 500MB dependency for a demo. Swap it in when you actually need token precision.

**Takeaway:** trim the model's *view*, never your stored history. Storage is cheap; context is not.

---

## Quick reference

| File | Pattern | Key API |
|---|---|---|
| 01 | tool-calling loop | `ToolNode`, `tools_condition` |
| 02 | multi-tool selection | docstrings + system prompt |
| 03 | parallel tool calls | one AI turn, several `tool_calls` |
| 04 | bounded context | `trim_messages(strategy="last")` |

## Gotchas we hit building this

- **`eval()` in a calculator tool is a real risk.** The expression comes from an LLM, which can be steered by prompt injection. These files whitelist the input first (`[0-9.\s+\-*/%()]+`), so no names can appear and no attribute tricks are possible. Don't ship a bare `eval`.
- **A model will do easy math in its head** and skip your calculator, which makes tool demos look broken. File 03 uses `18473 * 29361` on purpose — too hard to fake.
- **Tool errors must be returned, not raised** — a raise aborts the whole graph run.
