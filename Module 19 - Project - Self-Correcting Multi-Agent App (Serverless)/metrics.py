"""Run the loop over several topics and record iterations-to-approval.

    uv run python metrics.py            -> writes metrics.json

The point is the DISTRIBUTION. A reviewer that always approves on pass 1
proves nothing; one that never approves is broken. A healthy loop shows a
mix. Topics are deliberately mixed: plain technical ones the writer handles
easily, and marketing-flavoured ones that tempt it into banned buzzwords.
"""
import json
import time
from pathlib import Path

from graph import MAX_WORDS, generate

TOPICS = [
    "why a reducer is needed when graph nodes run in parallel",
    "what a checkpointer gives you in an agent framework",
    "the business value of AI agents for a mid-sized company",
    "why our agent platform is better than the competition",
    "how human-in-the-loop approval prevents costly mistakes",
    "what makes a developer tool genuinely enjoyable to use",
]

if __name__ == "__main__":
    runs = []
    for i, topic in enumerate(TOPICS, 1):
        t0 = time.perf_counter()
        out = generate(topic, max_iteration=3)
        runs.append({
            "topic": topic,
            "iterations_to_approval": out["iteration"],
            "approved": out["verdict"] == "approved",
            "final_word_count": out["word_count"],
            "buzzwords_in_final": out["banned_found"],
            "drafts": len(out["drafts"]),
            "seconds": round(time.perf_counter() - t0, 1),
        })
        print(f"[{i}/{len(TOPICS)}] {out['iteration']} iter  "
              f"{'approved' if runs[-1]['approved'] else 'HIT CAP'}  "
              f"{out['word_count']}w  {topic[:46]}")

    approved = [r for r in runs if r["approved"]]
    dist: dict[str, int] = {}
    for r in runs:
        k = str(r["iterations_to_approval"])
        dist[k] = dist.get(k, 0) + 1

    summary = {
        "word_limit": MAX_WORDS,
        "max_iteration": 3,
        "runs": len(runs),
        "approved": len(approved),
        "hit_cap": len(runs) - len(approved),
        "mean_iterations": round(sum(r["iterations_to_approval"] for r in runs) / len(runs), 2),
        "iteration_distribution": dist,
        "converged_within_3": sum(1 for r in approved if r["iterations_to_approval"] <= 3),
    }

    Path("metrics.json").write_text(json.dumps({"summary": summary, "runs": runs}, indent=2))

    print("\n--- summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("\nwrote metrics.json")
