"""Central configuration.

Values are read (in this order) from Streamlit secrets, environment variables, then defaults.
Streamlit secrets are copied into os.environ so that the OpenAI and LangSmith SDKs pick them up.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SAMPLE_RFP_DIR = DATA_DIR / "sample_rfps"

_SECRET_KEYS = [
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "LLM_MODE",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_PROJECT",
    "LANGSMITH_ENDPOINT",
    "RFP_DB_PATH",
    "EVALUATOR_PASSWORD",
    "REVIEWER_PASSWORD",
]


def load_streamlit_secrets() -> None:
    """Copy Streamlit secrets into environment variables (no-op outside Streamlit)."""
    try:
        import streamlit as st

        for key in _SECRET_KEYS:
            if key in st.secrets and not os.environ.get(key):
                os.environ[key] = str(st.secrets[key])
    except Exception:  # no secrets file, or not running under Streamlit
        pass


def get(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    return value if value not in (None, "") else default


def db_path() -> Path:
    return Path(get("RFP_DB_PATH", str(DATA_DIR / "rfp_evaluation.db")))


def openai_model() -> str:
    return get("OPENAI_MODEL", "gpt-4o-mini")


def llm_mode() -> str:
    """'openai' when an API key is configured, otherwise 'mock'. LLM_MODE overrides."""
    mode = (get("LLM_MODE") or "").lower()
    if mode in ("openai", "mock"):
        return mode
    return "openai" if get("OPENAI_API_KEY") else "mock"


def langsmith_enabled() -> bool:
    return bool(get("LANGSMITH_API_KEY")) and (get("LANGSMITH_TRACING", "true").lower() == "true")


APP_NAME = "RFP Insight"
APP_TAGLINE = "Agentic supplier evaluation"
APP_VERSION = "2.0.0"

PROMPT_VERSION = "v2.0"
MAX_DOC_CHARS = 60_000          # text sent to the LLM per supplier
MIN_DOC_CHARS = 200             # below this the PDF is treated as unreadable (e.g. scanned image)
MAX_UPLOAD_MB = 10
ALLOWED_EXTENSIONS = ("pdf", "docx", "doc")
MIN_SUPPLIERS = 2
MAX_SUPPLIERS = 12
MAX_SUBMISSION_AGE_DAYS = 365   # older submission dates are rejected as likely typos
PPI_DECIMALS = 4                # PPI is rounded to this precision before sorting (avoids float noise)
SCORE_DECIMALS = 4
