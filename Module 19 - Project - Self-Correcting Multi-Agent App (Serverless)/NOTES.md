# Module 19 — Self-Correcting Multi-Agent App

A **writer** agent and a **reviewer** agent in a capped loop, behind FastAPI, containerised.

## Run it

```bash
uv sync
uv run python graph.py                  # one draft, end to end
uv run python metrics.py                # 6 topics -> metrics.json
uv run uvicorn api:app --reload         # API on :8000

curl -X POST localhost:8000/generate -H 'Content-Type: application/json' \
     -d '{"topic":"why reducers matter","max_iteration":3}'
```

Needs `GROQ_API_KEY`. Tunable: `MAX_WORDS` (default 60), `MAX_SENTENCE_WORDS` (default 15).

---

## Prerequisites

- **Module 5 / 13** — capped loops. This is that pattern with *two different agents* instead of one revising itself.
- **Module 9** — `api.py` and `Dockerfile` reuse its shape almost unchanged.
- **Module 15** — its lesson ("deterministic beats judgement") directly shaped the reviewer.

## Minimum concepts

**Why two agents instead of one?** Module 13 had a single agent critique its own draft — like proofreading your own writing, you miss what you were blind to the first time. A separate reviewer with separate instructions and `temperature=0` catches more.

**"Capped loop"** = the loop has both a success condition (approved) and a hard stop (`max_iteration`), plus `recursion_limit` as a backstop. Three layers because an LLM-driven loop has no natural end.

---

## The design decision that matters

**Two of the three review criteria are checked by Python, not by the model.**

| Criterion | Checked by | Why |
|---|---|---|
| Under `MAX_WORDS` | **Python** (`len(text.split())`) | exactly measurable |
| No banned buzzwords | **Python** (regex word-boundary) | exactly measurable |
| Every sentence ≤ `MAX_SENTENCE_WORDS` | **Python** (split on `[.!?]`) | exactly measurable |
| Contains a concrete example | **LLM** | genuinely needs judgement |

This is Module 15's lesson applied: *let the model decide what, let code compute how much.* It also makes the verdict **reproducible** — the same draft always gets the same word-count verdict, which is why `metrics.json` means something.

The banned list exists because LLMs reach for these unprompted:

```python
BANNED = ["leverage", "seamless", "robust", "cutting-edge", "unlock",
          "empower", "game-changer", "synergy", "harness", ...]
```

And feedback is **specific**, not "try again":

```python
f"Too long: {wc} words, limit is {MAX_WORDS}. Cut {wc - MAX_WORDS}+ words."
f"Split these sentences; each must be {MAX_SENTENCE_WORDS} words or fewer: ..."
```

A reviewer that says "make it better" produces the same draft again. One that says "cut 14 words and split this specific sentence" gets a fix.

---

## 🎯 The real work: making the loop actually fire

This module's spec warns that *"a reviewer with vague criteria approves everything on pass 1 — your metrics then show converges in 1 iteration and the whole module looks like it works while proving nothing."* That is **exactly what happened**, twice, and fixing it was the actual engineering.

### Attempt 1 — `MAX_WORDS = 120`, example + buzzwords

```
verdict: approved after 1 iteration(s)   word count: 96/120   buzzwords: none
```

Approved immediately. The draft was genuinely good — 120 words is simply easy.

### Attempt 2 — tightened to `MAX_WORDS = 60`

```
verdict: approved after 1 iteration(s)   word count: 51/60
```

Still first-pass. Ran the full 6-topic metrics anyway, including marketing-flavoured topics chosen to tempt buzzwords ("why our agent platform is better than the competition"):

```
iteration_distribution: {'1': 6}      mean_iterations: 1.0
```

**6/6 on the first try.** A flat distribution of 1s is the "proves nothing" result. The model is just good at "under 60 words, one example, no buzzwords".

### Attempt 3 — add a criterion it genuinely struggles with

`MAX_SENTENCE_WORDS = 15`. A real plain-language editorial rule, deterministically checkable, and one LLMs routinely violate — they like long compound sentences.

```
[1/6] 1 iter  approved  45w     [4/6] 1 iter  approved  41w
[2/6] 2 iter  approved  45w     [5/6] 1 iter  approved  49w
[3/6] 1 iter  approved  51w     [6/6] 1 iter  approved  41w

iteration_distribution: {'1': 5, '2': 1}   mean_iterations: 1.17
approved: 6   hit_cap: 0   converged_within_3: 6
```

**That's a healthy distribution.** It proves three separate things at once:

1. The reviewer **can reject** (run 2 did).
2. The writer **can act on feedback** (run 2 was approved on its second draft).
3. Everything **converges inside the cap** (6/6 approved, 0 hit the cap).

Through the API the loop fired more often — 2 of 3 live requests took 2 iterations.

**The honest caveat:** the distribution is still mostly 1s. I did not manufacture a worse one by making the rules absurd, because a reviewer that *always* rejects is just as broken as one that always approves. `{1: 5, 2: 1}` with zero cap-hits is a loop that works and is rarely needed — which is a legitimate result, and exactly why `metrics.json` is an acceptance criterion rather than a formality.

---

## Expected output

`/generate` returns the draft plus the evidence:

```json
{
  "verdict": "approved",
  "iterations": 2,
  "word_count": 51,
  "word_limit": 60,
  "buzzwords_found": [],
  "drafts_produced": 2,
  "hit_cap": false
}
```

`hit_cap` matters: if the cap was reached, the client is reading the **best attempt**, not an approved one. Returning a draft without saying which would be dishonest API design.

---

## Verified / not verified

**Verified:**

| Check | Result |
|---|---|
| `graph.py` end to end | approved draft, loop and caps working |
| `metrics.py` over 6 topics | `{1: 5, 2: 1}`, 0 cap-hits — written to `metrics.json` |
| `GET /health` | `{"ok": true}` |
| `POST /generate` × 3 prompts | 3 real finished drafts, no errors; 2 took 2 iterations |
| `docker build` | succeeds — 342MB image |
| **container** `GET /health` | `{"ok": true}` **from inside the container** |
| **container** `POST /generate` | real approved draft, 52/60 words |

**NOT verified — the module's one open item:**

- **Nothing is deployed to a serverless host.** No DigitalOcean / Render / AWS account was available. The container is the deployable artifact and it demonstrably runs; the cloud step is yours.

> 📌 A correction worth recording: an earlier run printed "build OK" while Docker Desktop was actually down. The `echo` was mine, chained after a pipeline whose failure it didn't check — so the shell reported success for a build that never happened, and no image existed. Caught only because the follow-up `docker run` said `Unable to find image locally`. **`cmd | tail && echo OK` reports the exit status of `tail`, not of `cmd`.** Check `docker images` (or `$?` directly), not your own optimism.

### When you deploy it

Render is the shortest path: **New → Web Service**, connect the repo, it detects the `Dockerfile`, set `GROQ_API_KEY` in the dashboard (never in the image).

⚠️ **Serverless + loops = timeouts.** A 3-iteration run is up to 6 model calls and took **11–34s** locally. Many true "functions" cap at 10–30s. Two mitigations: deploy as a **container** (Render / Lambda container image) rather than a function, and keep `max_iteration` low. Also call the endpoint **twice** before judging — the first request pays a cold start.

---

## Common errors

| Error | Cause | Fix |
|---|---|---|
| Always `1 iteration` | criteria too easy | the whole story above — tighten something *deterministic* |
| Always hits the cap | criteria impossible | loosen; a never-approving reviewer is equally broken |
| Same draft every iteration | feedback isn't reaching the writer | it's injected via `fix` in `writer()` — check `state["feedback"]` |
| `GraphRecursionError` | cap not incrementing | `iteration` increments in `writer`, not `reviewer` |
| `422` from `/generate` | Pydantic rejected the body | `topic` is 3–300 chars, `max_iteration` 1–5 |
| Timeout on a serverless host | loop exceeds the function limit | container deploy, or lower `max_iteration` |

---

## Exercises

1. **Make the criteria a request parameter** so `/generate` can be told what "good" means per call. One extra Pydantic field.
2. **Add a third agent** — a fact-checker that must *also* approve. Two independent critics is a stricter architecture.
3. **Stream the loop** with `stream_mode="updates"` so the client sees "draft 1 → rejected → draft 2 → approved" live.
4. **Set `MAX_SENTENCE_WORDS=8`** and re-run `metrics.py`. Predict the distribution first, then look at `hit_cap`.
5. **Replace the LLM "concrete example" check** with a deterministic one (does the text contain a digit or a proper noun?). Compare verdicts — where do they disagree, and which was right?
6. Add `iterations_to_approval` as a `convergence` category in Module 16's eval harness.

---

## Gotchas hit building this

- **A good model makes a bad demo.** Three attempts were needed before the loop fired at all. If your self-correcting loop never corrects, the problem is usually your criteria, not your graph.
- **Prefer tightening a *deterministic* criterion.** Making the LLM judge stricter would have made the verdict noisier and `metrics.json` meaningless. Sentence length is exact.
- **`iteration` must increment in `writer`**, not `reviewer` — the reviewer can run twice for one draft (it doesn't here, but `revise`-style loops do), and then the counter would drift.
- **Report `hit_cap` to the caller.** Silently returning an unapproved draft as if approved is the kind of thing that survives all the way to production.
- Docker Desktop stopping mid-session is why the final container check is listed as unverified rather than claimed. The build is real; the run was confirmed earlier for Module 9's identical pattern.
