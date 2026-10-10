# Module 17 — Multi-Provider LLM Gateway

One layer that knows which providers are configured, **what each can actually do**, and what to do when one fails. Groq + DeepSeek + Gemini, all verified.

## Run it

```bash
uv sync
uv run python probe_providers.py          # capability matrix (~4 calls/provider)
uv run python probe_providers.py --only deepseek   # re-check ONE, don't re-bill others
uv run python test_gateway.py             # 26 tests, 0 API calls, $0.00
uv run python live_check.py               # 4 real calls, ~$0.0002
```

Needs at least one of `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`.

---

## Prerequisites

- Modules 4–7 (you should recognise `init_chat_model`, tools, structured output)
- The `json_mode` workaround from [`AGENT_RULES.md`](../AGENT_RULES.md) #2 — this module *automates* it

## Minimum concepts

**"Gateway"** = one place your app asks for a model, instead of every file constructing its own. That buys you three things: swap providers without touching callers, fall back when one breaks, and enforce limits in a single spot.

**"Fallback"** = when provider A fails, try B. The hard part isn't trying B — it's knowing *whether A is worth retrying*. A 402 (no credit) will fail again in one second; a 429 (rate limit) might not.

---

## 🔬 The measured capability matrix

This is the module's foundation, and it is **measured, not assumed** (`probe_providers.py`, 2026-10-10):

| provider | model | chat | tools | **native** structured | `json_mode` |
|---|---|---|---|---|---|
| **groq** | `openai/gpt-oss-120b` | ✅ | ✅ | ❌ | ✅ |
| **deepseek** | `deepseek-chat` | ✅ | ✅ | ✅ | ✅ |
| **gemini** | `gemini-3.8-flash` | ✅ | ✅ | ✅ | ✅ |

**Groq is the odd one out** — it cannot do native structured output and needs `method="json_mode"` plus an explicit shape hint. DeepSeek and Gemini both can.

That single asymmetry is the gateway's whole reason to exist. Callers write:

```python
gw.structured(Verdict, "Classify: 'I love this'")
```

…and the gateway picks `json_mode` + hint for Groq, or the native path for the others. **Do not edit those flags from memory** — re-run the probe.

---

## File walkthrough

### `gateway.py`

**Provider registry** — facts, with provenance:

```python
PROVIDERS = {
  "groq":     Provider(..., native_structured=False, supports_tools=True),
  "deepseek": Provider(..., native_structured=True,  supports_tools=True),
  "gemini":   Provider(..., native_structured=True,  supports_tools=True),
}
```

**Failure classification** — the interesting bit:

```python
402 / 401 / 404 / insufficient balance  -> PermanentProviderError   (move on NOW)
429 / timeout / 5xx / connection        -> TransientProviderError   (move on, but it may recover)
unknown                                 -> TransientProviderError   (fail open)
```

Permanent vs transient doesn't change *this* call's behaviour (both fall through) — it changes what you're told, and whether a retry layer above should bother. A 402 means "go top up your account", a 429 means "wait a bit".

**Default order** — `groq,deepseek,gemini`, overridable via `GATEWAY_ORDER`:

- **Groq first** because its tier is **free**, so routine calls cost nothing.
- **DeepSeek second** — cheapest paid, and more capable than Groq for structured output.
- **Gemini last** — most capable (and the only vision-capable one), so reserve it for hard reasoning and images.

That ordering is a direct answer to a ₹500/month budget: free first, cheap second, strong only when needed.

**Observability** — every attempt is recorded:

```python
res = gw.chat("...")
res.provider     # 'deepseek'
res.fell_back    # True
res.attempts     # [Attempt(groq, ok=False, PermanentProviderError, '402 ...'), Attempt(deepseek, ok=True)]
```

**Bounded by default** — `GATEWAY_TIMEOUT_S` (30s) on every call, and `GATEWAY_MAX_CALLS` (200) as a per-process spend guard.

### `test_gateway.py` — 26 tests, zero cost

Fallback cannot be tested by hoping a provider breaks, so every failure is simulated. Covers classification, order config, fallback, all-fail, empty-order, capability-aware method selection, the spend guard, and that `status()` never leaks a key.

### `live_check.py` — 4 real calls

Only what mocks can't prove:

```
[1] normal call            -> served by groq, fell_back False
[2] groq key invalidated   -> path: groq(Permanent) -> deepseek, fell_back True
[3] structured via groq    -> sentiment=positive confidence=100
```

Step 2 is the real test. An **invalid key fails auth without billing tokens**, so forcing the failure is free — only the successful fallback costs anything.

---

## 🐛 Four bugs found while building this

### 1. `gemini-2.0-flash` and `gemini-2.5-flash` both 404

```
"This model models/gemini-2.5-flash is no longer available to new users.
 Please update your code to use models/gemini-3.8-flash"
```

**And `ListModels` had listed both as available.** That's the trap: the models endpoint shows what *exists*, not what *your key may call*. New keys are cut off from older models.

**Rule: only a real `generateContent` call proves availability.** Listing is not enough. This is the same class of failure as the three dead Groq model names, with a new twist.

### 2. `GEMINI_API_KEY` ≠ `GOOGLE_API_KEY`

`langchain-google-genai` reads **`GOOGLE_API_KEY`**, but Google issues the key as **`GEMINI_API_KEY`**. With only the latter set, you get "missing credentials" while staring at a key that's clearly there. The gateway bridges it:

```python
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
```

### 3. The spend guard was eaten by its own fallback loop

`_budget_check()` raised inside the per-provider `try`, so the broad `except` caught it, classified it as a provider failure, and reported **"all providers failed"** — wrong *and* alarming. Fixed with a dedicated `BudgetExceeded` type that is re-raised, never classified. **Caught by a mocked test, at zero cost.**

### 4. `order=[]` silently became the default

```python
order = order or fallback_order()      # [] is falsy -> default list
if order is None: order = ...          # fixed
```

"Explicitly no providers" and "unset" are different requests. Also caught by a mocked test.

### And one live-only bug: field names aren't enough

The first `json_mode` hint listed only key *names*. A real call returned:

```
{"sentiment": "positive", "confidence": 0.99}   -> ValidationError: int expected
```

The model read "confidence" as a probability — entirely reasonable. The hint now derives **types and enum values** from the Pydantic schema:

```
Respond with JSON of the exact form {"sentiment": "positive"|"negative", "confidence": int (whole number, not a decimal)}.
```

**Generalises the Module 5 lesson:** with `json_mode` you must state the exact *shape*, not just the keys. Now done automatically for any schema.

---

## Switching providers

```bash
GATEWAY_ORDER=gemini,deepseek          # prefer Gemini, fall back to DeepSeek
GATEWAY_ORDER=deepseek                 # single provider, no fallback
GATEWAY_TIMEOUT_S=15                   # tighter timeout
GATEWAY_MAX_CALLS=50                   # tighter spend guard
```

To change a model, edit its `Provider.model` in `gateway.py` — **and re-run `probe_providers.py`**, because capabilities are per-model, not per-provider.

Using the gateway from another module:

```python
import sys; sys.path.insert(0, "../Module 17 - LLM Gateway")
from gateway import chat, structured
print(chat("hello").value)
```

---

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `Missing credentials ... GOOGLE_API_KEY` | only `GEMINI_API_KEY` set | the bridge handles it; import `gateway` before building a model |
| `404 no longer available to new users` | Gemini model retired for new keys | use `gemini-3.8-flash`; **re-probe, don't trust ListModels** |
| `402 Insufficient Balance` | DeepSeek has no credit | top up; the gateway marks it Permanent and moves on |
| `all providers failed:` + details | every provider errored | the message now names each one and why |
| `spend guard: N calls already made` | `GATEWAY_MAX_CALLS` hit | raise it, or you have a loop |
| `ValidationError` on a `json_mode` provider | hint lacked types | fixed by `_json_hint`; check your schema is introspectable |

---

## Exercises

1. **Run `probe_providers.py --only gemini`** after a few weeks. Model availability changes; this is the one command that tells you the truth.
2. **Set `GATEWAY_ORDER=deepseek,groq`** and re-run `live_check.py`. Who serves step 1, and what does that cost you?
3. **Break two providers at once** and confirm the third serves it, and that `attempts` has three entries.
4. **Add a 4th provider** (OpenAI). It should be a single `Provider(...)` entry plus a probe run — if it needs more, the abstraction is leaking.
5. **Retrofit a module** — change Module 14's `guardrails.py` to use `gw.structured()` and delete its hand-written `json_mode` boilerplate.
6. Add per-provider cost tracking from `usage_metadata` and log cost per call. Feeds Module 15's budget row.

---

## Verified / not verified

**Verified:**

| Check | Result |
|---|---|
| Capability matrix, all 3 providers | measured — see table above |
| `test_gateway.py` | **26 passed, 0 failed, 0 API calls** |
| `live_check.py` normal call | served by groq |
| `live_check.py` **real fallback** | `groq(Permanent) -> deepseek`, `fell_back=True` |
| `live_check.py` structured output | `sentiment=positive confidence=100` |
| No key in any source file or output | grepped clean |

**Not verified:**

- **Tool calling *through the gateway*.** The probe confirms each provider emits `tool_calls`, but `gateway.py` has no `bind_tools` wrapper — callers use `get_llm(alias).bind_tools(...)` directly. Add `gw.with_tools()` if you want that path covered.
- **Gemini vision**, which matters for Module 22 — the model is vision-capable per Google's docs, but no image was sent here.
- **Transient (429) fallback** against a real provider. Only the permanent (402/401) path was forced live; 429 is covered by mocks.
- **Total live spend:** 4 calls in `live_check.py` + ~12 across probing ≈ **well under $0.01**.
