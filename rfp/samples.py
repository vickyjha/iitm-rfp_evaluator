"""Access to the bundled synthetic sample proposals (data/sample_rfps)."""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

from rfp import config


@lru_cache(maxsize=1)
def metadata() -> dict:
    path = config.SAMPLE_RFP_DIR / "sample_metadata.json"
    if not path.exists():
        return {"categories": {}, "error_cases": []}
    data = json.loads(path.read_text())
    return data if "categories" in data else {"categories": {}, "error_cases": []}


def for_category(code: str) -> dict | None:
    return metadata()["categories"].get(code)


def error_cases() -> list[dict]:
    return metadata().get("error_cases", [])


def read(entry: dict) -> bytes:
    return (config.SAMPLE_RFP_DIR / entry["file"]).read_bytes()


def file_name(entry: dict) -> str:
    return entry["file"].rsplit("/", 1)[-1]


def supplier_rows(code: str, include_demo: bool = False, today: date | None = None) -> list[dict]:
    """Rows ready for orchestrator.validate_inputs().

    Sample submission dates are shifted so the newest one is today (or `today`), keeping the gaps between
    suppliers - and therefore every tie-break - exactly as designed, whenever the app is run.
    """
    meta = for_category(code) or {"suppliers": []}
    entries = [s for s in meta["suppliers"] if include_demo or s["demo_role"] == "core"]
    if include_demo:
        entries += [e for e in error_cases() if e["demo_role"].startswith("error case")]
    dates = [date.fromisoformat(s["submission_date"]) for s in entries]
    shift = ((today or date.today()) - max(dates)) if dates else None
    return [{"supplier_name": s["supplier_name"], "submission_date": d + shift,
             "experience_rating": s["experience_rating"], "file_name": file_name(s), "file_bytes": read(s)}
            for s, d in zip(entries, dates)]
