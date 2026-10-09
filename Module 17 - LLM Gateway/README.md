# Module 17 — LLM Gateway

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

Route your Module 10 chatbot's LLM calls through **LiteLLM** with a real fallback — and **prove the fallback fires** by breaking the primary on purpose.

## Why this module exists

Right now your whole project dies if Groq has a bad afternoon. A gateway puts one layer between your code and the provider, so you get fallbacks, cost tracking, and the ability to switch models without touching your graph.

The lesson is **not** "install LiteLLM." It's that a fallback you haven't tested is not a fallback.

## Setup

```bash
cd "Module 17 - LLM Gateway"
uv init --no-readme --name module17-llm-gateway --python 3.12
rm main.py
uv add litellm langchain-litellm langgraph==1.2.0 langchain==1.3.1 python-dotenv pydantic langgraph-checkpoint-sqlite
cp "../Module 10 - Project - Build Your Own ChatGPT Agent/.env" .env
cp "../Module 10 - Project - Build Your Own ChatGPT Agent/backend.py" .
```

## Files to create

```
gateway.py     the LiteLLM Router config (2+ models under one alias)
backend.py     Module 10's backend, with the LLM call swapped
test_fallback.py  breaks the primary key on purpose, proves fallback
NOTES.md       your own notes afterwards
```

## Requirements

- A **`litellm` Router** with at least **2 models under one alias** — a primary and a fallback.
- Swap `init_chat_model(...)` for **either** `ChatLiteLLM(model=...)` **or** a direct `litellm.completion()` wrapper. Pick one and be consistent across the project.
- **A deliberate failure test:** set the primary's env var to an invalid key, run a **real** request, and show in the output that the Router fell back and the user still got an answer.
- **Cost tracking:** print `completion_cost(response)` for at least 3 real calls.

## ⚠️ Correction to the course brief

The brief suggests `groq/llama-3.3-70b-versatile` as the primary. **That model is decommissioned** — it will 404. Use instead:

```python
primary  = "groq/openai/gpt-oss-120b"
fallback = "groq/openai/gpt-oss-20b"        # or gemini/gemini-2.5-flash if you add a Google key
```

A same-provider fallback proves the *mechanism* but not resilience to a provider outage. If you have a Google or OpenAI key, use a **different provider** as the fallback — that's the realistic configuration.

## Acceptance criteria

- [ ] The fallback test is run **for real** — paste the actual console output showing the primary failing and the fallback succeeding.
- [ ] A one-paragraph note on what you'd set as `fallbacks=[...]` for a production version of Module 10, and why.

## Pitfalls specific to this module

- **LiteLLM's model-name format differs from LangChain's.** LangChain: `groq:openai/gpt-oss-120b` (colon). LiteLLM: `groq/openai/gpt-oss-120b` (slash). Mixing them gives confusing "model not found" errors.
- **An invalid key may raise instead of falling back** if the Router isn't configured with `fallbacks=[...]` and retry settings. A 401 is sometimes treated as non-retryable. If your test shows a crash instead of a fallback, that's the config, not the test.
- **`completion_cost()` can return 0.0** for models whose pricing LiteLLM doesn't know (newer/free models often). That's not a bug — note it rather than chasing it.
- Don't break the key by editing `.env` and forgetting to restore it. Override in-process instead: `os.environ["GROQ_API_KEY"] = "invalid"` inside the test file only.
- This module touches your working Module 10. **Copy it in, don't edit Module 10 in place** — keep a known-good version.

## Further steps & ideas

- Add a third model and set a priority order; test what happens when the first two fail.
- Add LiteLLM's caching so repeated identical questions cost nothing — then measure the saving.
- Set per-model rate limits in the Router and watch it load-balance.
- Run LiteLLM as a **proxy server** instead of in-process: one gateway, many apps, central key management. That's how teams actually deploy it.
- Feed cost-per-call into Module 15's "budgets" row and Module 16's `cost` column — the three modules connect here.
