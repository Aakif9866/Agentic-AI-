# Agent Rules — paste this together with any module README

When you ask Claude Code (or any coding agent) to build a module in this repo, paste **this file first**, then the module's `README.md`. Without these rules the agent will cheerfully write 2023-era LangChain code that no longer runs.

---

## Tech stack — use exactly these, do not substitute older patterns

- **Python 3.12**, **uv** for dependencies (`uv init`, `uv add`). No `pip freeze`-style `requirements.txt` except when exporting for Docker.
- **`langgraph==1.2.0`**, **`langchain==1.3.1`** — the 1.x API: `create_agent`, `Command`, `Send`, `interrupt`. **Not** the deprecated 0.x `AgentExecutor` / `initialize_agent` / `Chain` classes.
- **`langchain-groq`** for the LLM unless a module specifically needs another provider.
- **Pydantic v2** — `model_dump()` not `.dict()`; `Field(...)` not deprecated validators.
- **`python-dotenv`** + one `.env` per module folder.

## Non-negotiables

- Every node returns **only the keys it changed**, never the whole state dict.
- Every tool's **docstring is the prompt** the model reads to decide whether to call it. Vague docstring = bug.
- Every tool that can fail **returns an error string, never raises**. A raise aborts the whole graph; a returned string lets the model read the error and retry.
- Every loop has **both** a `max_iteration` counter in state **and** a `recursion_limit` passed to `invoke`/`stream` as a backstop.
- **No hardcoded API keys, ever.** `load_dotenv()` / `os.environ` only.
- Prefer LangGraph's `StateGraph` over LangChain's old `AgentExecutor`. If using `create_agent` from `langchain.agents`, confirm it's the 1.x signature (`model`, `tools`, `middleware=[...]`, `checkpointer=...`), not `initialize_agent(llm, tools, agent=...)`.
- **A module is done only when it actually runs** via `uv run python <file>.py` and you've seen the real output. "It compiles" is not "it works."

## After each module, require this from the agent

1. The file tree actually created.
2. The exact commands run to verify it, **and their real output**.
3. One paragraph on what *you* should test yourself.

---

## Hard-won pitfalls from Modules 4–10 (this repo, real failures)

These cost real debugging time. Tell the agent about them up front.

### 1. Groq model names go stale — check, don't trust

`llama-3.3-70b-versatile` and `mixtral-8x7b-32768` are both **dead** (404 / decommissioned), despite appearing in every tutorial and in the course brief itself. Working models as of this repo:

```
openai/gpt-oss-120b     <- default for these modules
openai/gpt-oss-20b      smaller/faster
qwen/qwen3.8-27b        use when you need parallel tool calls (see #3)
```

Always verify against the live list before debugging anything else:

```bash
curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

Usage: `init_chat_model("groq:openai/gpt-oss-120b")`.

#### `init_chat_model` vs `ChatGroq` — neither is deprecated

Verified on `langchain 1.3.1` / `langchain-groq 1.1.3`:

```
DeprecationWarnings on call : NONE
init_chat_model("groq:...") -> langchain_groq.chat_models.ChatGroq
ChatGroq(model=...)         -> langchain_groq.chat_models.ChatGroq
IDENTICAL CLASS : True
```

**`init_chat_model` is a thin factory that imports and returns `ChatGroq`.** Same object, no warning, no deprecation marker. (Its docstring does say "legacy" once — that refers to legacy *OpenAI model names* like `text-davinci`, not to the function.)

| | `init_chat_model("provider:model")` | `ChatGroq(model=...)` |
|---|---|---|
| Provider | swappable via one string | hardcoded |
| Autocomplete on provider kwargs | weaker | better |
| Needs provider package imported | no | yes |
| Env-var provider switching | ✅ `CHAT_MODEL=openai:gpt-4o-mini` | ❌ code edit per file |

**This repo standardises on `init_chat_model`** — all 15 code modules use it. The reason is functional, not stylistic: it's what makes `CHAT_MODEL` env-var switching work (see `OpenAI.md`). With `ChatGroq` hardcoded, moving to OpenAI or DeepSeek means editing every file instead of setting one variable.

Use `ChatGroq` directly only when you need a Groq-specific constructor argument that the factory can't pass through.

### 2. `with_structured_output()` fails on gpt-oss — use `json_mode`

The default (tool-calling) mode errors with `Tool choice is required, but model did not call a tool`, consistently, on short prompts with simple schemas. Fix:

```python
llm.with_structured_output(MySchema, method="json_mode")
```

`json_mode` has **two requirements you must satisfy yourself**, because it only guarantees valid JSON — it knows nothing about your Pydantic schema:

1. The word **"json"** must literally appear in your prompt, or Groq rejects the request.
2. You must **spell out the exact field names**, or the model invents its own and validation fails. It returned `{"severity": ...}` when the schema wanted `level`.

```python
llm.with_structured_output(Priority, method="json_mode").invoke(
    'Classify severity. Respond with JSON of the exact form '
    '{"level": "critical"|"high"|"medium"|"low"}.\n' + text
)
```

### 3. `gpt-oss-120b` serializes tool calls

It will **not** emit two `tool_calls` in one turn, even when explicitly instructed to. If a module needs genuine parallel tool execution, use `qwen/qwen3.8-27b`. The graph supports parallelism either way — it's the model's choice, not the graph's.

### 4. The model will "helpfully" skip your tool

- Asked to send an email, it writes the email **as chat text** and never calls `send_email` — so any human-approval step never fires. Fix with a blunt system message: *call the tool, never reply with a plain-text draft, never ask the user to confirm.*
- It does easy arithmetic in its head and skips your calculator. Use ugly numbers (`18473 * 29361`) in demos.

### 5. Folder and path rules

- **No `:` in any folder name.** `uv run` errors with `path segment contains separator ':'`, and far worse, `source .venv/bin/activate` **silently fails** — you stay on system Python and get baffling import errors. This is true in the latest uv too; it is not a version bug. Every folder here uses ` - `.
- A `/` typed into a folder name in Finder creates a **nested directory**. That's how Module 9 ended up with a stray empty folder.

### 6. Dependency gotchas

- `langchain-huggingface` does **not** install `sentence-transformers`. Add it explicitly.
- `trim_messages(token_counter=llm)` needs `transformers` installed just to tokenize. Use `token_counter=len` (counts messages) unless you truly need token precision.
- `langchain-community` prints a sunset warning. It is still the correct home for `PyPDFLoader` and `FAISS` — there is no official standalone replacement yet (`langchain-pypdf` doesn't exist; `langchain-faiss` on PyPI is an unrelated third party, don't use it). Ignore the warning for now.
- `TavilySearch()` reads its API key **at construction time**. If a module builds it at import, that module must call `load_dotenv()` itself.
- Loading a FAISS index needs `allow_dangerous_deserialization=True` (it unpickles). Fine for an index you built; never for one you downloaded.

### 7. RAG quality
 
Clean PDF text **before** chunking. Our first retrieval returned the wrong chapter purely because of padding whitespace:

```python
for d in docs:
    d.page_content = " ".join(d.page_content.split())
```

Smaller chunks (400 / overlap 80) retrieved far better than 1000/200 on a short document.
