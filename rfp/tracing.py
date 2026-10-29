"""LangSmith tracing, configured from the UI per browser session.

Each evaluation run is wrapped in its own tracing context with an explicit client, so the switch on the
AI engine page decides whether that run is traced, whatever the environment variables say. After the run,
the root trace's ID and URL are stored with the run so users can open it from Results and Run history.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Iterator

from rfp import config

ENDPOINTS = {
    "US (api.smith.langchain.com)": "https://api.smith.langchain.com",
    "EU (eu.api.smith.langchain.com)": "https://eu.api.smith.langchain.com",
}
DEFAULT_PROJECT = "rfp-evaluator"
LANGSMITH_HOME = "https://smith.langchain.com"


@dataclass
class TracingSettings:
    enabled: bool = False
    api_key: str = field(default="", repr=False)
    project: str = DEFAULT_PROJECT
    endpoint: str = "https://api.smith.langchain.com"
    key_source: str = ""          # "secrets", "session" or ""

    @property
    def active(self) -> bool:
        return self.enabled and bool(self.api_key)

    @property
    def label(self) -> str:
        return f"LangSmith tracing on ({self.project})" if self.active else "Tracing off"

    @property
    def web_url(self) -> str:
        return "https://eu.smith.langchain.com" if "eu." in self.endpoint else LANGSMITH_HOME


def default_tracing() -> TracingSettings:
    key = config.get("LANGSMITH_API_KEY") or ""
    on = (config.get("RFP_TRACING_DEFAULT") or config.get("LANGSMITH_TRACING", "true") or "true").lower() == "true"
    return TracingSettings(enabled=bool(key) and on, api_key=key,
                           project=config.get("LANGSMITH_PROJECT", DEFAULT_PROJECT) or DEFAULT_PROJECT,
                           endpoint=config.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
                           key_source="secrets" if key else "")


def make_client(settings: TracingSettings):
    from langsmith import Client

    return Client(api_key=settings.api_key, api_url=settings.endpoint, timeout_ms=(5000, 10000))


def test_connection(settings: TracingSettings) -> tuple[bool, str]:
    """Check the key by listing one project."""
    try:
        client = make_client(settings)
        list(client.list_projects(limit=1))
        return True, "Connected to LangSmith."
    except Exception as exc:  # noqa: BLE001 - shown to the user
        text = str(exc)
        if "401" in text or "403" in text or "Unauthorized" in text:
            return False, "LangSmith rejected the API key. Check the key and the region (US or EU)."
        return False, f"Couldn't reach LangSmith: {text[:200]}"


def _new_run_id():
    try:
        from langsmith._internal._uuid import uuid7

        return uuid7()
    except Exception:  # noqa: BLE001 - older langsmith
        import uuid

        return uuid.uuid4()


@contextlib.contextmanager
def run_context(settings: TracingSettings | None, run_name: str, metadata: dict) -> Iterator[dict]:
    """Trace the block when tracing is active; otherwise make sure nothing is traced.

    Yields a dict {'enabled','project','trace_id','url','error'}. When tracing is active, 'trace_id' is set
    before the block runs: pass it as the root run_id so the run can be linked afterwards.
    """
    from langsmith.run_helpers import tracing_context

    info: dict = {"enabled": False, "project": None, "trace_id": None, "url": None, "error": None}
    if not settings or not settings.active:
        with tracing_context(enabled=False):
            yield info
        return

    import time
    from types import SimpleNamespace

    from langchain_core.tracers.context import tracing_v2_enabled

    client = make_client(settings)
    run_id = _new_run_id()
    info.update(enabled=True, project=settings.project, trace_id=str(run_id))
    with tracing_context(enabled=True, client=client, project_name=settings.project, metadata=metadata), \
            tracing_v2_enabled(project_name=settings.project, client=client, tags=["rfp-evaluation"]) as tracer:
        yield info
        try:
            tracer.wait_for_futures()
        except Exception:  # noqa: BLE001
            pass
    last_error = None
    for attempt in range(3):  # the project can take a moment to appear after the first upload
        try:
            client.flush()
            info["url"] = client.get_run_url(run=SimpleNamespace(id=run_id), project_name=settings.project)
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001 - the evaluation succeeded; only the link is missing
            last_error = exc
            time.sleep(1 + attempt)
    if last_error is not None:
        info["error"] = f"The trace was sent, but its link could not be fetched: {str(last_error)[:160]}"
    _ = run_name


def fetch_run_url(settings: TracingSettings, trace_id: str, project: str) -> tuple[str | None, str]:
    """Look up the LangSmith link for a trace recorded earlier (used by the 'Get link' button)."""
    from types import SimpleNamespace

    try:
        url = make_client(settings).get_run_url(run=SimpleNamespace(id=trace_id), project_name=project)
        return url, ""
    except Exception as exc:  # noqa: BLE001 - shown to the user
        return None, f"Couldn't fetch the link from LangSmith: {str(exc)[:200]}"
