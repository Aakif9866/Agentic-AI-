# Module 16 — AI Agent Evaluation

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

A real eval harness — **25+ test cases** across five dimensions — that runs in CI and **fails the build** when quality drops.

## Why this module exists

Up to now, "does it work?" meant "I ran it once and the output looked fine." That doesn't survive a model upgrade, a prompt tweak, or a refactor. An eval set turns "seems fine" into a number you can watch over time.

**This is the single most useful module in the course for real work.** It's also the one that makes every *later* change safe to make.

## Scope

Evaluate **Module 10** or **Module 14** — pick one and say which at the top of `run_evals.py`.

## Setup

```bash
cd "Module 16 - AI Agent Evaluation"
uv init --no-readme --name module16-evals --python 3.12
rm main.py
uv add langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv pydantic pandas
cp "../Module 10 - Project - Build Your Own ChatGPT Agent/.env" .env
```

## Files to create

```
evals/dataset.jsonl      >= 25 test cases
evals/run_evals.py       the runner + scorecard
.github/workflows/evals.yml   CI gate
NOTES.md                 your own notes afterwards
```

## The five dimensions

| Dimension | Question | How to check |
|---|---|---|
| **Final answer** | Is the answer right? | substring match, or LLM judge for fuzzy cases |
| **Tool selection** | Did it pick the right tool? | compare against `expect_tools` |
| **Trajectory** | Did it take the right *path*? | ordered tool list, step count |
| **Latency** | Was it fast enough? | wall clock vs `max_latency_s` |
| **Safety** | Did it refuse what it should? | expected-refusal cases |

## Requirements

- **`evals/dataset.jsonl`** — ≥25 rows, each with:
  - `question`
  - `expect_any` (acceptable answer substrings) **or** `expect_judge_criteria` for fuzzy cases
  - `expect_tools` (ordered list)
  - `max_latency_s`
  - `category` — one of `correctness` / `tool_use` / `safety` / `latency`
- **`evals/run_evals.py`** — runs every case, records `answer`, `tools_called` (ordered), `latency`; computes pass/fail per dimension; prints a scorecard as a **pandas DataFrame grouped by category**.
- **At least one case per category uses LLM-as-judge** with structured output (`VERDICT`, `SCORE`, `REASON`). Not substring matching for everything.
- **`.github/workflows/evals.yml`** — runs on every push, **fails the build** if overall pass rate drops below your threshold (e.g. 80%).

## Acceptance criteria

- [ ] `uv run python evals/run_evals.py` prints a real scorecard with real pass/fail counts — paste the actual output.
- [ ] **Intentionally break one tool's docstring** (make it vague), re-run, and show the `tool_use` pass rate **drop**. This proves the harness catches regressions rather than just printing green.

## Pitfalls specific to this module

- **25 real evals take real time and real API calls.** At ~3–5s each that's a 2-minute run, and CI will pay it on every push. Consider a `--quick` flag that runs a subset locally, full set in CI.
- **LLM judges are flaky if under-specified.** Give the judge explicit criteria and a scale, request structured output (`method="json_mode"`, field names spelled out — `AGENT_RULES.md` #2), and set `temperature=0`.
- **Latency tests are the flakiest thing you'll own.** Groq's free tier varies wildly; a test that passes at 2s locally fails at 6s on a busy CI runner. Set generous thresholds and treat latency as informational, not a hard gate.
- **Don't let the eval import start a server.** Import the graph (`from backend import agent`) directly — that's exactly why Module 9 separated `backend.py` from `api.py`.
- Writing 25 cases is the boring part and the whole value. Don't let the agent generate 25 near-identical ones — mix easy, hard, adversarial, and out-of-scope.

## Further steps & ideas

- Reuse Module 14's 5 adversarial inputs as your `safety` category — they're already written.
- Track scores over time: append each run's summary to `evals/history.jsonl` and chart pass rate per commit.
- Add a `cost` column (tokens × price) and watch it alongside quality — the two trade off.
- Run the same eval set against two different models (`gpt-oss-120b` vs `qwen3.8-27b`) and compare scorecards. That's a genuinely useful engineering result.
- Once this exists, every later module gets safer: change something, run evals, see if you broke anything.
