# 🔄 Using OpenAI instead of Groq

This repo defaults to **Groq** because it has a usable free tier. If you have an OpenAI key, switching is mostly configuration — and it makes three things in this repo *simpler*, not just different.

> ⚠️ **Verification status, stated honestly.** No OpenAI key was available in this environment, so **no OpenAI call in this guide has been executed.** What *was* verified: `langchain-openai` installs, `ChatOpenAI`/`OpenAIEmbeddings` import, and `init_chat_model("openai:gpt-4o-mini")` resolves the provider correctly — it fails with *"Missing credentials… set the `OPENAI_API_KEY`"* rather than "unknown provider", which proves the wiring is right and only the key is absent. Treat model names and cost figures as needing your confirmation. See [§8](#8-verification-status).

---

## 1. The 30-second version

```bash
# 1. install the provider package (once, per module you're switching)
uv add langchain-openai

# 2. put the key in that module's .env
echo 'OPENAI_API_KEY=sk-...' >> .env

# 3. switch
echo 'CHAT_MODEL=openai:gpt-4o-mini' >> .env
```

Module 10 already works this way — `CHAT_MODEL` and `EMBED_MODEL` are read from the environment with Groq as the default, so **nothing breaks if you don't set them.**

```python
# Module 10/backend.py — the pattern to copy into other modules
CHAT_MODEL = os.getenv("CHAT_MODEL", "groq:openai/gpt-oss-120b")
llm = init_chat_model(CHAT_MODEL).bind_tools(ALL_TOOLS)
```

---

## 2. 🧠 Don't trust model names — including mine

The single most repeated failure in this repo was **hardcoded model names that had been retired** (`llama-3.3-70b-versatile`, `mixtral-8x7b-32768` — both dead). That lesson applies to OpenAI too. My knowledge has a cutoff; yours doesn't.

**Always check what's live before debugging anything else:**

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | python3 -m json.tool | grep '"id"'
```

Pick from that list. Reasonable starting points *if they appear in your output*:

| Need | Candidate | Why |
|---|---|---|
| Default workhorse | `gpt-4o-mini` | cheap, fast, good tool calling |
| Harder reasoning | `gpt-4o` or a current flagship | when mini gets routing wrong |
| Embeddings | `text-embedding-3-small` | 1536 dims, cheap |
| Embeddings (better) | `text-embedding-3-large` | 3072 dims |

> 🚨 **`OpenAIEmbeddings()` defaults to `text-embedding-ada-002`** (verified by inspecting the installed signature) — an older generation. **Always pass `model=` explicitly.**

---

## 3. ✅ What does NOT change

Most of this repo is provider-independent. None of the following needs touching:

| Stays identical | Where |
|---|---|
| Graph structure — `StateGraph`, nodes, edges | all modules |
| State schemas, `Annotated` reducers, `operator.add` | M4, M5, M11, M13 |
| Checkpointers — `InMemorySaver`, `SqliteSaver` | M6, M9, M10 |
| `thread_id`, time travel, `get_state_history` | M6 |
| Streaming modes — `messages` / `updates` / `values` | M6, M9, M10 |
| `ToolNode`, `tools_condition`, the tool loop | M7+ |
| `interrupt()` / `Command(resume=...)` | M8, M14 |
| `Send`, `Command(goto=...)` | M5, M11 |
| Tool *bodies* — calculator, Tavily search, `send_email` | M7, M8, M10 |
| FastAPI, Dockerfile, CI, Streamlit UI | M9, M10 |
| Middleware stack and guardrail logic | M14 |

**The LangChain abstraction is doing real work here.** That's the point of `init_chat_model` taking a `"provider:model"` string.

---

## 4. 🎁 What gets *better* on OpenAI

### 4.1 Structured output stops needing the workaround

On Groq's `gpt-oss-120b`, `with_structured_output()` fails in its default (tool-calling) mode — `Tool choice is required, but model did not call a tool` — so every structured call in this repo uses `method="json_mode"` **plus** a prompt that spells out the exact field names ([`AGENT_RULES.md`](./AGENT_RULES.md) #2).

OpenAI supports native structured outputs properly, so you can drop both crutches:

```python
# Groq (what this repo does today)
llm.with_structured_output(Priority, method="json_mode").invoke(
    'Classify severity. Respond with JSON of the exact form '
    '{"level": "critical"|"high"|"medium"|"low"}.\n' + text
)

# OpenAI — the schema IS the contract
llm.with_structured_output(Priority).invoke(f"Classify severity:\n{text}")
```

**Why this matters:** `json_mode` only guarantees *valid JSON*, not *your* JSON — it once returned `{"severity": ...}` when the schema wanted `level`. Native structured output enforces the schema server-side, so the field-name prompt boilerplate becomes unnecessary.

**Affected files** (all currently carry the workaround): M5 `02`/`03`/`05`, M11 `main.py`, M13 both files, M14 `guardrails.py`.

### 4.2 Parallel tool calls just work

Module 7's `03_parallel_tool_calls.py` had to switch to `qwen/qwen3.8-27b` because `gpt-oss-120b` **serialises** tool calls — it won't emit two in one turn even when told to. OpenAI models do emit several, so:

```python
# Module 7/03_parallel_tool_calls.py
llm = init_chat_model("openai:gpt-4o-mini").bind_tools(tools)   # instead of groq:qwen/...
```

### 4.3 Token counting for `trim_messages`

Module 7's `04_trim_long_history.py` uses `token_counter=len` (counting *messages*) because `token_counter=llm` wanted `transformers` installed just to tokenise. With OpenAI, `tiktoken` is already a dependency of `langchain-openai`:

```python
trimmed = trim_messages(state["messages"], max_tokens=2000,
                        strategy="last", token_counter=llm,   # real tokens now
                        start_on="human", include_system=True)
```

---

## 5. ⚠️ Embeddings — the one genuinely breaking change

**Vector dimensions differ, and an index built with one model is unreadable by another.**

| Model | Dimensions |
|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` (current default) | **384** |
| `text-embedding-3-small` | **1536** |
| `text-embedding-3-large` | **3072** |

### FAISS (Modules 8, 10, 18, 22)

You **must rebuild the index**. Reading a 384-dim index with a 1536-dim model fails or returns nonsense:

```bash
rm -rf faiss_db
EMBED_MODEL=text-embedding-3-small uv run python ingest.py sample_notes.pdf
```

Module 10 already supports this — `tools.py` branches on the env var:

```python
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
if EMBED_MODEL.startswith("text-embedding-"):
    from langchain_openai import OpenAIEmbeddings
    EMBEDDINGS = OpenAIEmbeddings(model=EMBED_MODEL)
else:
    EMBEDDINGS = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
```

For Module 8, copy that block into `rag_shared.py` and `uv add langchain-openai`.

### Pinecone (Module 20)

The index's dimension is fixed **at creation**. Module 20's plan says `dimension=384` for MiniLM — with OpenAI you need `dimension=1536`, and a free-tier account may only allow one index, so you may have to delete and recreate it. Confirm before creating:

```python
print(len(EMBEDDINGS.embed_query("test")))   # use THIS number
```

### A real trade-off

Local MiniLM embeddings are **free and private** — text never leaves your machine. OpenAI embeddings are better but are a paid network call per chunk, and ingesting a large PDF embeds every chunk. **Keeping MiniLM for embeddings while using OpenAI for chat is a perfectly good hybrid**, and it's what the env-var split above allows.

---

## 6. 🗂️ Per-module changes

Find every site that needs editing:

```bash
grep -rn 'init_chat_model\|ChatGroq(' --include="*.py" . | grep -v '\.venv'
```

| Module | Change | Notes |
|---|---|---|
| **M4** `02`–`06` | `ChatGroq(model=...)` → `init_chat_model("openai:gpt-4o-mini")` | 5 files |
| **M5** all 5 | model string | `02`/`03`/`05` can also drop `method="json_mode"` |
| **M6** all 5 | model string only | memory/streaming unaffected |
| **M7** `01`,`02`,`04` | model string | `04` can use `token_counter=llm` |
| **M7** `03` | model string | ✅ *improves* — no longer needs qwen |
| **M8** `02`–`05` | model string | + embeddings block in `rag_shared.py`, **rebuild FAISS** |
| **M9** `backend.py` | model string | adopt M10's `CHAT_MODEL` env pattern |
| **M10** | ✅ **already done** | `CHAT_MODEL` + `EMBED_MODEL` env vars |
| **M11** `main.py` | model string | can drop `json_mode` in `structured()` helper |
| **M12** `client.py` | model string | MCP layer is provider-agnostic |
| **M13** both files | model string | can drop `json_mode` |
| **M14** `main.py` + `guardrails.py` | model string in **both** | `guardrails.py` builds its own judge |
| **M16–M22** | not built | use the `CHAT_MODEL` pattern from the start |

**M17 (LLM Gateway) is special** — its whole point is multi-provider. OpenAI is the natural *fallback* for a Groq primary. Note LiteLLM uses slashes, not colons:

```python
primary  = "groq/openai/gpt-oss-120b"
fallback = "openai/gpt-4o-mini"        # genuine cross-provider resilience
```

---

## 7. 💸 Cost — read this before you switch everything

Groq's free tier means a mistake costs nothing. **OpenAI bills per token**, and this repo contains loops.

Realistic hazards already present in the code:

- **M13's revision loop** — up to 3 drafts, each a full article.
- **M14's eval** — 5 cases × (supervisor + specialist + judge) ≈ 15 calls per run.
- **M16's planned eval harness** — 25+ cases, intended to run *on every push* in CI.
- **M18's CRAG/Self-RAG** — multiple graders per question, with retries.

Protect yourself:

1. **Set a hard spend limit** in the OpenAI dashboard (Billing → Limits). Do this *first*.
2. **Use `gpt-4o-mini`**, not a flagship, for everything except where quality visibly fails.
3. **Module 15's budget cap already helps** — `MAX_LLM_CALLS_PER_THREAD` bounds spend per conversation. Copy that pattern into any module with a loop.
4. **Hybrid:** OpenAI for chat, local MiniLM for embeddings. Embeddings are the high-volume call.
5. **Keep Groq for development**, switch to OpenAI only when you need the quality — the env var makes this a one-line flip.

---

## 8. Verification status

| Check | Status |
|---|---|
| `uv add langchain-openai` resolves and installs | ✅ verified (Module 10) |
| `ChatOpenAI`, `OpenAIEmbeddings` import | ✅ verified |
| `init_chat_model("openai:gpt-4o-mini")` resolves the provider | ✅ verified — fails on missing key, **not** unknown provider |
| `OpenAIEmbeddings` default is `text-embedding-ada-002` | ✅ verified by signature inspection |
| `CHAT_MODEL` env override is read end-to-end | ✅ verified — override reaches `init_chat_model`, blocked only by the absent key |
| Groq default still works after the refactor | ✅ verified — `9 × 9 = 81` through the full Module 10 agent |
| An actual OpenAI completion | ❌ **not run** — no key available |
| Structured output without `json_mode` | ❌ **not run** — documented from the API contract |
| Parallel tool calls on OpenAI | ❌ **not run** |
| OpenAI embeddings + FAISS rebuild | ❌ **not run** |
| Specific model names and prices | ❌ **not confirmed** — check the `/v1/models` endpoint |

**What to do first with a real key:** set a spend limit, then run Module 10 with `CHAT_MODEL=openai:gpt-4o-mini`. If `9*9` comes back as 81 through the calculator tool, the whole path works.

---

## 9. Other providers

`init_chat_model` takes `"provider:model"`, so the same pattern covers more than OpenAI:

```python
init_chat_model("groq:openai/gpt-oss-120b")       # current default
init_chat_model("openai:gpt-4o-mini")             # needs langchain-openai
init_chat_model("google_genai:gemini-2.5-flash")  # needs langchain-google-genai
init_chat_model("anthropic:claude-sonnet-4-5")    # needs langchain-anthropic
```

Each needs its own `langchain-*` package and `*_API_KEY`. **Same caveat as §2: verify the model name against that provider's live list.**
