# Module 18 — Advanced RAG I: Corrective RAG & Self-RAG

Module 8's RAG was naive: retrieve, then answer. If retrieval returned junk, the model answered from junk. These two architectures add **grading** so the system can notice its own retrieval was bad and do something about it.

## Run it

```bash
uv sync
uv run python kb.py sample_notes.pdf    # build faiss_db/ (or just run crag.py, it's prebuilt)
uv run python crag.py
uv run python self_rag.py
uv run python test_caps.py              # free: proves both loop caps, no API calls
```

Needs `GROQ_API_KEY` and `TAVILY_API_KEY`. First run downloads ~90MB of embedding weights.

See [`COMPARISON.md`](./COMPARISON.md) for the required side-by-side analysis.

---

## Prerequisites

- **Module 8** — retrieval, chunking, FAISS. `kb.py` is Module 8's `rag_shared.py` plus one `retrieve()` helper.
- **Module 5** — conditional routing and capped loops. Both graphs are those two patterns applied to retrieval.
- Pydantic `Literal` fields (Module 2).

## Minimum concepts

**"Grading"** = a model scoring something on a scale or label instead of writing prose. Here it scores documents (CRAG) or its own answer (Self-RAG). It's a normal LLM call whose output you *branch on*, which is why it must be structured output and not text.

**"Hallucination" in RAG terms** = an answer containing claims the retrieved context doesn't support. Self-RAG's IsSUP check exists precisely to catch that.

**The one-line difference:** CRAG distrusts the **retriever**. Self-RAG distrusts **itself**.

---

## 1. `crag.py` — grade the documents

```
retrieve → grade_docs → CORRECT   : refine → generate            (kb)
                      → AMBIGUOUS : refine + web → generate      (kb+web)
                      → INCORRECT : rewrite → web → generate     (web)
```

### Two thresholds, three outcomes

```python
UPPER, LOWER = 0.7, 0.3
best = max(scores)
decision = "CORRECT" if best >= UPPER else "INCORRECT" if best < LOWER else "AMBIGUOUS"
```

That middle band is the whole point. A binary good/bad decision would force every half-relevant document into one bucket; the `AMBIGUOUS` band lets the graph say "partly useful" and combine sources.

**Real scores from the run:**

| Question | Scores | Decision |
|---|---|---|
| "What does a checkpointer do?" | `[0.3, 0.9, 0.7, 0.0]` | CORRECT |
| "What is a reducer and why is it needed?" | `[0.4, 0.5, 0.0, 0.0]` | AMBIGUOUS |
| "What is the capital of Peru?" | `[0.0, 0.0, 0.0, 0.0]` | INCORRECT |

Three questions, three different branches. That's the graph working.

### One call grades every document

```python
numbered = "\n\n".join(f"[{i}] {d}" for i, d in enumerate(state["docs"]))
out = structured(DocScores, f'...{{"scores": [float, ...]}} with exactly {len(docs)} scores, in order...')
```

Grading each document in its own call would cost `k` calls per question. One batched call returns a score per document and costs one. Still per-document grading — just not per-document *billing*.

The length is defended, because a model may return the wrong number of scores:

```python
scores = (out.scores + [0.0] * len(state["docs"]))[: len(state["docs"])]
```

### Sentence-level refine

```python
'Keep only the sentences that help answer the question. Drop everything else.'
```

Retrieved chunks carry padding — a 400-character chunk might hold one relevant sentence. Refining before generation means the model reads less noise. This is the step most naive RAG skips.

---

## 2. `self_rag.py` — grade your own answer, twice

```
decide_retrieval → direct_answer                          (skip retrieval)
                 → retrieve → grade_relevance → generate | no_answer
generate → is_sup  → supported     → is_use
                   → not_supported → revise   (MAX_RETRIES)
is_use   → useful     → END
         → not_useful → rewrite_query (MAX_REWRITE_TRIES) → retrieve
                      → exhausted    → no_answer
```

### Two caps, deliberately independent

```python
MAX_RETRIES = 2        # IsSUP: how many times we'll re-ground an answer
MAX_REWRITE_TRIES = 2  # IsUSE: how many times we'll re-query
```

These answer **different questions**, so they must not share a counter. "The answer isn't grounded" is fixed by rewriting the *answer*. "The answer isn't useful" is fixed by rewriting the *query*. Sharing one counter would let a grounding failure consume the query budget.

`test_caps.py` proves this with 11 assertions and zero API calls — including that each router ignores the other's counter.

### `no_answer` is the most important node

```python
"I don't know — the document doesn't cover this and I won't guess."
```

The node people skip, and the one that matters most. An agent that says "I don't know" is worth more than one that invents. It's reachable from three places: no relevant documents, grounding retries exhausted, usefulness rewrites exhausted.

---

## Expected output

```
Q: What does a checkpointer do?
   path    : decide_retrieval=True -> retrieve(4 docs) -> grade_relevance=3 -> generate
             -> is_sup=supported -> is_use=useful
   caps    : retries=0/2 rewrites=0/2  source=kb

Q: What is the capital of Peru?
   path    : decide_retrieval=False -> direct_answer
   caps    : retries=0/2 rewrites=0/2  source=parametric
   A: Lima.
```

The `path` line is worth building into any graph with branches — it's how you see *which way it went* instead of guessing from the answer.

---

## 🐛 The bug that nearly invalidated the whole module

First run of `self_rag.py`:

```
Q: What does a checkpointer do?         decide_retrieval=False -> direct_answer
Q: What is a reducer and why is it...   decide_retrieval=False -> direct_answer
Q: What is the capital of Peru?         decide_retrieval=False -> direct_answer
```

**`decide_retrieval` said "no" to everything.** The retrieval path, both graders, both loops and `no_answer` — none of it executed. And the answer to Q2 was:

> *"A reducer is a pure function that takes the current state and an action, and returns a new state..."*

That's a **Redux** reducer. Correct for JavaScript, wrong for LangGraph, and delivered with complete confidence.

**Cause:** my gate asked *"does answering this need looking up a document?"* The model felt it knew these topics, so it said no. It was never told **what the document contains**.

**Fix:** describe the corpus and default to retrieving:

```python
"We hold ONE private document: course notes on LangGraph (state, nodes, edges,
 checkpointers, thread_id, Send, dynamic fan-out, reducers, interrupts).
 Should we search it to answer this question?
 - true if the question could plausibly be answered by that document, even partly.
 - false ONLY for small talk or topics clearly outside that subject."
```

**Why it's the module's best lesson:** nothing errored. Three questions, three fluent answers, exit code 0. The only clue was that an answer was *subtly about the wrong framework*. A retrieval gate that's too eager to skip turns your RAG system into a plain chatbot **silently** — and if you'd only tested with the Peru question, it would have looked perfect.

**Generalise it:** a router that decides *whether* to use your data must be told what your data is.

---

## Common errors

| Error | Cause | Fix |
|---|---|---|
| Everything lands `AMBIGUOUS` | thresholds too tight | widen; `0.7/0.3` worked here |
| `GraphRecursionError` | a loop didn't stop | both caps + `recursion_limit=25`; run `test_caps.py` |
| `scores` length ≠ docs length | model returned the wrong count | already padded/truncated in `grade_docs` |
| Grader returns prose, not a label | missing `method="json_mode"` | `AGENT_RULES.md` #2 — all six graders need it |
| `retrieve()` returns `[]` | no `faiss_db/` | `uv run python kb.py sample_notes.pdf` |
| Self-RAG never retrieves | the bug above | describe the corpus in the gate prompt |
| Answers cite no pages | refine dropped the `[page N]` prefix | keep it in the chunk text |

---

## Exercises

1. **Set `UPPER = 0.4`** and re-run CRAG. The reducer question flips AMBIGUOUS → CORRECT and stops consulting the web. Same code, different behaviour — thresholds *are* policy.
2. **Force a loop.** Hard-code `check_sup` to return `not_supported` and watch `revise` run exactly `MAX_RETRIES` times, then land on `no_answer`. The caps have been proven logically but never exercised end-to-end.
3. **Break the gate back** to the vague prompt and watch Self-RAG silently become a chatbot. Best possible demonstration of the bug above.
4. **Add CRAG's web fallback to Self-RAG's `no_answer`** path. That's the hybrid `COMPARISON.md` recommends.
5. **Swap in a PDF you know well.** The behaviour differences get much more obvious on content where you can judge the answers yourself.
6. Add a `rag_quality` category to Module 16's eval set using these six graders as the thing under test.

---

## Gotchas hit building this

- **Six graders means six `json_mode` calls**, so they're wrapped in one `structured()` helper per file rather than repeated. With this many, the boilerplate would dominate.
- **Pick the unanswerable question from a genuinely different domain.** "Capital of Peru" works; a harder LangGraph question would be partly covered and prove nothing.
- **`decide_retrieval` costs a call on every query** to save retrieval sometimes. On an easy question Self-RAG paid 3 grader calls where CRAG paid 1. Self-correction isn't free.
- **The caps were unexercised** by real runs, because on a healthy document everything passes first time. Rather than claim they work, `test_caps.py` proves the routing logic deterministically for free. **Prefer a free deterministic test over an expensive probabilistic one** whenever the logic is pure.
