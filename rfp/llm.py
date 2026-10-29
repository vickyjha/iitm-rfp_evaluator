"""LLM engine settings chosen in the UI: offline mock mode or OpenAI with a selectable model.

The API key entered in the UI lives only in the browser session (Streamlit session_state). It is never
written to the database, the run JSON or LangSmith metadata. A key in app secrets / env is used as the
default when present.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from rfp import config

RECOMMENDED_MODELS = ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4o", "gpt-4.1", "gpt-5-mini", "gpt-5"]
_INCLUDE_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt-")
_EXCLUDE_PARTS = ("audio", "realtime", "tts", "transcribe", "image", "search", "instruct", "embedding", "whisper",
                  "dall-e", "moderation", "codex", "computer-use", "deep-research", "o1-mini", "o1-preview")


@dataclass
class LLMSettings:
    mode: str = "mock"                       # "mock" or "openai"
    model: str = "mock-evaluator"
    api_key: str = field(default="", repr=False)
    key_source: str = ""                     # "secrets", "session" or ""

    @property
    def is_openai(self) -> bool:
        return self.mode == "openai"

    @property
    def label(self) -> str:
        return f"OpenAI · {self.model}" if self.is_openai else "Mock mode (offline)"

    def key_hint(self) -> str:
        return f"{self.api_key[:3]}…{self.api_key[-4:]}" if len(self.api_key) > 10 else ""

    def key_fingerprint(self) -> str:
        return hashlib.sha256(self.api_key.encode()).hexdigest()[:12] if self.api_key else ""


def default_settings() -> LLMSettings:
    """Initial settings for a new session, taken from secrets / environment."""
    key = config.get("OPENAI_API_KEY") or ""
    forced = (config.get("LLM_MODE") or "").lower()
    if key and forced != "mock":
        return LLMSettings("openai", config.openai_model(), key, "secrets")
    return LLMSettings("mock", "mock-evaluator", key, "secrets" if key else "")


_clients: dict[str, object] = {}


def client_for(api_key: str):
    """Cached OpenAI client per key (wrapped for LangSmith tracing when enabled)."""
    fp = hashlib.sha256(api_key.encode()).hexdigest()
    if fp not in _clients:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=120, max_retries=2)
        from langsmith.wrappers import wrap_openai  # traces only inside an active tracing context

        client = wrap_openai(client)
        _clients[fp] = client
    return _clients[fp]


def is_chat_model(model_id: str) -> bool:
    mid = model_id.lower()
    return mid.startswith(_INCLUDE_PREFIXES) and not any(p in mid for p in _EXCLUDE_PARTS)


def sort_models(ids: list[str]) -> list[str]:
    def key(m: str):
        return (RECOMMENDED_MODELS.index(m) if m in RECOMMENDED_MODELS else len(RECOMMENDED_MODELS), m)
    return sorted(set(ids), key=key)


def list_models(api_key: str) -> list[str]:
    """Chat-capable models available to this key, recommended ones first. Raises on auth/network errors."""
    client = client_for(api_key)
    ids = [m.id for m in client.models.list()]
    return sort_models([m for m in ids if is_chat_model(m)])


def friendly_error(exc: Exception) -> str:
    """Turn OpenAI SDK exceptions into a message a user can act on."""
    name = type(exc).__name__
    text = str(exc)
    if name == "AuthenticationError":
        return "OpenAI rejected the API key. Check that it is correct and active."
    if name == "PermissionDeniedError":
        return "This API key doesn't have access to that model or project."
    if name == "RateLimitError":
        return ("OpenAI rate limit or quota reached. Check your billing/usage, wait a moment, or switch to "
                "mock mode.")
    if name == "NotFoundError":
        return "That model isn't available for this API key. Choose another model."
    if name in ("APIConnectionError", "APITimeoutError"):
        return "Couldn't reach OpenAI. Check your internet connection or proxy and try again."
    if name == "BadRequestError":
        return f"OpenAI couldn't process the request: {text[:300]}"
    return f"{name}: {text[:300]}"


def chat_json(settings: LLMSettings, messages: list[dict]) -> str:
    """One chat completion in JSON mode. Retries without temperature/seed for models that don't accept them."""
    from openai import BadRequestError

    client = client_for(settings.api_key)
    kwargs = {"model": settings.model, "messages": messages, "response_format": {"type": "json_object"},
              "temperature": 0, "seed": 42}
    try:
        resp = client.chat.completions.create(**kwargs)
    except BadRequestError as exc:
        msg = str(exc).lower()
        if "temperature" in msg or "seed" in msg or "unsupported" in msg:
            kwargs.pop("temperature", None)
            kwargs.pop("seed", None)
            resp = client.chat.completions.create(**kwargs)
        else:
            raise
    return resp.choices[0].message.content or ""


def test_connection(settings: LLMSettings) -> tuple[bool, str]:
    """Send a tiny JSON-mode request to confirm the key and model work together."""
    try:
        raw = chat_json(settings, [
            {"role": "system", "content": "Reply with a JSON object only."},
            {"role": "user", "content": 'Return {"status": "ok"} as JSON.'},
        ])
        return ("ok" in raw.lower(), f"{settings.model} responded in JSON mode.")
    except Exception as exc:  # noqa: BLE001 - shown to the user
        return False, friendly_error(exc)
