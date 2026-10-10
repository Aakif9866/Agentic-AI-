"""Live verification — deliberately tiny. 3 real calls, ~$0.0002.

    uv run python live_check.py

Everything that CAN be mocked is mocked in test_gateway.py (0 calls). This
file only covers what mocks cannot prove: that a real provider failure really
does fall through to a real provider that really answers.

Never prints key values.
"""
import os
from typing import Literal

from pydantic import BaseModel

import gateway as gw

gw.MAX_CALLS = 8  # hard ceiling for this script, well under the default


class Verdict(BaseModel):
    sentiment: Literal["positive", "negative"]
    confidence: int


def line(label: str, res: gw.Result) -> None:
    path = " -> ".join(
        f"{a.alias}{'' if a.ok else '(' + a.error_kind.replace('ProviderError', '') + ')'}"
        for a in res.attempts
    )
    print(f"  {label}")
    print(f"    served by : {res.provider}")
    print(f"    path      : {path}")
    print(f"    fell_back : {res.fell_back}")


if __name__ == "__main__":
    print("configured providers:")
    for s in gw.status():
        mark = "yes" if s["configured"] else "NO "
        print(f"  {mark} {s['alias']:<9} {s['model']:<34} "
              f"native_structured={s['native_structured']}")
    print(f"\ndefault order: {gw.fallback_order()}\n")

    # 1. normal path — whoever is first answers (Groq = free tier)
    print("[1] normal call, default order")
    line("chat('Reply with exactly: OK')",
         gw.chat("Reply with exactly: OK"))

    # 2. FORCED FAILURE -> real fallback. An invalid key fails auth without
    #    billing tokens, so this costs only the successful fallback call.
    print("\n[2] forced failure: Groq key invalidated in-process")
    real = os.environ.get("GROQ_API_KEY", "")
    os.environ["GROQ_API_KEY"] = "not-a-real-key-forces-401"  # deliberately NOT key-shaped, so the CI secret scan stays strict
    try:
        line("chat(...) with groq broken", gw.chat("Reply with exactly: OK",
                                                   order=["groq", "deepseek"]))
    finally:
        os.environ["GROQ_API_KEY"] = real  # always restore

    # 3. capability-aware structured output against a real provider
    print("\n[3] structured output, real call")
    res = gw.structured(Verdict, "Classify the sentiment of: 'I love this product'",
                        order=["groq"])
    line("structured(Verdict, ...) via groq (needs json_mode)", res)
    print(f"    parsed    : sentiment={res.value.sentiment} confidence={res.value.confidence}")

    print(f"\ntotal real calls made: {gw.calls_made()}")
