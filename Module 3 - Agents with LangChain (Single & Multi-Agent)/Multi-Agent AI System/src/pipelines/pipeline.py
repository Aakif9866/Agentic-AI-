"""The pipeline: search -> reader -> writer -> critic.

Each step is its own function so the CLI (main.py) and the UI (app.py) run the exact same logic.
"""

import re

from src.agents.agents import build_reader_agent, build_search_agent, critic_chain, writer_chain

# ==========================================
# STEPS
# ==========================================

def search_step(topic: str) -> str:
    result = build_search_agent().invoke({
        "messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]
    })
    return result["messages"][-1].content


def reader_step(topic: str, search: str) -> str:
    # URLs sit at the end of the search summary, so a plain search[:800] would cut them off.
    urls = "\n".join(dict.fromkeys(re.findall(r"https?://[^\s)\]>\"']+", search)))  # unique, in order
    result = build_reader_agent().invoke({
        "messages": [("user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Candidate URLs:\n{urls}\n\n"
            f"Search Results (excerpt):\n{search[:800]}")]
    })
    return result["messages"][-1].content


def writer_step(topic: str, search: str, reader: str) -> str:
    research = f"SEARCH RESULTS:\n{search}\n\nDETAILED SCRAPED CONTENT:\n{reader}"
    return writer_chain.invoke({"topic": topic, "research": research})


def critic_step(report: str) -> str:
    return critic_chain.invoke({"report": report})


# ==========================================
# FULL PIPELINE (CLI)
# ==========================================

def run_research_pipeline(topic: str) -> dict:
    """Run all four steps, printing each output. Returns {"search", "reader", "writer", "critic"}."""
    r = {}
    print(f"\n=== 1/4 SEARCH: {topic} ===")
    r["search"] = search_step(topic)
    print(r["search"])

    print("\n=== 2/4 READER ===")
    r["reader"] = reader_step(topic, r["search"])
    print(r["reader"])

    print("\n=== 3/4 WRITER ===")
    r["writer"] = writer_step(topic, r["search"], r["reader"])
    print(r["writer"])

    print("\n=== 4/4 CRITIC ===")
    r["critic"] = critic_step(r["writer"])
    print(r["critic"])
    return r
