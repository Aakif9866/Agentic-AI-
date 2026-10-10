# CRAG vs Self-RAG — same document, same three questions

Both graphs ran against the same `sample_notes.pdf` (5 chunks of LangGraph course notes). Real output, not reconstructed.

## The one-line difference

| | What it grades | When it corrects |
|---|---|---|
| **CRAG** | the **retrieved documents** | *before* answering — if the docs are weak, go get better material |
| **Self-RAG** | its **own answer**, twice | *after* answering — is it grounded, and is it useful? |

CRAG distrusts the retriever. Self-RAG distrusts itself.

---

## Question 1 — "What does a checkpointer do?" (clearly in the document)

| | Path | Source |
|---|---|---|
| **CRAG** | `retrieve → grade [0.3, 0.9, 0.7, 0.0] → CORRECT → refine → generate` | `kb` |
| **Self-RAG** | `decide_retrieval=True → retrieve(4) → grade_relevance=3 → generate → is_sup=supported → is_use=useful` | `kb` |

Both answered correctly from the document. **Same destination, different reasoning:** CRAG scored a document at 0.9 and trusted it. Self-RAG wrote an answer first and then checked it was grounded and useful.

**Cost note:** Self-RAG paid two extra grader calls here to confirm an answer that was already fine. CRAG paid one. On easy questions, CRAG is cheaper.

---

## Question 2 — "What is a reducer and why is it needed?" (partially covered)

| | Path | Source |
|---|---|---|
| **CRAG** | `grade [0.4, 0.5, 0.0, 0.0] → **AMBIGUOUS** → refine + web → generate` | `kb+web` |
| **Self-RAG** | `retrieve(4) → grade_relevance=2 → generate → supported → useful` | `kb` |

**This is where they genuinely diverge.** The document mentions reducers only in passing ("a reducer such as `operator.add` is required to merge the parallel writes"). Best document score was **0.5** — above `LOWER=0.3`, below `UPPER=0.7`.

- **CRAG saw the ambiguity and hedged**, pulling in web results alongside the document. The answer is broader but partly generic ("a reducer is a component that combines something larger into something smaller").
- **Self-RAG never noticed the thinness.** Two chunks were judged relevant, the answer it wrote *was* supported by them, so both graders passed. The result is narrower but more precise, and it cited `page 0`.

**Which is better depends on what you want.** For "answer strictly from my document", Self-RAG won. For "give me the fullest answer available", CRAG won. Neither is wrong; they optimise different things.

---

## Question 3 — "What is the capital of Peru?" (not in the document)

| | Path | Source | Answer |
|---|---|---|---|
| **CRAG** | `grade [0.0, 0.0, 0.0, 0.0] → **INCORRECT** → rewrite → web → generate` | `web` | "Lima." |
| **Self-RAG** | `decide_retrieval=**False** → direct_answer` | `parametric` | "Lima." |

**Same answer, and the two architectures never even met.**

- **CRAG had to find out the hard way.** It retrieved, scored everything 0.0, concluded the knowledge base was wrong for this question, rewrote the query to "What is the capital city of Peru?", and searched the web. Four steps to learn something it could have guessed.
- **Self-RAG asked first.** Its `decide_retrieval` gate decided no private document was needed and answered directly — one step, no retrieval, no web call.

**Why the difference makes sense architecturally:** CRAG's graph *begins* with `retrieve`. It has no mechanism for skipping retrieval, so its only correction route is "retrieve, discover it's useless, go elsewhere." Self-RAG's graph begins with a **decision**, so it can bypass retrieval entirely. That extra gate is Self-RAG's structural advantage, and it costs one grader call on every single query to get it.

**Crucially, neither hallucinated.** CRAG grounded in a web result; Self-RAG answered from parametric knowledge and would have said "I don't know" via `no_answer` had `grade_relevance` returned nothing. Verified by hand: "Lima" is correct.

---

## Summary table

| | CRAG | Self-RAG |
|---|---|---|
| Can skip retrieval entirely | ❌ always retrieves first | ✅ `decide_retrieval` gate |
| Detects weak/thin documents | ✅ float scores + two thresholds | ⚠️ only if nothing is relevant |
| Checks its own answer is grounded | ❌ | ✅ IsSUP, with a retry loop |
| Checks its own answer is useful | ❌ | ✅ IsUSE, with a rewrite loop |
| Falls back to the web | ✅ built in | ❌ not in this implementation |
| Grader calls on an easy question | 1 | 3 |
| Loops | none — single forward pass | two, independently capped |
| Fails safe by | web fallback | `no_answer` |

## What I'd actually build

Combine them: Self-RAG's `decide_retrieval` gate at the front (skip retrieval when it's pointless), CRAG's document scoring with a web fallback in the middle (fix bad retrieval), and Self-RAG's IsSUP check at the end (catch ungrounded claims). Drop IsUSE unless you've seen it fire — it cost a call per query here and never once disagreed.

That's roughly what production RAG converges on, and it's Module 20's starting point.
