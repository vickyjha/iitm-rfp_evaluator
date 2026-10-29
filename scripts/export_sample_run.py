"""Evaluate the bundled sample proposals and write the exported JSON to samples/.

    python scripts/export_sample_run.py            # mock mode
    python scripts/export_sample_run.py --openai   # uses OPENAI_API_KEY / OPENAI_MODEL from env or secrets
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rfp import config, db, samples  # noqa: E402
from rfp.agents import orchestrator  # noqa: E402
from rfp.llm import LLMSettings, default_settings  # noqa: E402


def export(code: str, out_name: str, settings: LLMSettings, include_demo: bool = False,
           inject: list[str] | None = None) -> None:
    rows = samples.supplier_rows(code, include_demo=include_demo)
    valid, errors, _ = orchestrator.validate_inputs(rows)
    if errors:
        raise SystemExit("\n".join(errors))
    meta = samples.for_category(code)
    state = orchestrator.run_evaluation(valid, "evaluator", db.category_by_code(code), meta["rfp_title"],
                                       rfp_reference=meta["rfp_reference"], category_note=meta["category_note"],
                                       llm_settings=settings, inject_malformed_for=inject)
    out = ROOT / "samples" / out_name
    out.write_text(json.dumps(state.get("result") or {"error": state.get("error")}, indent=2))
    order = " > ".join(x["supplier_name"] for x in state.get("result", {}).get("leaderboard", []))
    print(f"{out.relative_to(ROOT)}: {state['status']}  {order}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai", action="store_true")
    args = parser.parse_args()
    config.load_streamlit_secrets()
    db.init_db()
    settings = default_settings() if args.openai else LLMSettings()
    if args.openai and not settings.is_openai:
        raise SystemExit("Set OPENAI_API_KEY first.")
    (ROOT / "samples").mkdir(exist_ok=True)
    export("OTHERS", "sample_run_core_suppliers.json", settings)
    export("OTHERS", "sample_run_validation_cases.json", settings, include_demo=True, inject=["BrightPath Tech"])
    export("TECH_AI_GOV", "sample_run_ai_governance.json", settings)
    export("OFFICE_STATIONERY", "sample_run_stationery_tie_break.json", settings)
    export("AUTO_DASHCAM", "sample_run_dashcam.json", settings)
