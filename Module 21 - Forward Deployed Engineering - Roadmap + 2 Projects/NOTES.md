# Module 21 — Forward Deployed Engineering

**No new LangGraph here, and nothing to run.** The deliverable is a written case study: [`fde-case-study.md`](./fde-case-study.md).

## What an FDE actually does

Sits with a customer, works out what they *actually* need, scopes it brutally, builds it, deploys it, and **measures whether it helped**. The write-up is the deliverable because the write-up is the skill — it's the artefact that proves you can do the thinking, not just the typing.

**This is your portfolio piece.** A recruiter reading one good case study learns more about you than from 22 folders of code.

## Prerequisites — genuinely required, not nice-to-have

| Needed | Why | Status |
|---|---|---|
| **Module 16** (evals) | §6 demands real before/after numbers. Without an eval set you *must* invent them, which defeats the whole exercise. | ✅ built |
| **Module 14** (the subject) | you need something real to write about | ✅ built |
| Module 9 or 19 (deploy) | §5 wants a live URL | ⚠️ container verified, nothing hosted |

**Do not attempt this module before Module 16.** That's not a suggestion — §6 is unwriteable without it.

---

## The six sections, and what each is really testing

| # | Section | What it's testing |
|---|---|---|
| 1 | Customer problem | can you describe a problem **without** describing your solution? |
| 2 | Scoped spec | can you say **no**, and justify where the line sits? |
| 3 | Eval set | can you define "working" as a **number**? |
| 4 | Build | does the code exist? (link a real commit) |
| 5 | Deploy | is it **in front of a user**? |
| 6 | Measure | did it actually **help**? |

### Section 1 is the one everybody gets wrong

Writing *"users need an AI agent for support"* is a **solution**, not a problem. Section 1 must be in the customer's words, from before they knew a solution existed.

What I wrote instead, and why it works: the customer complains that *"the annoying part isn't answering them, it's reading all of them"*, mentions a previous chatbot that *"confidently told a customer their refund was processed when it wasn't"*, and that someone *"got it to print its own instructions back"*. Three concrete pains, each of which §2 maps to a specific capability. **The problem statement has to be specific enough that the scope follows from it.**

### Section 2 is where the skill shows

My "won't build" list is **longer** than the "will build" list. That's the point. The hardest exclusion was RAG over the customer's documentation — Module 8 makes it easy and it sounds impressive. Excluded because *the complaint was triage, not answer quality*, and adding retrieval would add a hallucination surface to solve a problem nobody reported.

**The line I drew:** v1 does everything up to the moment of irreversible action, and nothing past it. It doesn't send email, even though it can. The customer's binding constraint is **trust**, not capability — and you can't buy trust back with features.

That isn't the obvious scope. The obvious scope is "an agent that handles tickets end to end."

### Section 6 is where the honesty lives

Real numbers from two full eval runs:

| Category | Before | After |
|---|---|---|
| `safety` | 86.0% | **100.0%** |
| **Overall** | **88.6%** | **99.1%** |

Three things I made myself write down:

1. **The +10.5 points came from fixing two regexes**, not from a better model or prompt. The number moved because *measurement existed*. That's the strongest possible argument for building the eval set first.
2. **`correctness` is 94.4%, not 100%** — one case still fails and I left it failing. A suite at 100% usually stopped trying.
3. **Two of the seven original failures were bugs in the eval**, not the agent. An eval suite is software too.

---

## ⚠️ Section 5 does not pass its acceptance criterion

The criterion is *"every link resolves to something real — no placeholders"*, and **there is no deployed URL**. Nothing is hosted; no account exists.

I wrote that plainly in the document rather than linking a plausible-looking `onrender.com` address. **An unmet criterion stated clearly is worth more than a met criterion that's fictional** — in a real FDE engagement, an invented deployment link is the kind of thing that destroys your credibility permanently.

The remaining work is roughly 30 minutes: Render → New Web Service → point at the repo → set `GROQ_API_KEY`. Then update §5 and the appendix table.

---

## Common mistakes

| Mistake | Why it fails |
|---|---|
| Section 1 describes the solution | the scope then has nothing to follow from |
| "Won't build" list is short or missing | scoping *is* the exercise |
| Section 6 uses estimates | then you're writing marketing, not a case study |
| Placeholder links | one dead link makes a reader doubt all of it |
| Letting an agent write it | it'll produce plausible generic prose; the value is *your* reasoning about *your* project |
| Picking the biggest project | I picked Module 14 over the Module 10 capstone precisely because 14 has eval numbers and 10 doesn't |

---

## Exercises

1. **Write section 2 for a project you didn't build** — something a friend or your workplace actually needs. Scoping an unfamiliar problem is the real exercise.
2. **Deploy the thing and fill in §5.** The single highest-value hour left in this module.
3. **Re-run the evals in a month** and add a third column. Tracking quality over time is rare and gets noticed.
4. **Record a 3-minute demo video.** Case study + demo is a strong portfolio pair.
5. **Give §1 to someone who hasn't seen the project** and ask what they think should be built. If their answer differs wildly from §2, §1 isn't specific enough.

---

## Gotchas

- **Verify your links before claiming them.** I checked every commit SHA with `git log -1 <sha>` and counted the eval cases from `dataset.jsonl` (31; 10/11/6/4; 4 judged) rather than quoting from memory. One wrong number undermines the rest.
- **The appendix table is doing real work.** Listing each section's evidence status — including the ❌ — is what makes the ✅ rows believable.
- **Prerequisites are not optional here.** Had I attempted this before Module 16, §6 would have been estimates, and the document's one genuinely valuable section would have been its weakest.
