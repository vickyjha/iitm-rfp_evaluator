import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Every test gets its own SQLite file and runs the LLM in offline mock mode."""
    monkeypatch.setenv("RFP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    from rfp import db

    db.init_db()
    yield


@pytest.fixture
def criteria():
    return [
        {"criterion_id": 1, "name": "Technical Capability", "description": "tech", "weight": 30, "max_score": 10},
        {"criterion_id": 2, "name": "Implementation Plan", "description": "plan", "weight": 20, "max_score": 10},
        {"criterion_id": 3, "name": "Commercial Value", "description": "price", "weight": 20, "max_score": 10},
        {"criterion_id": 4, "name": "Security & Compliance", "description": "sec", "weight": 20, "max_score": 10},
        {"criterion_id": 5, "name": "Support & Experience", "description": "support", "weight": 10, "max_score": 10},
    ]


def make_supplier(name, scores, submission_date="2026-10-10", experience=50, criteria_defs=None):
    criteria_defs = criteria_defs or [{"criterion_id": i + 1, "name": f"C{i + 1}", "max_score": 10}
                                      for i in range(len(scores))]
    return {
        "supplier_name": name, "submission_date": submission_date, "experience_rating": experience,
        "scorecard": {"criteria": [
            {"criterion_id": c["criterion_id"], "criterion_name": c["name"], "score": float(s),
             "max_score": c["max_score"], "justification": "", "evidence": "", "validation_flags": []}
            for c, s in zip(criteria_defs, scores)]},
    }
