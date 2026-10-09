# Module 19 — Self-Correcting Multi-Agent App (Serverless)

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

A **writer agent** and a **reviewer agent** in a capped loop, behind a FastAPI endpoint, **deployed** to a serverless host.

## Why this module exists

Module 4's loop had one agent revising *itself* — which is a bit like proofreading your own writing. Here the critic is a **separate agent with separate instructions**, which catches more. Then you deploy it, because an agent on your laptop isn't a product.

## Setup

```bash
cd "Module 19 - Project - Self-Correcting Multi-Agent App (Serverless)"
uv init --no-readme --name module19-self-correcting --python 3.12
rm main.py
uv add langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv pydantic fastapi uvicorn
cp "../Module 10 - Project - Build Your Own ChatGPT Agent/.env" .env
```

## Files to create

```
graph.py       writer + reviewer loop
api.py         FastAPI with POST /generate  (reuse Module 9's api.py shape)
Dockerfile     reuse Module 9's — it's already correct
metrics.json   iterations-to-approval for N real runs
NOTES.md       your own notes afterwards
```

## Requirements

- **`writer_agent`** produces a draft.
- **`reviewer_agent`** grades it against **explicit criteria** using structured output — not vibes — and either approves or returns **specific, actionable** feedback.
- Loop capped by **`max_iteration` in state AND `recursion_limit`** on invoke.
- Wrapped in **FastAPI** with a single `POST /generate` endpoint (Module 9's `api.py` shape).
- **Deployed** to a serverless target: DigitalOcean Functions, Render, or AWS Lambda via container image. **Pick whichever you can actually get working** and document which and why.
- **`metrics.json`**: for N real runs, record iterations-to-approval, to show the loop usually converges in ≤3.

## Acceptance criteria

- [ ] The **deployed** endpoint, called with `curl`, returns a real finished draft (not an error) for **3 different prompts**.
- [ ] `metrics.json` holds real data from real runs — paste it.

## Pitfalls specific to this module

- **A reviewer with vague criteria approves everything on pass 1.** Your metrics then show "converges in 1 iteration" and the whole module looks like it works while proving nothing. Give the reviewer a concrete rubric and verify it can say *needs_revision* at least sometimes.
- **The opposite failure: a reviewer that never approves.** Then you always hit the cap. Both failures look like "it ran fine" — which is why `metrics.json` is an acceptance criterion. A healthy distribution has a mix of 1s, 2s, and 3s.
- **Reviewer feedback must reach the writer.** Put it in state and inject it into the writer's prompt. If the writer ignores it, you get the same draft repeatedly — check by logging each draft.
- Structured output for the review → `method="json_mode"`, field names spelled out (`AGENT_RULES.md` #2).
- **Serverless + long loops = timeouts.** A 3-iteration loop with 6 LLM calls can exceed a serverless function's limit (often 10–30s). Either keep the cap low, or deploy as a container (Render/Lambda container) rather than a true function. Document what you hit.
- **Cold starts** make the first `curl` slow or time out. Call it twice before judging.

## Further steps & ideas

- Make the reviewer's criteria a request parameter, so `/generate` can be told what "good" means per call.
- Add a *third* agent: a fact-checker that must also approve. Two independent critics is a different (and stricter) architecture.
- Stream the loop with `stream_mode="updates"` so the client sees "draft 1 → rejected → draft 2 → approved" live.
- Apply Module 15's lesson: replace the reviewer's LLM self-grade with a **deterministic** check where possible (word count, required sections, valid JSON, code that actually runs). Deterministic beats judgment whenever it's available.
- Feed `metrics.json` into Module 16 as a `convergence` eval category.
