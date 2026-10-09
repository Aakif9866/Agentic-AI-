# LEARNPLAN — how to actually learn this course

Read this before anything else. It is not about agents; it's about how to turn the code in this repo into understanding that stays in your head.

---

## Start here: an honest description of where you are

You have ten modules of working code. **You did not write most of it, and you don't yet understand it.** That is completely normal and it is not a problem — as long as you know it's the situation.

There's a trap here that catches almost everyone. Working code *feels* like knowledge. You can scroll through `04_parallel.py`, think "yeah, that makes sense," and close the file having learned nothing. Recognising a thing is not the same as being able to build it.

So the goal of this document is one specific conversion:

> **code that runs on your machine → ideas you can rebuild from scratch**

There is a method for that. It isn't reading. It's **running, breaking, and predicting.**

---

## Part 1: The method — six steps per file

Do this for **one file at a time**. It takes 20–40 minutes per file. Don't batch it.

### Step 1 — Run it before you read it (2 min)

```bash
cd "Module 4 - LangGraph Fundamentals/project"
uv run python 01_temperature.py
```

Look at the output. Just the output. Don't open the file yet.

**Ask yourself:** what did this program *do*? Not how — what. Say it in one sentence out loud.

### Step 2 — Guess the shape (3 min)

Before reading the code, guess: how many steps did that take? What information got passed between them? If you had to write this, what would you need?

Being wrong here is *good*. A wrong guess makes the right answer stick; reading cold doesn't.

### Step 3 — Read the code, top to bottom, once (5 min)

Now open it. Read it once, straight through. **Do not stop at things you don't understand** — note them and keep going. You're getting the map, not the detail.

### Step 4 — Read the NOTES.md section for that file (5 min)

Every module has a `NOTES.md` explaining each file in plain English. Read **only** the section for the file you just read. See Part 2 below for how to read it properly.

### Step 5 — Break it on purpose (10 min) ← **this is the step that teaches**

Change one thing. **Predict what will happen. Write the prediction down.** Then run it.

Being surprised is the entire point. Surprise means your mental model was wrong, and that's the moment it gets fixed. Part 5 of this doc has specific experiments for every module.

### Step 6 — Explain it with the file closed (5 min)

Close the file. Explain out loud, to nobody, what it does and why. If you stall mid-sentence, that's your gap — reopen the file and look at exactly that.

Talking to yourself feels stupid and works better than re-reading. Re-reading creates the *feeling* of understanding; explaining tests it.

---

## Part 2: How to read a NOTES.md (you asked this specifically)

Each `NOTES.md` has three kinds of content, and they deserve different treatment.

| Section type | How to read it |
|---|---|
| **"The idea"** / concept paragraphs | Read **after** you've run the file. Before running, it's abstract words; after, it's an explanation of something you just watched happen. |
| **Code snippets** | Compare them to the real file. The notes show the *important 5 lines*; the file has all 40. Knowing which 5 matter is most of the skill. |
| **"Gotchas we hit"** (at the end) | **The most valuable part of the whole repo.** |

### Why the gotchas matter most

Those sections are real failures from actually building this — models that refused to call tools, a model name that 404'd, whitespace that wrecked retrieval. They're where learning actually lives, because:

1. They're what you'll hit yourself.
2. They teach *debugging*, which is the real job. Writing agent code is easy; figuring out why an agent did something stupid is the hard part.
3. They tell you what's **your bug** vs **the model being weird** — a distinction that takes people months to develop.

**Read the gotchas twice: once now, once when you're stuck.** The second read is when they'll make sense.

### Read NOTES.md twice, at different times

- **First pass — right after running the file.** You'll understand maybe 60%.
- **Second pass — a day later, before the next module.** The remaining 40% lands, because your brain has had time, and because the next module builds on it.

Don't try to get 100% on the first pass. That's not how this works.

### Then write your own notes

For each module, add a `MYNOTES.md` next to `NOTES.md` with just three things:

```markdown
## What this module is for (one sentence, my words)

## The thing I got wrong at first

## A question I still have
```

Three lines. Not an essay. The "thing I got wrong" entries become the most valuable file in your repo — they're your personal gotcha list.

---

## Part 3: The order to learn in — and what each module is *really* about

**Learn in number order.** Each one genuinely depends on the one before. Don't skip ahead; Module 8 won't make sense without Module 7's tool loop.

| Module | Status | In one sentence, the real idea |
|---|---|---|
| **1** | notes only | What an "agent" even means. Read it, don't overthink it. |
| **2** | notebooks | **Don't skip.** `async` and Pydantic appear everywhere from Module 7 on. |
| **3** | built earlier | Agents the old way (LangChain). Useful contrast for why LangGraph exists. |
| **4** | ✅ built | **State, nodes, edges.** The three pieces everything else is made of. |
| **5** | ✅ built | Routing and loops — `Send`, `Command`, capped retries. |
| **6** | ✅ built | **Memory.** A checkpointer + `thread_id` is how ChatGPT has a sidebar. |
| **7** | ✅ built | **Tools.** The `chat → tools → chat` loop. Arguably the most important module. |
| **8** | ✅ built | Answering from *your* documents (RAG) + pausing for a human (HITL). |
| **9** | ✅ built | Getting it off your laptop — FastAPI, Docker. |
| **10** | ✅ built | Everything at once. The capstone. |
| **11–22** | 📋 planned | Each folder has a `README.md` with the build plan. Not built yet, on purpose. |

### If you only have limited time, these four matter most

**4 → 6 → 7 → 8.** State, memory, tools, RAG. Everything else in the entire field is a variation on those four. Module 10 is just those four stacked together.

---

## Part 4: A realistic schedule

Honest expectation setting: you can **build** ten modules in a night. You cannot **learn** ten modules in a night. Those are different activities and both are fine.

The building is done. Now budget for the learning:

| Pace | Plan | Finish Modules 4–10 in |
|---|---|---|
| **Comfortable** | one *file* per day | ~4 weeks |
| **Focused** | one *module* per day | ~1 week |
| **Intense** | two modules per day | ~4 days (expect to re-read later) |

A module = 3–6 files. "One module per day" means roughly 2–3 focused hours. **Going slower than this is not falling behind** — someone who truly understands Modules 4–8 is far ahead of someone who has skimmed all 22.

### One rule about pacing

**Never start a new module on the same day you felt lost in the previous one.** Confusion compounds in this material faster than almost anything else, because every module literally imports the last one's ideas. A day re-reading Module 7 is worth more than a day skimming Module 9.

---

## Part 5: Break-it experiments (do these — they're the real lessons)

For each one: **predict first, write the prediction down, then run.**

### Module 4 — state, nodes, edges

| Break this | Prediction to make |
|---|---|
| In `04_parallel.py`, change `scores: Annotated[list[int], operator.add]` to plain `list[int]` | Does it crash? What's the error called? |
| In `01_temperature.py`, make `convert` return `{"celsius": 0}` instead of `fahrenheit` | What does `label` see? |
| In `06_iterative_loop.py`, set `max_iteration` to 1 | Where does it stop, and does it say it's "approved"? |

The first one produces `InvalidUpdateError`. **That error is the single most important thing in Module 4** — it's LangGraph refusing to silently lose data when two nodes write at once.

### Module 5 — routing and dynamic work

| Break this | Prediction |
|---|---|
| In `01_dynamic_fanout_send.py`, pass 1 topic, then 10 | Does anything about the graph need to change? (No — that's the whole point of `Send`.) |
| In `03_multiway_router.py`, make the router return `"urgent"` (not in the map) | What happens when a router returns an unmapped value? |
| In `05_capped_refinement_loop.py`, set `max_iteration=1000` and `recursion_limit=10` | Which cap trips first, and what's the error? |

### Module 6 — memory

| Break this | Prediction |
|---|---|
| In `02_persistent_chatbot.py`, remove `checkpointer=InMemorySaver()` | Does it error, or just forget? |
| Use the *same* `thread_id` for both questions in `01_basic_chatbot.py` | Does it remember now? (No — and understanding *why not* is the lesson.) |
| Delete `chatbot.db`, run `04` twice | Where does memory actually live? |

### Module 7 — tools

| Break this | Prediction |
|---|---|
| Change `calculator`'s docstring to `"""Does stuff."""` | Will the model still pick it? |
| Remove the `try/except` in a tool and feed it `"1/0"` | Does the graph recover or die? |
| In `04_trim_long_history.py`, set `MAX_MESSAGES = 2` | Does the bot get dumber? Watch it lose track. |

The docstring one is the big one. **Tool docstrings are prompts.** Nothing teaches that faster than watching a vague docstring make the agent stop using a working tool.

### Module 8 — RAG and human approval

| Break this | Prediction |
|---|---|
| In `rag_shared.py`, delete the whitespace-cleanup loop and re-ingest | Does retrieval get worse? (It did for us — badly.) |
| Set `chunk_size=4000` | Does search get more or less precise, and why? |
| In `03_hitl_basic.py`, resume with `"no"` instead of `"yes"` | Does the LLM even get called? |
| Put a `print("SIDE EFFECT")` *before* the `interrupt()` in `04` | How many times does it print across pause+resume? |

That last one teaches the gotcha that bites everyone: **the node re-runs from its start on resume.**

### Module 9 / 10 — deployment and the capstone

| Break this | Prediction |
|---|---|
| Ask Module 10 to send an email via `/chat` and watch the response | Why is the stream *empty*? |
| Call `/chat` twice with different `thread_id`s, then `/threads` | Where did those come from? |
| Remove `GROQ_API_KEY` from `.env` and start the API | Does it fail at startup or at first request? |

---

## Part 6: When you're stuck

### The first four things to check, in order

1. **Is it one of the known gotchas?** Open `AGENT_RULES.md` → "Hard-won pitfalls". Half of all errors you'll hit are already listed there with the fix.
2. **Read the *last* line of the traceback first,** not the first. Python puts the actual error at the bottom.
3. **Is it your bug or the model being weird?** Run it again. Code bugs fail identically every time; model weirdness varies between runs. This one distinction will save you hours.
4. **Did you change one thing or three?** If three, undo two.

### Errors you will definitely see, and what they mean

| Error | What it actually means |
|---|---|
| `InvalidUpdateError` | Two nodes wrote the same key at once; you need a reducer (`Annotated[list, operator.add]`). |
| `GraphRecursionError` | A loop didn't stop. Your `max_iteration` logic is wrong or missing. |
| `model ... does not exist` / `decommissioned` | Groq retired the model. See `AGENT_RULES.md` #1. |
| `Tool choice is required, but model did not call a tool` | `with_structured_output` needs `method="json_mode"`. `AGENT_RULES.md` #2. |
| `must contain the word 'json'` | You used `json_mode` without the word "json" in the prompt. |
| `path segment contains separator ':'` | A folder name has a colon in it. Never use `:` in folder names here. |
| `ImportError: ... sentence_transformers` | `uv add sentence-transformers`. |
| Imports fail but the file looks fine | You're on the wrong Python. Use `uv run python x.py`, not bare `python x.py`. |

### Asking for help well

Bad: *"my agent doesn't work"*. Good: *"I expected X, I got Y, here's the last 5 lines of the traceback, here's the one thing I changed."* The second version usually answers itself as you type it.

---

## Part 7: How to use Claude Code without letting it do your learning

You'll build Modules 11–22 with an agent's help. That's fine and realistic — but there's a sharp line between **help** and **replacement**.

### Do this

- **One module per session.** Paste `AGENT_RULES.md` + that module's `README.md`. Nothing more.
- **Run it yourself** after it builds. Don't take "it works" on trust — the acceptance criteria in each README exist for exactly this.
- **Ask it to explain its own code**, line by line, on anything you don't follow. This is where an agent genuinely beats a tutorial: it will answer "why this line?" forty times without getting bored.
- **Ask for the reasoning, not just the fix:** "why did that fail?" rather than "fix it."
- **Make it justify choices:** "why a reducer here?", "what breaks without this?"

### Don't do this

- ❌ Paste all twelve module specs at once. Failures tangle together and you'll burn credits debugging a knot instead of a bug.
- ❌ Accept code you can't read. Ask for it simpler. Simpler-but-understood beats clever-but-opaque, always.
- ❌ Let it build the **break-it experiments** for you. Those are yours. That's where the learning is.
- ❌ Skip running things because the agent says they work.

### The honest test

After a module is built, ask yourself: **could I rebuild the core of this from a blank file, with docs but no agent?** If no, you have code, not knowledge. Go back to Part 1 Step 5 and break things until the answer is yes.

---

## Part 8: Self-check — can you answer these without looking?

Try these after Modules 4–8. If you can answer all nine in your own words, you genuinely know this material.

1. What are the three pieces of every LangGraph app?
2. Why does a node return only the keys it changed, instead of the whole state?
3. What is a reducer, and when do you *need* one?
4. What exactly does `thread_id` do?
5. What's the difference between `InMemorySaver` and `SqliteSaver` — and when does it matter?
6. How does the model decide which tool to call?
7. Why must a tool return its errors instead of raising them?
8. Why is RAG a *tool* rather than a step that always runs?
9. Why does `interrupt()` require a checkpointer?

**If you're stuck on one**, the answer is in that module's `NOTES.md` — but try to answer first. Retrieving an answer badly teaches more than reading a correct one.

---

## Part 9: Four traps, specifically

1. **Reading instead of running.** Reading code feels productive and teaches very little. If you've read for 30 minutes without running anything, stop and run something.
2. **Moving on while confused.** This material compounds. Confusion in Module 6 becomes helplessness in Module 10.
3. **Collecting instead of understanding.** Twenty-two folders of code you've never run is worth less than four modules you can rebuild.
4. **Thinking confusion means you're not smart enough.** This stack genuinely changes every few months — the course brief itself names three models that are already dead. Everyone is confused here. The ones who get good are the ones who break things and read errors, not the ones who find it easy.

---

## Part 10: Your next 90 minutes

Don't plan. Just do this:

```bash
cd "Module 4 - LangGraph Fundamentals/project"
uv run python 01_temperature.py
```

1. Look at the output. Say what it did, out loud. **(2 min)**
2. Open `01_temperature.py`. Read it once, start to finish. **(5 min)**
3. Open `Module 4 - LangGraph Fundamentals/NOTES.md`, read **only** section 1. **(5 min)**
4. Now break it: make `convert` return `{"celsius": 0}` instead of `{"fahrenheit": ...}`. Predict what `label` will do. Write the prediction down. Run it. **(10 min)**
5. Undo it. Run `02_qa_llm.py`. Repeat the same five steps. **(20 min)**
6. Create `Module 4 - LangGraph Fundamentals/MYNOTES.md` and write your three lines. **(5 min)**

That's about an hour. At the end of it you will understand state, nodes, and edges — properly, not vaguely. That's the foundation for all twenty-two modules.

Then do the same tomorrow with the next file.

---

## One last thing

The gap between "I have this code" and "I understand this code" is closed by exactly one activity: **changing something and finding out you were wrong about what would happen.**

Everything in this document is an elaborate way of saying: run it, break it, be surprised, repeat.

Good luck. Go run the first file.
