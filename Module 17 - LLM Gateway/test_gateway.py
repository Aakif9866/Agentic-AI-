"""Gateway tests — ALL MOCKED, zero API calls, zero cost.

    uv run python test_gateway.py

Fallback is the one behaviour you cannot test by hoping a provider breaks, so
every failure mode here is simulated. Live verification is separate
(live_check.py) and makes exactly 2 calls.
"""
import os
import sys

import gateway as gw

PASS, FAIL = 0, 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f"  <- {detail}" if detail else ""))


class FakeMsg:
    def __init__(self, content): self.content = content


def fake_llm(*, fail_with: Exception | None = None, reply: str = "hi"):
    """Minimal stand-in for a chat model."""
    class _LLM:
        def invoke(self, _):
            if fail_with:
                raise fail_with
            return FakeMsg(reply)

        def with_structured_output(self, schema, method=None):
            _LLM.last_method = method
            outer = self

            class _S:
                def invoke(self, prompt):
                    _LLM.last_prompt = prompt
                    if fail_with:
                        raise fail_with
                    return schema(sentiment="positive", confidence=9)
            return _S()
    return _LLM()


# ---------------------------------------------------------------- classify
print("\n[1] failure classification drives whether we bother retrying")
check("402 insufficient balance -> permanent",
      gw.classify(Exception("Error code: 402 Insufficient Balance")) is gw.PermanentProviderError)
check("401 unauthorized -> permanent",
      gw.classify(Exception("401 unauthorized")) is gw.PermanentProviderError)
check("404 model not found -> permanent",
      gw.classify(Exception("404 NOT_FOUND no longer available")) is gw.PermanentProviderError)
check("429 rate limit -> transient",
      gw.classify(Exception("Error code: 429 rate limit")) is gw.TransientProviderError)
check("timeout -> transient",
      gw.classify(TimeoutError("timed out")) is gw.TransientProviderError)
check("unknown -> transient (fail open, keep falling back)",
      gw.classify(ValueError("something weird")) is gw.TransientProviderError)

# ------------------------------------------------------------ order config
print("\n[2] provider order is configuration, and only yields configured providers")
orig_env = dict(os.environ)
for p in gw.PROVIDERS.values():
    os.environ[p.env_key] = "x"          # pretend all configured (dummy, never used)
os.environ["GATEWAY_ORDER"] = "gemini,groq"
check("GATEWAY_ORDER respected", gw.fallback_order() == ["gemini", "groq"],
      str(gw.fallback_order()))
os.environ.pop("GROQ_API_KEY")
check("unconfigured provider dropped from order", gw.fallback_order() == ["gemini"],
      str(gw.fallback_order()))
os.environ.clear(); os.environ.update(orig_env)
os.environ.pop("GATEWAY_ORDER", None)

# --------------------------------------------------------------- fallback
print("\n[3] fallback: first provider fails, second answers")
calls: list[str] = []


def chat_call_factory(failing: set[str]):
    def call(alias: str):
        calls.append(alias)
        if alias in failing:
            raise Exception("Error code: 402 Insufficient Balance")
        return f"answer-from-{alias}"
    return call


calls.clear()
res = gw._run_with_fallback(chat_call_factory({"groq"}), order=["groq", "gemini"])
check("second provider served the request", res.value == "answer-from-gemini", res.value)
check("Result.provider names the winner", res.provider == "gemini", res.provider)
check("fell_back flag set", res.fell_back is True)
check("both attempts recorded (observable)", len(res.attempts) == 2, str(res.attempts))
check("failed attempt classified permanent",
      res.attempts[0].error_kind == "PermanentProviderError", res.attempts[0].error_kind)
check("providers tried in order", calls == ["groq", "gemini"], str(calls))

print("\n[4] no fallback needed -> single attempt, fell_back False")
calls.clear()
res = gw._run_with_fallback(chat_call_factory(set()), order=["groq", "gemini"])
check("first provider used", res.provider == "groq")
check("only one attempt", len(res.attempts) == 1 and res.fell_back is False)

print("\n[5] all providers fail -> raises, and the error names every failure")
try:
    gw._run_with_fallback(chat_call_factory({"groq", "gemini"}), order=["groq", "gemini"])
    check("raises when everything fails", False, "no exception raised")
except gw.TransientProviderError as e:
    check("raises when everything fails", True)
    check("error mentions both providers", "groq" in str(e) and "gemini" in str(e), str(e))

print("\n[6] empty order -> permanent error, not a confusing crash")
try:
    gw._run_with_fallback(chat_call_factory(set()), order=[])
    check("empty order raises", False)
except gw.PermanentProviderError as e:
    check("empty order raises PermanentProviderError", True)
    check("message tells you which env vars to set", "GROQ_API_KEY" in str(e))

# ------------------------------------------------ capability-aware method
print("\n[7] structured output picks the right method PER PROVIDER (the point of this module)")
from pydantic import BaseModel          # noqa: E402
from typing import Literal             # noqa: E402


class Verdict(BaseModel):
    sentiment: Literal["positive", "negative"]
    confidence: int


_real_get_llm = gw.get_llm
try:
    holder: dict[str, object] = {}

    def fake_get_llm(alias, **kw):
        llm = fake_llm()
        holder[alias] = llm
        return llm

    gw.get_llm = fake_get_llm

    r = gw.structured(Verdict, "Classify: great", order=["gemini"])
    check("gemini (native_structured=True) -> method=None",
          type(holder["gemini"]).last_method is None,
          str(type(holder["gemini"]).last_method))

    r = gw.structured(Verdict, "Classify: great", order=["groq"])
    check("groq (native_structured=False) -> method='json_mode'",
          type(holder["groq"]).last_method == "json_mode",
          str(type(holder["groq"]).last_method))
    prompt = type(holder["groq"]).last_prompt
    check("groq prompt gets explicit field-name hint",
          '"sentiment"' in prompt and '"confidence"' in prompt, prompt[-90:])
    check("gemini prompt NOT polluted with the workaround hint",
          "exactly these keys" not in str(type(holder["gemini"]).last_prompt))
finally:
    gw.get_llm = _real_get_llm

# ------------------------------------------------------------ spend guard
print("\n[8] application-level spend guard")
orig_max, orig_made = gw.MAX_CALLS, gw._calls_made
try:
    gw.MAX_CALLS = 2
    gw._calls_made = 0
    gw._run_with_fallback(chat_call_factory(set()), order=["groq"])
    gw._run_with_fallback(chat_call_factory(set()), order=["groq"])
    try:
        gw._run_with_fallback(chat_call_factory(set()), order=["groq"])
        check("guard trips past MAX_CALLS", False, "third call was allowed")
    except Exception as e:
        check("guard trips past MAX_CALLS", isinstance(e, gw.BudgetExceeded) and "spend guard" in str(e), f"{type(e).__name__}: {str(e)[:60]}")
finally:
    gw.MAX_CALLS, gw._calls_made = orig_max, orig_made

# --------------------------------------------------------------- hygiene
print("\n[9] status() never leaks a key")
blob = str(gw.status())
leaked = [p.env_key for p in gw.PROVIDERS.values()
          if (v := os.getenv(p.env_key)) and len(v) > 8 and v in blob]
check("no key value present in status() output", not leaked, str(leaked))

print(f"\n{'=' * 56}\n{PASS} passed, {FAIL} failed  (0 API calls, $0.00)")
sys.exit(1 if FAIL else 0)
