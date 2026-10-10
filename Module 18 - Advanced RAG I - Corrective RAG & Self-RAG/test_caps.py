"""Deterministic check that the two caps are enforced INDEPENDENTLY.

    uv run python test_caps.py

The routers are pure functions of state, so this needs no API calls — which
matters, because on a healthy document every answer passes IsSUP and IsUSE on
the first try and the loops never execute. This proves the cap logic without
having to provoke a failure.
"""
from self_rag import MAX_RETRIES, MAX_REWRITE_TRIES, route_sup, route_use


def s(**kw) -> dict:
    base = {"sup": "supported", "use": "useful", "retries": 0, "rewrite_tries": 0}
    return {**base, **kw}


def main() -> None:
    # --- IsSUP cap -------------------------------------------------------
    assert route_sup(s(sup="supported")) == "check_use", "supported must advance to IsUSE"
    assert route_sup(s(sup="not_supported", retries=0)) == "revise"
    assert route_sup(s(sup="not_supported", retries=MAX_RETRIES - 1)) == "revise", "last retry allowed"
    assert route_sup(s(sup="not_supported", retries=MAX_RETRIES)) == "no_answer", "cap must stop the loop"
    assert route_sup(s(sup="not_supported", retries=MAX_RETRIES + 5)) == "no_answer"

    # --- IsUSE cap -------------------------------------------------------
    assert route_use(s(use="useful")) == "__end__"
    assert route_use(s(use="not_useful", rewrite_tries=0)) == "rewrite_query"
    assert route_use(s(use="not_useful", rewrite_tries=MAX_REWRITE_TRIES - 1)) == "rewrite_query"
    assert route_use(s(use="not_useful", rewrite_tries=MAX_REWRITE_TRIES)) == "no_answer"

    # --- independence: one cap exhausted must not affect the other -------
    assert route_sup(s(sup="not_supported", retries=0, rewrite_tries=99)) == "revise", \
        "IsSUP must ignore the rewrite counter"
    assert route_use(s(use="not_useful", rewrite_tries=0, retries=99)) == "rewrite_query", \
        "IsUSE must ignore the retry counter"

    print(f"MAX_RETRIES={MAX_RETRIES}  MAX_REWRITE_TRIES={MAX_REWRITE_TRIES}")
    print("all 11 cap assertions passed - both loops bounded, and independently")


if __name__ == "__main__":
    main()
