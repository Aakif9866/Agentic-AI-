# Verification — evidence that this actually runs

Real output from real runs against live APIs, captured while building Modules 4–21 on **2026-10-09 / 2026-10-10**. Nothing here is reconstructed or illustrative.

**Regenerate it yourself:**

```bash
./verify.sh            # free checks only — no API calls, no cost
./verify.sh --paid     # everything, ~250 model calls (≈ $0.09, see §4)
./verify.sh --module 4 # one module
```

Each run writes `proofs/module-N.txt` stamped with the **commit SHA and UTC time**, so the evidence says *which version* produced it. That's stronger than a screenshot — copy-pasteable, diffable, and hard to fake by accident.

> 📸 **On screenshots:** I can't produce image files. If you want images for a README, run `./verify.sh --paid` then screenshot the `proofs/*.txt` files (macOS: ⌘⇧4). The transcripts are the better artefact; screenshots are the prettier one.

---

## 1. Live regenerated proof (in `proofs/`, commit `ca9f93b`)

```
=== Module 4 — state/nodes/edges (no LLM)
commit: ca9f93b   UTC: 2026-10-10T09:46:38Z
cmd   : uv run python 01_temperature.py
----------------------------------------------------------------------
{'celsius': 28.5, 'fahrenheit': 83.3, 'label': 'Hot'}
[exit 0]
```

```
=== Module 18 — loop caps (pure logic)
commit: ca9f93b   UTC: 2026-10-10T09:46:38Z
cmd   : uv run python test_caps.py
----------------------------------------------------------------------
MAX_RETRIES=2  MAX_REWRITE_TRIES=2
all 11 cap assertions passed - both loops bounded, and independently
[exit 0]
```

---

## 2. The headline results

### Module 16 — eval suite, 31 cases

```
            answer tool_selection trajectory latency safety  cases
correctness    83%            n/a        n/a    100%   100%      6
latency       100%           100%       100%    100%   100%      4
safety         n/a           100%       100%    100%   100%     11
tool_use       n/a           100%       100%    100%   100%     10

OVERALL: 116/117 checks passed = 99.1%  (threshold 80%)
RESULT: PASS
```

**Before the guardrail fixes it scored 88.6%** (101/114). The suite found three real bugs in Module 14 — including that *"Ignore all previous instructions"* was **not blocked**, the commonest injection phrasing in the wild.

### Module 16 — regression detection (deliberately broken tool)

```
         answer tool_selection trajectory latency safety  cases
tool_use    n/a            25%        25%    100%    75%      4

OVERALL: 9/16 checks passed = 56.2%  (threshold 80%)
RESULT: BELOW THRESHOLD          <- exit code 1, CI fails the build
```

### Module 14 — 5 adversarial guardrail cases

```
case                      expected            got                       note
prompt injection          blocked_injection   blocked_injection   PASS  refused, no tools called
off topic                 blocked_offtopic    blocked_offtopic    PASS  refused, no tools called
PII redaction + routing   billing_agent       billing_agent       PASS  tools=['billing_agent'] | email redacted
escalation pauses         interrupt           interrupt           PASS  paused for human approval
normal technical          technical_agent     technical_agent     PASS  tools=['technical_agent']
5/5 passed

still paused after resume : False
```

### Module 18 — CRAG routed all three branches

```
Q: What does a checkpointer do?
   scores: [0.3, 0.9, 0.7, 0.0]   decision: CORRECT    -> source: kb
Q: What is a reducer and why is it needed?
   scores: [0.4, 0.5, 0.0, 0.0]   decision: AMBIGUOUS  -> source: kb+web
Q: What is the capital of Peru?
   scores: [0.0, 0.0, 0.0, 0.0]   decision: INCORRECT  -> source: web
   rewritten: What is the capital city of Peru?   A: Lima.
```

### Module 19 — writer/reviewer convergence (`metrics.json`)

```
iteration_distribution: {'1': 5, '2': 1}
mean_iterations: 1.17   approved: 6   hit_cap: 0   converged_within_3: 6
```

### Module 15 — budget cap, before vs after

```
BEFORE (MAX_LLM_CALLS_PER_THREAD=999)      AFTER (=3)
turn 1: llm_calls=1  answered              turn 1: llm_calls=1  answered
turn 4: llm_calls=4  answered              turn 4: llm_calls=3  REFUSED (no model call spent)
turn 6: llm_calls=6  answered              turn 6: llm_calls=3  REFUSED (no model call spent)
total charged: 6                           total charged: 3
```

The counter **freezing at 3** is the proof that refusals cost nothing.

### Module 10 — capstone, through a live server

| # | Check | Result |
|---|---|---|
| 1 | `GET /health` | `{"ok":true}` |
| 2 | calculator tool | `18473 * 29361` → 542,385,753 |
| 3 | memory on one `thread_id` | recalled the previous question |
| 4 | RAG with citation | answered from the PDF, cited `page 0` |
| 5 | `send_email` pauses | empty stream, as designed |
| 6 | `GET /pending/{id}` | returned the full draft |
| 7 | `POST /approve` + `edited_body` | resumed, returned final message |
| 8 | `/pending` after approval | `null` |
| 9 | `GET /threads` | all threads listed |
| 10 | `tavily_search` | live web answer |
| 11 | **human's edit reached the tool** | `{"status":"sent","body":"EDITED BY HUMAN: Q4 was great."}` |

Row 11 is what proves human-in-the-loop is real rather than cosmetic.

### Modules 9 & 19 — Docker

```
Module  9: docker build OK → container serves /health {"ok":true} and /chat "container works"
Module 19: docker build OK (342MB) → container /generate → verdict=approved iters=1 words=52/60
```

### Module 12 — MCP round-trip

```
Tools discovered over MCP: ['add_note', 'search_notes']
> Search my notes for anything about the budget.     tools used: ['search_notes']
  Here are the notes that mention budget:
  - The Goa trip budget is 15000 rupees.
```

---

## 3. Per-module status

| Module | Runs | Evidence |
|---|---|---|
| 1, 2 | n/a | theory / notebooks |
| 3 | ⚠️ untested | legacy LangChain, likely bit-rotten |
| 4 | ✅ | all 6 files |
| 5 | ✅ | all 5 files |
| 6 | ✅ | all 5; SQLite persistence proved by running twice (1→2 threads) |
| 7 | ✅ | all 4; parallel tool calls needed `qwen` |
| 8 | ✅ | all 5 + ingest; HITL approve **and** reject |
| 9 | ✅ | API + **container** |
| 10 | ✅ | 11-point check above |
| 11 | ✅ | each specialist once; budget ₹7000 ≤ ₹15000 |
| 12 | ✅ | MCP round-trip |
| 13 | ✅ | pipeline + subgraph standalone |
| 14 | ✅ | 5/5 + resume |
| 15 | ✅ | before/after + no regression in M10 |
| 16 | ✅ | 31 cases + regression demo |
| 18 | ✅ | both graphs, 3 branches, 11 cap assertions |
| 19 | ✅ | metrics + API + container |
| 21 | ✅ written | all links verified to resolve |
| 17, 20, 22 | ❌ not built | blocked on keys — see §5 |

### Honestly not verified

- **No cloud deployment anywhere.** Containers run locally; nothing is hosted. Module 21 §5 fails its own acceptance criterion and says so.
- **Streamlit UI** boots clean (HTTP 200) but has never been clicked through.
- **Module 10's own `docker build`** — it adds an embedding pre-bake step Module 9's verified image lacks.
- **Both CI workflows have never run** — they sit in module folders, and GitHub only reads `.github/workflows/` at the repo root.
- **Module 3** was never run.
- **Zero OpenAI or DeepSeek calls.** Provider wiring verified (fails on missing key, not unknown provider); no completion ever made.
- **Module 18's Self-RAG loops** proven by logic (`test_caps.py`), not by provoking a real failure.

---

## 4. 💰 What it costs to run

Based on **252 model calls** — actually counted while running every built module once — at ~1,200 input / ~300 output tokens per call (≈302k in, ≈76k out).

| Model tier | Per full pass | ×10 for debugging & re-runs |
|---|---|---|
| **mini** (≈$0.15 / $0.60 per 1M) | **$0.09** | **$0.91** |
| mid (≈$2.50 / $10.00 per 1M) | $1.51 | $15.12 |

Heaviest single module, the 31-case eval suite (60 calls): **$0.02** per run on a mini model — $0.65 if you ran it daily in CI for a month.

### So: what's the minimum OpenAI credit?

**$5 — their usual minimum top-up — and it's far more than you need.** A full pass of every module costs about **9 cents** on `gpt-4o-mini`. Even allowing 10× for mistakes and re-runs you're under a dollar.

Four things that would change the maths:

1. **Don't use a flagship model.** The mid-tier row is ~17× the mini row for work that's almost all routing and short drafting.
2. **Keep local embeddings.** MiniLM is free and private. Hosted embeddings bill per chunk, and ingestion embeds *every* chunk — that's the one call that scales with your data rather than your usage.
3. **Set a hard spend limit first** (Billing → Limits). This repo contains loops; Module 16's suite is designed to run in CI.
4. **Prices change and mine are unverified.** Check openai.com/api/pricing and recompute — the token counts above are the solid part.

**And the honest version: you don't need OpenAI credit at all.** Groq's free tier runs everything built here, which is how all the evidence above was produced. OpenAI only buys you the simpler structured-output path and genuine provider redundancy (see [`OpenAI.md`](./OpenAI.md)).

---

## 5. 🔑 Keys — which module needs what

| Key | Required by | Notes |
|---|---|---|
| **`GROQ_API_KEY`** | **4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18, 19** | the only one you truly need. Free: console.groq.com |
| **`TAVILY_API_KEY`** | **3, 7, 10, 11, 13, 18** | web search. Free: tavily.com |
| `LANGSMITH_API_KEY` | 6, 10 | **optional** — tracing only, off by default |
| `OPENWEATHER_API_KEY` | 11 | **optional by design** — degrades to Tavily, and that's the tested path |
| `OPENAI_API_KEY` | none | alternative provider. Needs `uv add langchain-openai` |
| `DEEPSEEK_API_KEY` | none | alternative provider. Needs `uv add langchain-deepseek`. **No embeddings API** — pair with local MiniLM |
| `PINECONE_API_KEY` | **20** *(not built)* | index dimension must match embeddings (MiniLM 384 / OpenAI 1536) |
| `NEO4J_URI` / `_USERNAME` / `_PASSWORD` | **22** *(not built)* | Aura free tier; needs `neo4j+s://`, not `bolt://` |
| `HF_TOKEN` | 3 | legacy module only |

Full annotated template: [`.env.example`](./.env.example). Copy it into each module folder as `.env`.

**Embeddings need no key** — Modules 8, 10, 18 use local MiniLM (~90MB download on first use).
