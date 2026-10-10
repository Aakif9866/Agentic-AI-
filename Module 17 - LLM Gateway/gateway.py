"""Multi-provider LLM gateway: Groq, DeepSeek, Gemini.

One place that knows (a) which providers are configured, (b) what each one can
actually do, and (c) what to do when one fails.

    from gateway import chat, structured, PROVIDERS

Design notes
------------
* Capabilities are NOT assumed equal. Measured with probe_providers.py:
  Groq cannot do native structured output and needs method="json_mode";
  Gemini can. The gateway picks the right method per provider so callers
  don't have to care.
* Failures are classified. A 402/401 means "this provider will never work
  right now" -> move on immediately, don't burn retries. A 429/timeout is
  transient -> it still moves on, but is reported differently.
* Every call is bounded by a timeout, so a hanging provider can't hang you.
* Nothing here prints or logs an API key.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv()

# langchain-google-genai reads GOOGLE_API_KEY, but the key is issued as
# GEMINI_API_KEY. Bridge it so either name works.
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

log = logging.getLogger("gateway")

DEFAULT_TIMEOUT = float(os.getenv("GATEWAY_TIMEOUT_S", "30"))
# Application-level spend guard: refuse past N calls per process.
MAX_CALLS = int(os.getenv("GATEWAY_MAX_CALLS", "200"))
_calls_made = 0


@dataclass(frozen=True)
class Provider:
    alias: str
    env_key: str
    model: str                     # as init_chat_model wants it: "provider:model"
    native_structured: bool        # False -> must use method="json_mode"
    supports_tools: bool
    notes: str = ""


# Verified by probe_providers.py on 2026-10-10. Re-run it if anything changes;
# do NOT edit these flags from memory or documentation.
PROVIDERS: dict[str, Provider] = {
    "groq": Provider(
        "groq", "GROQ_API_KEY", "groq:openai/gpt-oss-120b",
        native_structured=False, supports_tools=True,
        notes="free tier; native structured output fails, json_mode works; serialises tool calls",
    ),
    "gemini": Provider(
        "gemini", "GOOGLE_API_KEY", "google_genai:gemini-3.8-flash",
        native_structured=True, supports_tools=True,
        notes="native structured output works; vision-capable; older gemini-2.x 404s for new keys",
    ),
    "deepseek": Provider(
        "deepseek", "DEEPSEEK_API_KEY", "deepseek:deepseek-chat",
        native_structured=True, supports_tools=True,
        notes="native structured output works; cheapest of the three; NO embeddings API",
    ),
}


def configured(alias: str) -> bool:
    p = PROVIDERS.get(alias)
    return bool(p and os.getenv(p.env_key))


def fallback_order() -> list[str]:
    """Preference order, overridable with GATEWAY_ORDER=gemini,groq.

    Only configured providers are returned, in order.
    """
    # Groq first because its tier is free, so routine calls cost nothing.
    # DeepSeek second: cheapest paid, and unlike Groq it does native
    # structured output. Gemini last of the three: most capable (vision) and
    # the one to reserve for hard reasoning / image work.
    raw = os.getenv("GATEWAY_ORDER", "groq,deepseek,gemini")
    return [a.strip() for a in raw.split(",") if a.strip() in PROVIDERS and configured(a.strip())]


class PermanentProviderError(RuntimeError):
    """Auth/billing failure — retrying this provider now is pointless."""


class TransientProviderError(RuntimeError):
    """Rate limit, timeout, 5xx — might work later."""


class BudgetExceeded(RuntimeError):
    """Application spend guard tripped. Must NOT be treated as a provider
    failure, or the fallback loop swallows it and reports 'all providers
    failed' — which is both wrong and alarming."""


def classify(exc: Exception) -> type[Exception]:
    """Decide whether a provider is worth retrying. Drives fallback behaviour."""
    s = f"{type(exc).__name__} {exc}".lower()
    if any(k in s for k in ("402", "insufficient balance", "401", "unauthorized",
                            "api_key", "permission", "not_found", "404", "quota exceeded")):
        return PermanentProviderError
    if any(k in s for k in ("429", "rate", "timeout", "timed out", "503", "500",
                            "unavailable", "connection")):
        return TransientProviderError
    return TransientProviderError  # unknown -> treat as transient, but still fall through


def _budget_check() -> None:
    global _calls_made
    if _calls_made >= MAX_CALLS:
        raise BudgetExceeded(
            f"gateway spend guard: {MAX_CALLS} calls already made this process "
            "(raise GATEWAY_MAX_CALLS if intended)"
        )
    _calls_made += 1


def _json_hint(schema) -> str:
    """Build an explicit shape hint for providers lacking native structured output.

    Listing only field NAMES is not enough: a live run returned
    {"confidence": 0.99} for an int field, because the model guessed a
    probability. Types and enum values have to be stated.
    """
    try:
        props = schema.model_json_schema().get("properties", {})
    except Exception:  # noqa: BLE001 - any schema we can't introspect
        names = ", ".join(f'"{n}"' for n in getattr(schema, "model_fields", {}))
        return f"\n\nRespond with JSON containing exactly these keys: {names}."

    parts: list[str] = []
    for name, spec in props.items():
        if "enum" in spec:
            t = "|".join(json.dumps(v) for v in spec["enum"])
        elif "const" in spec:
            t = json.dumps(spec["const"])
        else:
            t = {
                "integer": "int (whole number, not a decimal)",
                "number": "float",
                "boolean": "true|false",
                "array": "[...]",
                "object": "{...}",
            }.get(spec.get("type"), "string")
        parts.append(f'"{name}": {t}')
    return "\n\nRespond with JSON of the exact form {" + ", ".join(parts) + "}."


def get_llm(alias: str, *, timeout: float | None = None, **kwargs: Any):
    """Build a chat model for one provider. Raises if it isn't configured."""
    p = PROVIDERS[alias]
    if not configured(alias):
        raise PermanentProviderError(f"{alias}: {p.env_key} is not set")
    from langchain.chat_models import init_chat_model

    return init_chat_model(p.model, timeout=timeout or DEFAULT_TIMEOUT, **kwargs)


@dataclass
class Attempt:
    alias: str
    ok: bool
    error_kind: str = ""
    detail: str = ""


@dataclass
class Result:
    value: Any
    provider: str
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def fell_back(self) -> bool:
        return len(self.attempts) > 1


def _run_with_fallback(
    call: Callable[[str], Any],
    order: list[str] | None = None,
) -> Result:
    """Try each provider in turn. Observable: records every attempt."""
    # `None` means "use the configured default"; `[]` means "explicitly none"
    # and must not silently become the default.
    if order is None:
        order = fallback_order()
    if not order:
        raise PermanentProviderError(
            "no providers configured - set at least one of "
            + ", ".join(p.env_key for p in PROVIDERS.values())
        )

    attempts: list[Attempt] = []
    for alias in order:
        try:
            _budget_check()
            value = call(alias)
            attempts.append(Attempt(alias, ok=True))
            if len(attempts) > 1:
                log.warning("gateway: fell back to %s after %d failure(s)",
                            alias, len(attempts) - 1)
            return Result(value, alias, attempts)
        except BudgetExceeded:
            raise  # never mistake our own guard for a provider outage
        except Exception as e:  # noqa: BLE001 - deliberately broad; we classify it
            kind = classify(e)
            attempts.append(
                Attempt(alias, ok=False, error_kind=kind.__name__, detail=str(e)[:160])
            )
            log.warning("gateway: %s failed (%s): %s", alias, kind.__name__, str(e)[:120])

    # Include the actual detail. "all providers failed: groq=Transient" tells
    # you nothing about what to fix.
    raise TransientProviderError(
        "all providers failed:\n"
        + "\n".join(f"  {a.alias} [{a.error_kind}]: {a.detail}" for a in attempts)
    )


def chat(prompt: str | list, *, order: list[str] | None = None, **kwargs: Any) -> Result:
    """Plain chat with fallback. Returns Result(value=<str>, provider=..., attempts=[...])."""
    def call(alias: str):
        msg = get_llm(alias, **kwargs).invoke(prompt)
        return msg.content

    return _run_with_fallback(call, order)


def structured(schema, prompt: str, *, order: list[str] | None = None, **kwargs: Any) -> Result:
    """Structured output with fallback, using the right method per provider.

    This is the gateway's main reason to exist: Groq needs json_mode plus an
    explicit field-name hint, Gemini does not. Callers shouldn't have to know.
    """
    def call(alias: str):
        llm = get_llm(alias, **kwargs)
        p = PROVIDERS[alias]
        if p.native_structured:
            return llm.with_structured_output(schema).invoke(prompt)
        return llm.with_structured_output(schema, method="json_mode").invoke(
            prompt + _json_hint(schema)
        )

    return _run_with_fallback(call, order)


def status() -> list[dict]:
    """Which providers are configured, and what they can do. No keys revealed."""
    return [
        {
            "alias": p.alias,
            "configured": configured(a),
            "model": p.model,
            "native_structured": p.native_structured,
            "supports_tools": p.supports_tools,
            "notes": p.notes,
        }
        for a, p in PROVIDERS.items()
    ]


def calls_made() -> int:
    return _calls_made
