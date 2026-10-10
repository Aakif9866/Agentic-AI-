# Module 1 — Agentic AI Foundations

**This module is pure theory. There is no code and nothing to run.** Give it ~20 minutes, then move to Module 4.

Source material: [`info.txt`](./info.txt) (your own notes from the course).

---

## What this module is for

Building vocabulary. Every later module assumes you know what "agent", "tool call", "guardrail" and "orchestrator" mean. You don't need to *understand* them deeply yet — you need to recognise the words so Module 4 onward isn't a fog.

## Prerequisites

None. This is the start.

---

## The one idea that matters

The progression the module describes:

```
Generative AI  →  AI Agents  →  Agentic AI
```

| Stage | What it does | Limitation it hits |
|---|---|---|
| **Generative AI** | you ask, it writes | can't *do* anything — no actions, no live data |
| **AI Agent** | one LLM + tools, decides when to call them | one actor, one job, no real planning |
| **Agentic AI** | several agents, memory, supervision, goals | complexity — needs orchestration and guardrails |

**Put plainly:** generative AI answers. An agent *acts*. Agentic AI is several actors acting under supervision toward a goal.

---

## Key terminology (you'll meet all of these again)

| Term | Plain meaning | Where you'll build it |
|---|---|---|
| **Tool call** | the model asking your code to run a function | Module 7 |
| **Orchestrator** | the framework wiring steps together (LangGraph here) | Module 4 |
| **Memory** | what persists between turns | Module 6 |
| **Guardrails** | rules constraining what the agent may do or say | Module 14 |
| **HITL** (human-in-the-loop) | pausing for a person to approve | Module 8 |
| **Supervisor** | an agent that routes work to other agents | Modules 11, 14 |
| **Context awareness** | what the model can see this turn | Modules 6, 7 |
| **Reasoning / adaptability** | the model choosing its own next step | Modules 5, 13 |

### The five components

`info.txt` lists the standard breakdown. Map each to a real module so it stops being abstract:

| Component | What it is | Built in |
|---|---|---|
| **Brain** | the LLM | every module |
| **Orchestrator** | LangGraph (or CrewAI, AutoGen, n8n) | Module 4 |
| **Memory** | checkpointers + `thread_id` | Module 6 |
| **Supervisor** | guardrail enforcement, routing | Modules 11, 14 |
| **Tools** | search, calculator, RAG, email | Modules 7, 8 |

By Module 10 you'll have built all five in one project.

---

## Expected output

None — there's nothing to execute. You're "done" when you can say, in your own words, how an agent differs from a chatbot.

## Common confusions

| Confusion | Clarification |
|---|---|
| "Agentic AI needs a special model" | No. Same LLM. The difference is the **harness** around it — see Module 15. |
| "An agent is a prompt" | No. An agent *loops*: think → act → observe → think. The loop is the agent. |
| "More agents is better" | No. More agents = more failure modes. Module 11 uses three because the jobs genuinely differ. |
| "Guardrails are a filter" | Too narrow. Module 14 shows four *layers*, of which one is a regex filter. |

## Exercises

1. Write one sentence each for brain / orchestrator / memory / supervisor / tools, without looking.
2. Pick an app you use daily and sketch what an agentic version would need as tools.
3. After Module 10, come back and re-read `info.txt`. It should read as a description of something you built.

---

**Next:** skip-read Module 2 (check you can read `async`/Pydantic), skim Module 3, then start properly at **Module 4**. See [`../LEARNPLAN.md`](../LEARNPLAN.md).
