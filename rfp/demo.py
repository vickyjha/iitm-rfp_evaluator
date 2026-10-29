"""Create demo evaluations from the bundled samples (mock mode, no API cost)."""
from __future__ import annotations

from datetime import date

from rfp import db, samples
from rfp.agents import orchestrator
from rfp.llm import LLMSettings


def seed_demo_runs(created_by: str = "evaluator", today: date | None = None, tracing=None) -> list[str]:
    """One mock evaluation per category; 'Others' also includes the validation and error examples."""
    run_ids = []
    for cat in db.list_categories():
        meta = samples.for_category(cat["code"])
        if not meta:
            continue
        rows = samples.supplier_rows(cat["code"], include_demo=cat["code"] == "OTHERS", today=today)
        valid, errors, _ = orchestrator.validate_inputs(rows, today=today)
        if errors:
            continue
        state = orchestrator.run_evaluation(
            valid, created_by, cat, meta["rfp_title"], rfp_reference=meta["rfp_reference"],
            category_note=meta.get("category_note", ""), llm_settings=LLMSettings(),
            inject_malformed_for=["BrightPath Tech"] if cat["code"] == "OTHERS" else None, tracing=tracing)
        run_ids.append(state["rfp_run_id"])
    return run_ids

