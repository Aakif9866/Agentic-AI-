# Module 21 — Forward Deployed Engineering: Roadmap + Case Study

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready — though this module is mostly *you* writing, not an agent building.

## Goal in one line

Write an **FDE-style case study** of a project you already built, following the real shape: customer problem → scoped spec → eval set → build → deploy → measure.

## Why this module exists

No new LangGraph here. "Forward Deployed Engineer" is a role where you sit with a customer, figure out what they actually need, scope it brutally, build it, deploy it, and **measure whether it helped**. The deliverable is the write-up, because the write-up is the skill.

**This is your portfolio piece.** A recruiter reading one good case study learns more about you than from a repo of 22 folders.

## Scope

Apply this to a project **already in this repo** — Module 10 (the capstone) is the natural choice. **Do not build a separate throwaway project.** The brief is explicit about that.

## File to create

```
fde-case-study.md     in this folder (the brief says /mnt/project-files/... — that path
                      doesn't exist on your machine; keep it in the repo instead)
NOTES.md              your own notes afterwards
```

## The six required sections

| # | Section | What it must contain |
|---|---|---|
| 1 | **Customer problem** | One paragraph, **in a hypothetical user's words, not yours**. What hurts? |
| 2 | **Scoped spec** | What you *will* and *won't* build in v1 — and **why you drew the line there** |
| 3 | **Eval set** | Reuse/extend Module 16. What does "working" mean, **measurably**? |
| 4 | **Build** | Link to the actual PR/commit that implements it |
| 5 | **Deploy** | Link to the actual deployed URL (reuse Module 9/19's deployment) |
| 6 | **Measure** | **Real numbers** from the eval set, before and after this round |

## Acceptance criteria

- [ ] **Every link resolves** to something real in this repo or deployment. No placeholders, no `TODO`.
- [ ] The "measure" section has **actual before/after numbers**, not estimates.

## Pitfalls specific to this module

- **Section 1 is the one everyone gets wrong.** Writing "users need an AI agent" is a solution, not a problem. Write what the person says *before* they know a solution exists: *"I have 200 pages of lecture notes and I waste twenty minutes finding the one paragraph I need."*
- **Section 2 is where the skill shows.** Anyone can list features. Saying "v1 won't support multiple documents, because the eval showed single-doc accuracy was the bottleneck" is the FDE move. Your "won't build" list should be longer than your "will build" list.
- **Section 6 requires Module 16 to exist.** You can't report before/after numbers without an eval harness. **Do Module 16 first** — if you try this module earlier, you'll be forced to invent numbers, which defeats it entirely.
- Don't let an agent write this for you. It'll produce plausible generic prose. The value is that it's *your* reasoning about *your* project.

## Prerequisites (do these first)

- **Module 16** — you need the eval harness for section 6.
- **Module 9 or 19** — you need something actually deployed for section 5.
- Ideally **Module 15** — the harness audit gives you honest material for section 2.

## Further steps & ideas

- Write a second, shorter case study for a project you *didn't* build — scope something a friend or your workplace actually needs. Scoping unfamiliar problems is the real exercise.
- Add a "what I'd do next with 2 more weeks" section — shows judgment about diminishing returns.
- Record a 3-minute screen capture demoing the deployed thing. Case study + demo video is a strong portfolio pair.
- Re-run the eval set a month later and add a third column. Showing you track quality over time is rare and noticed.
