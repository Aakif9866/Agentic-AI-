"""Capability probe — what can each configured provider ACTUALLY do?

    uv run python probe_providers.py

Costs ~1 tiny call per capability per provider (9 max). Run it once, read the
matrix, then build against reality instead of assumptions. Never prints keys.
"""
import os
import sys
import warnings
from typing import Literal

from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel

warnings.filterwarnings("ignore")
load_dotenv()

# langchain-google-genai reads GOOGLE_API_KEY; the key is usually issued as
# GEMINI_API_KEY. Bridge it so either name works.
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

CANDIDATES = [
    ("groq", "GROQ_API_KEY", "groq:openai/gpt-oss-120b"),
    ("deepseek", "DEEPSEEK_API_KEY", "deepseek:deepseek-chat"),
    ("gemini", "GOOGLE_API_KEY", "google_genai:gemini-3.8-flash"),
]


@tool
def add(a: int, b: int) -> int:
    """Add two integers together."""
    return a + b


class Verdict(BaseModel):
    sentiment: Literal["positive", "negative"]
    confidence: int


def probe(alias: str, model: str) -> dict:
    from langchain.chat_models import init_chat_model

    r: dict[str, str] = {}
    try:
        llm = init_chat_model(model, temperature=0)
    except Exception as e:
        return {"chat": f"INIT FAIL: {type(e).__name__}", "tools": "-", "structured": "-",
                "json_mode": "-", "err": str(e)[:150]}

    # 1. plain chat
    try:
        out = llm.invoke("Reply with exactly: OK").content
        r["chat"] = "yes" if out else "empty reply"
    except Exception as e:
        r["chat"] = f"FAIL {type(e).__name__}"
        r["err"] = str(e)[:150]
        return {**r, "tools": "-", "structured": "-", "json_mode": "-"}

    # 2. tool calling
    try:
        msg = llm.bind_tools([add]).invoke("What is 2847 plus 1593? Use the tool.")
        r["tools"] = "yes" if getattr(msg, "tool_calls", None) else "no tool_call emitted"
    except Exception as e:
        r["tools"] = f"FAIL {type(e).__name__}"

    # 3. structured output, native mode
    try:
        v = llm.with_structured_output(Verdict).invoke("Classify: 'I love this product'")
        r["structured"] = "yes" if v.sentiment else "empty"
    except Exception as e:
        r["structured"] = f"FAIL {type(e).__name__}"

    # 4. structured output via json_mode (the Groq workaround)
    try:
        llm.with_structured_output(Verdict, method="json_mode").invoke(
            'Classify sentiment. Respond with JSON of the exact form '
            '{"sentiment": "positive"|"negative", "confidence": int}.\n'
            "Text: I love this product"
        )
        r["json_mode"] = "yes"
    except Exception as e:
        r["json_mode"] = f"FAIL {type(e).__name__}"

    return r


if __name__ == "__main__":
    # --only <alias> probes a single provider, so re-checking one does not
    # re-bill the others. Each capability is one tiny call.
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
        print(f"(probing only: {only})")

    print(f"{'provider':<10}{'key':<8}{'chat':<10}{'tools':<22}{'structured':<22}{'json_mode'}")
    print("-" * 94)
    for alias, env, model in CANDIDATES:
        if only and alias != only:
            continue
        if not os.getenv(env):
            print(f"{alias:<10}{'MISSING':<8}{'-':<10}{'-':<22}{'-':<22}-")
            continue
        res = probe(alias, model)
        print(f"{alias:<10}{'set':<8}{res.get('chat','-'):<10}"
              f"{res.get('tools','-'):<22}{res.get('structured','-'):<22}{res.get('json_mode','-')}")
        if res.get("err"):
            print(f"{'':<10}└─ {res['err']}")
    print("\nmodel ids probed:")
    for alias, _, m in CANDIDATES:
        if only and alias != only:
            continue
        print(f"  {alias:<10}{m}")
