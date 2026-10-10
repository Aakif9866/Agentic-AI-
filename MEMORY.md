# MEMORY — session handoff

**Purpose:** paste this (plus [`AGENT_RULES.md`](./AGENT_RULES.md)) into a **new chat** so an agent can continue without re-reading the repo or rediscovering anything. Last updated 2026-10-10, after fixing the first red CI run (Module 18 import-time client).

---

## 1. State of the repo in one table

| Module | Status | What exists |
|---|---|---|
| 1 Foundations | 📖 theory | `info.txt`, `NOTES.md` |
| 2 Python Essentials | 📓 notebooks | `async.ipynb`, `pydantic.ipynb`, `NOTES.md` |
| **3 LangChain Agents** | ✅ verified | 2 uv projects + `NOTES.md`. **Not rotten after all** — already on LangChain 1.x (`create_agent`, `init_chat_model`, `langchain-tavily`). Multi-Agent pipeline runs end to end; both Streamlit apps boot (HTTP 200) |
| **4 LangGraph Fundamentals** | ✅ verified | 6 files in `project/` + `NOTES.md` |
| **5 Workflow Patterns** | ✅ verified | 5 files + `NOTES.md` |
| **6 Memory/Streaming/Threads** | ✅ verified | 5 files + `NOTES.md` |
| **7 Observability & Tools** | ✅ verified | 4 files + `NOTES.md` |
| **8 RAG & HITL** | ✅ verified | 5 files + `rag_shared.py` + `sample_notes.pdf` + `NOTES.md` |
| **9 Deployment** | ✅ verified | `backend.py`, `api.py`, Dockerfile (**image built + run**), CI yml, `NOTES.md` |
| **10 Capstone** | ✅ verified | `tools.py`, `backend.py`, `api.py`, `ingest.py`, `ui_streamlit.py`, `budget_demo.py`, `README.md`, **`ARCHITECTURE.md`**, `NOTES.md` |
| **11 TripMate** | ✅ verified | `main.py` + `NOTES.md` |
| **12 MCP** | ✅ verified | `notes_server.py`, `client.py`, `README_MCP.md`, `NOTES.md` |
| **13 Subgraphs** | ✅ verified | `research_subgraph.py`, `main.py`, `NOTES.md` |
| **14 Guardrails** | ✅ verified | `main.py`, `guardrails.py`, `test_guards.py` (5/5), `NOTES.md` |
| **15 Harness** | ✅ verified | `HARNESS_REVIEW.md`, `NOTES.md` + budget fix landed in Module 10 |
| **16 Evals** | ✅ verified | `target.py`, `evals/dataset.jsonl` (31), `evals/run_evals.py`, CI yml, `NOTES.md` |
| **18 CRAG + Self-RAG** | ✅ verified | `crag.py`, `self_rag.py`, `kb.py`, `test_caps.py`, `COMPARISON.md`, `NOTES.md` |
| **19 Self-correcting app** | ✅ verified | `graph.py`, `api.py`, `metrics.py`+`metrics.json`, Dockerfile (**container run**), `NOTES.md` |
| **21 FDE case study** | ✅ written | `fde-case-study.md` (§5 deploy is the one open gap), `NOTES.md` |
| **17 LLM Gateway** | ✅ verified | `gateway.py`, `probe_providers.py`, `test_gateway.py` (26 pass, 0 calls), `live_check.py`, `NOTES.md` — Groq+DeepSeek+Gemini, real fallback proven |
| 20, 22 | 📋 **not built** | `README.md` build spec only. 17 needs an OpenAI key to be meaningful; 20 needs Pinecone; 22 needs Neo4j **and** a vision model |

**Docs at root:** `README.md` (beginner roadmap) · `LEARNPLAN.md` (how to study) · `AGENT_RULES.md` (stack + pitfalls) · `OpenAI.md` (provider switch) · `VERIFICATION.md` (**proof + key matrix + costs**) · `.env.example` (every key annotated) · `verify.sh` (regenerate proofs into `proofs/`) · this file.

**Keys:** `GROQ_API_KEY` is the only one truly needed (modules 4–14, 16, 18, 19). `TAVILY_API_KEY` for 3, 7, 10, 11, 13, 18. Optional: `LANGSMITH_API_KEY` (6, 10), `OPENWEATHER_API_KEY` (11, degrades by design). Not-yet-built: `PINECONE_API_KEY` (20), `NEO4J_*` (22). Embeddings are local MiniLM — no key.

**Cost:** 252 counted model calls to run every built module once ≈ **$0.09** on a mini-tier model, ~$0.91 with 10x debugging headroom. OpenAI's $5 minimum is far more than enough. Groq free tier covers everything.

**DeepSeek:** `langchain-deepseek` v1.1.1 exists and `init_chat_model("deepseek:deepseek-chat")` resolves (fails on missing key, not unknown provider). Has `bind_tools` + `with_structured_output`. **No embeddings API** — pair with local MiniLM. Untested beyond wiring.

---

## 2. Non-negotiables (learned the hard way — don't rediscover)

0. **`init_chat_model` is NOT deprecated.** Verified: `init_chat_model("groq:...")` returns the *identical class* as `ChatGroq(model=...)` (`langchain_groq.chat_models.ChatGroq`), with no DeprecationWarning on langchain 1.3.1. It's a thin factory. The repo standardises on `init_chat_model` for a functional reason — it's what makes `CHAT_MODEL` env-var provider switching work. Don't "modernise" it to `ChatGroq`; that would break the OpenAI/DeepSeek path.
1. **Groq model names rot.** `llama-3.3-70b-versatile` and `mixtral-8x7b-32768` are **dead**. Use `openai/gpt-oss-120b`. Verify first:
   `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`
2. **`with_structured_output(X)` fails on gpt-oss.** Always `method="json_mode"`, with the word *json* in the prompt **and** the exact field names spelled out, or the model invents its own.
3. **`gpt-oss-120b` serialises tool calls.** Needs `qwen/qwen3.8-27b` for genuine parallel calls (Module 7 file 03).
4. **Never put `:` in a folder name.** Breaks `uv run`, and `source .venv/bin/activate` **silently** fails. All folders use ` - `.
5. **A module that builds a client at import must call `load_dotenv()` itself — and if a key-free test imports it, that client must be lazy.** Imports run before the importer's `load_dotenv()`. Bit Module 10's `tools.py` and Module 14's `guardrails.py`. Then bit CI (2026-10-10): `test_caps.py` imports `self_rag.py`, which called `init_chat_model()` at module level; `langchain_groq` raises on a missing key, so the deliberately secretless `tests.yml` job died *before the first assertion*. It passed locally only because a `.env` was sitting in the folder. Both Module 18 clients are now `@lru_cache` factories — `self_rag.llm()` and `kb.embeddings()` — so importing the module needs no key and no 90MB MiniLM download. **Reproduce CI properly:** `env -u GROQ_API_KEY HF_HUB_OFFLINE=1 uv run python test_caps.py` with `load_dotenv` stubbed out.
6. **Tools return errors as strings, never raise.** A raise kills the graph.
7. **Every loop needs `max_iteration` in state AND `recursion_limit` on invoke.**
8. **Nodes return only changed keys.** Returning whole state breaks reducer merges.
9. **New state field = two edits.** Add to the schema *and* `StateGraph(NewState)`. Miss the second and it's silently dropped.
10. **Don't stream and then `invoke` the same input** — pays for everything twice.

---

## 3. Verified facts worth not re-testing

- `uv run` + `source activate` both work since the colon-free rename.
- Module 9's Docker image **builds and serves** `/health` + `/chat` from inside the container.
- Streamlit UI boots clean (HTTP 200), never clicked through.
- `langchain-community` sunset warning is **expected** — still the correct home for `PyPDFLoader`/`FAISS`. `langchain-pypdf` doesn't exist; `langchain-faiss` on PyPI is unrelated third-party, **do not use**.
- `trim_messages(token_counter=llm)` needs `transformers`; use `token_counter=len` (counts messages).
- `langchain-huggingface` does **not** pull `sentence-transformers` — add it explicitly.
- MCP: `client.get_tools()` opens a **new subprocess per call**, so stateful servers lose state. Hold `client.session()` open.
- HITL resume shapes **differ**: plain `interrupt()` → `Command(resume="yes")`; `HumanInTheLoopMiddleware` → `Command(resume={"decisions": [{"type": "approve"}]})`.
- Clean PDF whitespace **before** chunking; 400/80 beat 1000/200 on a short doc.
- Module 16 target is **Module 14** (light deps), not Module 10.
- Routing signal = **tool name + docstring + system prompt**. Vaguing only the docstring changed nothing.

---

## 4. Tooling actually available (checked, not assumed)

| Available | Not available |
|---|---|
| Ponytail skills (auto-active, level `full`) | **Context7** |
| Railway MCP, Claude Docs MCP | **Sequential Thinking** |
| `docker`, `uv`, `node`, `npx`, `curl` | **GitHub MCP / `gh` CLI** (absent) |

⚠️ `ponytail-audit` is scoped to **over-engineering only** (`delete`/`stdlib`/`yagni`/`shrink`) and explicitly routes correctness/security elsewhere. It is **not** a production-readiness review. Its verdict on Module 10: `Lean already. Ship.`

---

## 5. 🔑 When the OpenAI key returns — do exactly this

[`OpenAI.md`](./OpenAI.md) is written but **no OpenAI call has ever been executed**. What *was* verified: `langchain-openai` installs, imports work, and `init_chat_model("openai:gpt-4o-mini")` fails on the **missing key** rather than an unknown provider — so the wiring is correct.

Checklist, in order:

1. **Set a hard spend limit** in the OpenAI dashboard *first*. This repo contains loops.
2. Confirm live model names: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`. Names in `OpenAI.md` are **unconfirmed**.
3. Smoke test — Module 10 already reads env vars, no code change:
   ```bash
   cd "Module 10 - Project - Build Your Own ChatGPT Agent"
   CHAT_MODEL=openai:gpt-4o-mini uv run python -c "
   from backend import agent
   print(agent.invoke({'messages':[('user','What is 9*9?')]},
       {'configurable':{'thread_id':'oa1'},'recursion_limit':25})['messages'][-1].content)"
   ```
   `81` via the calculator tool ⇒ the whole path works.
4. **Then verify the three claims in `OpenAI.md` that are documented-but-untested:**
   - structured output works **without** `method="json_mode"` and without field-name boilerplate
   - parallel tool calls work (so Module 7 file 03 no longer needs qwen)
   - `trim_messages(token_counter=llm)` works (tiktoken ships with `langchain-openai`)
5. Embeddings are the **one breaking change**: 384 → 1536 dims. `rm -rf faiss_db` then re-run `ingest.py` with `EMBED_MODEL=text-embedding-3-small`. Pinecone (Module 20) needs `dimension=1536`.
6. **Module 17 genuinely needs this key** — a Groq→Groq fallback proves the mechanism but not provider-outage resilience.
7. Update the verification table in `OpenAI.md` §8 with what actually passed.

---

## 6. Remaining work, prioritised

| # | Task | Cost | Notes |
|---|---|---|---|
| 1 | **Module 17** LLM Gateway | low | ⚠️ brief names a dead model; needs OpenAI key to be meaningful |
| 2 | **Module 18** CRAG + Self-RAG | medium | reuse Module 8's `rag_shared.py` + `sample_notes.pdf`; most loop-prone module |
| 3 | **Module 19** serverless writer/reviewer | medium | reuse Module 9's `api.py`+Dockerfile; watch serverless timeouts |
| 4 | **Module 20** Agentic RAG | medium | needs `PINECONE_API_KEY`; **dimension must match embeddings** |
| 5 | **Module 21** FDE case study | low | needs Module 16 (done) for real before/after numbers |
| 6 | **Module 22** GraphRAG + Multimodal | **high** | needs Neo4j Aura **and** a vision model — **check Groq has one before starting**; likely blocked without OpenAI/Gemini |
| 7 | `ARCHITECTURE.md` for Modules 9, 14, 11 | low | Module 10's is the template |
| 8 | `NOTES.md` for Modules 17–22 | — | write as each is built |
| ~~9~~ | ~~Move CI workflows to repo root~~ | — | ✅ **done** — see §6c |
| 10 | Module 10's weak harness rows | low | Verification, Observability, Context trimming, thread deletion — all in `HARNESS_REVIEW.md` §11 |

**Keys now configured:** Groq ✅, DeepSeek ✅ (was 402, now topped up ~$2), Gemini ✅. Still missing: `PINECONE_API_KEY` (M20), `NEO4J_*` (M22).

**Measured provider capabilities** (Module 17's probe, re-run it rather than trusting this): groq=chat/tools/json_mode but NO native structured output; deepseek=all four; gemini=all four + vision. Verified Gemini model is `gemini-3.8-flash` — 2.0/2.5 are 404 for new keys.

**Budget: ~₹500/month.** Default gateway order `groq,deepseek,gemini` = free, cheapest paid, then most capable. Mocked tests cost nothing; live checks are deliberately 4 calls.

**Done since:** 17, 18, 19, 21, plus Module 3 repaired and CI moved to the repo root. **Remaining: 20 (needs `PINECONE_API_KEY`) and 22 (needs `NEO4J_*`; Gemini unblocks its vision half).** **Remaining:** 17 (needs OpenAI key), 20 (Pinecone), 22 (Neo4j + vision model — check Groq has one first).

---

## 6b. ⚠️ Virtual envs were deleted to reclaim disk (2026-10-10)

The Mac was down to **2.6 GB free of 245 GB**, which was causing swap thrashing. All `.venv` folders for Modules 4–19 were deleted, plus `~/.cache/uv`, `__pycache__`, and two `*:ci` Docker images — about **5.9 GB** reclaimed.

**Consequence: every module needs `uv sync` before it will run again.** Module 3's two venvs were deliberately left alone (pre-existing, and that module is bit-rotten — its venv may be the only environment where it works).

Because the uv cache was also cleared, the *first* `uv sync` re-downloads. Modules 8, 10 and 18 pull `torch`/`sentence-transformers` (~1 GB each, shared once cached), so sync those on a decent connection.

```bash
cd "Module 4 - LangGraph Fundamentals/project" && uv sync   # ~40MB, fast
cd "Module 8 - RAG & Human-in-the-Loop" && uv sync          # ~960MB, slow first time
```

Disk is still tight. The big remaining items are **outside this repo** and the user's call: `~/Library/Caches` (13 GB), `~/Downloads` (3.1 GB), `~/Documents` (50 GB), `~/anaconda3` (4.9 GB), Docker's data (~5.3 GB).

## 6c. CI workflows (now at the repo root, so they actually run)

| Workflow | Trigger | Needs secrets? | Cost |
|---|---|---|---|
| `tests.yml` | **every push + PR** | ❌ none | **$0** — M17 gateway (26 mocked), M18 caps (11), M4 graph, plus a secret scan |
| `live-evals.yml` | **manual only** (`workflow_dispatch`) | `GROQ_API_KEY` | ~60 calls at `--quick 0`; defaults to `--quick 8` |
| `docker-build.yml` | push to M9/M19 paths | none to *build* | $0; starting a container is manual-only |

Default CI is free and secretless by design, so it runs on forks and can't bill you. The module-local copies were deleted — GitHub only reads `.github/workflows/` at the repo root.

**CI has no `.env` and no secrets.** Anything `tests.yml` imports must therefore be importable with zero keys — that is the rule the first red run taught (see §2 #5). Before adding a step, run it the way CI will: key unset, no `.env`.

**The secret scan is deliberately strict** (no allowlist). It caught my own dummy `gsk_invalid_...` in `live_check.py`; the fix was renaming the dummy, not weakening the rule.

## 6e. `proofs/` — transcripts for 13 of 16 built modules (2026-10-10)

`./verify.sh` now writes a `proofs/module-N.txt` per module, each stamped with the commit SHA, UTC time, the directory and the exact command. Two new flags: `--sync` (runs `uv sync --frozen` first, because the venvs aren't committed) and the `api` helper, which boots `uvicorn`, polls `/health`, fires one real request and always kills the server.

**PASS, real output committed:** 4, 5, 6, 7, 8, 9, 10 (API **and** budget guard), 11, 12, 13, 14, 16 (`--quick 8`), 17 (mocked **and** live fallback), 18 (caps + Self-RAG + CRAG), 19 — **15 of the 16 built modules.**

**Still owed: Module 3 only.** It is the heaviest single run in the repo (a full multi-agent pipeline, ~2,600 tokens) and the day's budget was down to 5 tokens. Nothing is wrong with the code — the same run passed by hand on 2026-10-10. Re-run `./verify.sh --paid --module 3` first thing after the quota resets, before spending the day's tokens on anything else.

`proofs/module-3.txt` is committed but is **not a proof** — it is the 429 transcript (`Used 199998, Requested 1715`, dying in step 1 of 4). It is in the repo as a record of where the budget ran out; the next successful run overwrites it.

### ⚠️ A check that cannot fail is worth nothing — the `api` helper proved it

First version of `api()` ended on `echo`, so `bash -c` returned the exit status of *that*, not of the request. Module 10 printed `curl: (7) Failed to connect` and the script still reported **PASS**. Now: the `/health` poll `exit 1`s if it never answers (90 tries × 2s — Module 10 loads torch and FAISS before it serves), and the request uses `curl --fail-with-body ... || exit 1`. The rerun correctly reported FAIL. **Check the failure path of any new check before trusting its PASS.**

### Two labels that oversold what they ran

- `budget_demo.py` needs **`MAX_LLM_CALLS_PER_THREAD=3`**. The default cap is 12 and the demo only takes 6 turns, so at the default the guard *cannot* trip — the first proof said "budget guard trips" over a transcript where nothing tripped. That env var is the whole before/after switch (see the file's own docstring).
- Module 8's approve path **did not fire** in its transcript: the model replied *"Would you like me to go ahead?"* instead of calling `purchase_stock`, so no `interrupt()` happened and the script correctly printed `No approval was requested`. The reject path did pause and decline properly. Model nondeterminism, not a bug — but the proof only half-covers the module. Re-run it to catch the approve path.

Each invocation truncates only the files it writes (`SEEN` string, not an assoc array — **macOS ships bash 3.2, no `declare -A`**), so re-running one module doesn't wipe the rest and doesn't append duplicates either.

### ⚠️ Groq free tier is 200,000 tokens per DAY, per model

Generating the proof set exhausted it: `429 ... on tokens per day (TPD): Limit 200000, Used 197989`. It frees up **gradually** rather than all at once — retrying after ~10 minutes got Modules 8, 9 and 10 through, while Module 3 (the biggest single run) still could not fit. Treat the remaining headroom as the scarce thing: run the expensive module FIRST. There is no retry that beats a genuinely spent budget — the remaining proofs wait for the reset. Plan a full `./verify.sh --paid` as a once-a-day operation, and prefer `--quick 8` over the full 31-case eval suite unless the full number is the point.

### ⚠️ Disk: 3.9 GB free after syncing Modules 8, 9 and 10

Modules 8 and 10 pull `torch` via `sentence-transformers`. Syncing both took the Mac from 5.3 GB to 3.9 GB free. See §6b — this is still the binding constraint on how many venvs can exist at once.

## 6d. ⚠️ Renaming a folder breaks that project's venv

Discovered via Module 3: venv **console scripts embed the absolute path**. After the colon-free rename, `uv run streamlit` failed with *"Module 3 — Agents .../python3: No such file or directory"* (em-dash) while `uv run python` still worked, because uv resolves the interpreter itself but not the wrapper scripts.

Modules 4–19 were rebuilt after renaming so they were fine; Module 3's preserved venvs kept the stale paths.

**If you rename a project folder, run `uv sync` in it.** A byte-level path rewrite is *not* a safe shortcut: I tried it and corrupted 2,769 `.pyc` files, because the em-dash is 3 bytes and the hyphen is 1, which breaks length-prefixed bytecode strings (`UnicodeDecodeError: invalid continuation byte`). Recovered by deleting all `__pycache__` — `.pyc` is pure cache and regenerates.

## 7. Working agreements that held up

- **One module per session.** Build → run → fix → `NOTES.md` → commit → push. Never two in flight.
- **Commit each module separately**, so running out mid-work loses nothing.
- **Nothing is "done" until it has actually run** and the real output is pasted. "It compiles" ≠ "it works".
- **State unverified things explicitly.** Every `NOTES.md` has a *"Gotchas hit"* and some a *"Not verified"* section. Keep that habit — it's the most valuable content in the repo.
- **Probe unknown APIs with `inspect.signature()` before writing against them.** Saved debug loops in Modules 12, 14 and 16.
- **When an eval fails, suspect the eval.** In Module 16's first run, 2 of 7 failures were the dataset's fault, not the agent's.
- Secrets: `.env` per module, gitignored; `*.db`, `faiss_db/`, `.venv/` ignored. Check `git status` before every commit.

---

## 8. Commit trail

```
8f4686c  Fix CI: Module 18 built its Groq client at import (first red run, now green)
9c36fba  Repair Module 3, move CI to repo root, final MEMORY.md update
b3b999b  Module 17 complete: multi-provider gateway
e9f73cc  README: mark Module 16 built
22dadcf  Module 16 complete: eval harness that found 3 real bugs in Module 14
2ec64cc  Add OpenAI.md; make Module 10 provider-switchable by env var
75fa838  Module 15 complete: harness audit + real budget fix
5443728  Rewrite README as beginner-first roadmap
b03ba1f  Module 14 complete: layered guardrails
38ec458  Module 13 complete: subgraphs + AgentWriter
0120599  Module 12 complete: MCP server + client
04880a0  Module 11 complete: TripMate AI
8c34878  LEARNPLAN + AGENT_RULES + plans for 11-22
8fd28a1  Modules 5-10; colon-free folder rename
03d733e  Module 4
```

Remote: `github.com:Aakif9866/Agentic-AI-.git` · branch `main`
