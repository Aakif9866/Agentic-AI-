# Module 15 — Harness & Loop Engineering

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

Audit a project you already built against the 8-row harness table, then **fix the weakest row in real code**.

## Why this module exists

This is the only module with almost no new API to learn. It's a thinking module: you look at something you built and ask "what would break this in production?" The 8 rows are a checklist that makes that question answerable instead of vague.

**This is also the highest-value module for interviews.** Anyone can wire a graph. Being able to say "our verification row was weak because the loop trusted the LLM's own self-grading, so I replaced it with a deterministic check" is the senior-engineer version of the same skill.

## Scope — pick one

Audit **Module 10** (the capstone) or **Module 14** (the guarded supervisor). Say which at the top of your review. Module 10 is the better choice if you haven't built 14 yet.

## Files to create

```
HARNESS_REVIEW.md   the audit (lives here, or in the audited project — say which)
<the actual fix>    real code changes in the audited project
NOTES.md            your own notes afterwards
```

## The 8 rows

| Row | The question it answers |
|---|---|
| **Context** | What does the model see each turn, and is it the *right* stuff? |
| **Tools** | Can it do what it needs to? Are docstrings clear enough to pick correctly? |
| **Control flow** | Who decides what runs next — you, or the model? |
| **Verification** | How do you know the output is right? Who checks? |
| **Permissions** | What can it do without asking? What must a human approve? |
| **State / memory** | What's remembered, where, for how long? |
| **Budgets** | What stops it burning tokens/money/time forever? |
| **Observability** | When it misbehaves, can you find out why? |

## Requirements

- **`HARNESS_REVIEW.md`**: for each of the 8 rows, write what the project does **well** and **one concrete weakness**, each with a real **`file:line`** reference. Not "observability could be better" — `backend.py:31, no token usage is logged anywhere`.
- Pick the **weakest** row and **actually fix it in code**.
- **Before/after comparison**: run the same test input before and after, show both outputs, and write 2–3 sentences on what changed and why it's better.

## Acceptance criteria

- [ ] The fix is real, runnable code with a diff you can show — not prose describing a hypothetical improvement.
- [ ] Every `file:line` reference points at real code in this repo. No invented examples.

## Starting points for Module 10 (observations already available)

Module 10's own `NOTES.md` admits several weaknesses — these are honest starting candidates:

- **Budgets** — nothing caps tokens, cost, or tool-call count per thread. Probably the weakest row.
- **Verification** — the agent's answers are never checked by anything. No judge, no deterministic assertion.
- **State/memory** — SQLite doesn't persist on a free host; no thread deletion exists.
- **Observability** — LangSmith is wired but off by default; no token/cost logging locally.
- **Permissions** — `send_email` requires approval, but `tavily_search` and `calculator` run freely. Is that the line you want?

Pick one, don't fix all five.

## Pitfalls specific to this module

- **The temptation is to write prose and call it done.** The acceptance criteria exist specifically to stop that. If there's no diff, the module isn't finished.
- `file:line` references rot as you edit. Write the review *just before* making the fix, and note the commit SHA at the top so the references stay meaningful.
- Picking an easy row instead of the weakest row defeats the exercise. The weakest one is usually the least fun to fix.

## Further steps & ideas

- Implement a real token budget: count usage per thread in state, refuse politely past a cap, and surface the remaining budget in the API response.
- Swap one LLM self-grade for a deterministic check (Module 5's lesson): e.g. in Module 19's writer/reviewer loop, actually *run* generated code rather than asking the model if it looks correct.
- Re-run this audit after Module 16's evals exist — "verification" will look very different once you have a scorecard.
- Keep `HARNESS_REVIEW.md` as a living document and re-audit after Module 21. The diff between the two audits is a great portfolio artifact.
