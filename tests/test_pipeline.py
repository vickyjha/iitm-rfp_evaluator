"""End-to-end workflow, input validation, documents, categories, criteria audit, passwords (offline mock LLM)."""
import json
from datetime import date, timedelta

import pytest

from rfp import auth, db, samples
from rfp.agents import evaluation_agent, orchestrator
from rfp.agents.mock_llm import FIXTURES
from rfp.llm import LLMSettings, is_chat_model, sort_models
from rfp.tools import document_tool, evidence_tool

TODAY = date(2026, 10, 28)


def _category(code):
    return db.category_by_code(code)


def _run(code, include_demo=False, **kw):
    rows = samples.supplier_rows(code, include_demo=include_demo, today=TODAY)
    valid, errors, _ = orchestrator.validate_inputs(rows, today=TODAY)
    assert errors == []
    meta = samples.for_category(code)
    return orchestrator.run_evaluation(valid, "evaluator", _category(code), meta["rfp_title"],
                                       rfp_reference=meta["rfp_reference"], category_note=meta["category_note"], **kw)


# ------------------------------------------------------------------------------------------- documents
def test_every_sample_file_is_readable_and_formats_are_mixed():
    formats = set()
    for code, meta in samples.metadata()["categories"].items():
        for s in meta["suppliers"]:
            doc = document_tool.extract_text(samples.read(s), samples.file_name(s))
            assert doc["chars"] > 500
            formats.add(doc["file_type"])
    assert formats == {"pdf", "docx", "doc"}


def test_error_case_files_are_rejected():
    scan, renamed = samples.error_cases()
    with pytest.raises(document_tool.DocumentError, match="no readable text"):
        document_tool.extract_text(samples.read(scan), samples.file_name(scan))
    kind, errors = document_tool.check_file(samples.file_name(renamed), samples.read(renamed))
    assert kind == "docx" and "actually a Word (.docx) file" in errors[0]
    assert document_tool.check_file("notes.txt", b"hello")[1]
    assert document_tool.check_file("x.pdf", b"")[1]


def test_mock_fixture_evidence_is_present_in_the_documents():
    for meta in samples.metadata()["categories"].values():
        for s in meta["suppliers"]:
            text = document_tool.extract_text(samples.read(s), samples.file_name(s))["text"]
            for crit, (_, _, evidence) in FIXTURES[s["supplier_name"].lower()]["criteria"].items():
                if evidence:
                    assert evidence_tool.locate(evidence, text)["found"], (s["supplier_name"], crit)


def test_evidence_locator_returns_page_section_and_context():
    text = "[Page 1]\n1. Overview\nWe are great.\n[Page 2]\n2. Support\nP1 incidents receive a 30-minute response."
    loc = evidence_tool.locate("P1 incidents receive a 30 minute response", text)
    assert loc["found"] and loc["page"] == 2 and loc["section"] == "2. Support"
    assert "30-minute response" in loc["match_text"]
    assert evidence_tool.locate("Quantum blockchain certified by NASA", text)["found"] is False


# ------------------------------------------------------------------------------------------- workflow
def test_each_category_uses_its_own_criteria_and_ranks_as_designed():
    expected = {
        "TECH_AI_GOV": ["ClearMind Assurance", "TrustGrid Systems", "Lumora AI", "Kavach Labs"],
        "OFFICE_STATIONERY": ["Inkwell Office Supplies", "OfficeNest India", "PaperTrail Traders",
                              "Shree Ganesh Stationers"],
        "AUTO_DASHCAM": ["Zento Mobility", "VisionDrive Electronics", "RoadEye Technologies", "Kestrel Auto Imaging"],
        "OTHERS": ["NexaWorks", "Apex Systems", "Orbit Digital", "BrightPath Tech"],
    }
    for code, order in expected.items():
        state = _run(code)
        res = state["result"]
        assert [x["supplier_name"] for x in res["leaderboard"]] == order, code
        crit_names = {c["name"] for c in res["criteria_snapshot"]}
        assert crit_names == {c["name"] for c in db.list_criteria(_category(code)["category_id"], active_only=True)}
        assert res["category"]["code"] == code and res["disclaimer"].startswith("Mock mode")


def test_stationery_tie_is_broken_by_experience():
    res = _run("OFFICE_STATIONERY")["result"]
    tie = [t for t in res["tie_break_explanations"] if t["tie_break_used"]]
    assert len(tie) == 1 and tie[0]["deciding_rule"] == 3
    assert tie[0]["higher"] == "OfficeNest India" and tie[0]["lower"] == "PaperTrail Traders"


def test_run_is_persisted_with_documents_and_reproducible():
    first, second = _run("OTHERS"), _run("OTHERS")
    order = [x["supplier_name"] for x in first["result"]["leaderboard"]]
    assert order == [x["supplier_name"] for x in second["result"]["leaderboard"]]
    run = db.get_run(first["rfp_run_id"])
    assert run["status"] == "completed" and run["category_label"] == "Others"
    assert run["rfp_title"] == "Omnichannel Customer Support Platform"
    doc = db.get_document(first["rfp_run_id"], "NexaWorks")
    assert doc["file_type"] == "pdf" and bytes(doc["file_bytes"]).startswith(b"%PDF")
    for s in run["data"]["suppliers"]:
        for c in s["criteria"]:
            assert {"criterion_id", "weight", "score", "benchmark_score", "relative_pct", "evidence",
                    "evidence_location"} <= c.keys()
    assert [r["category_label"] for r in db.list_runs(category_id=_category("OTHERS")["category_id"])] == ["Others"] * 2


def test_validation_and_error_cases_in_one_run():
    state = _run("OTHERS", include_demo=True, inject_malformed_for=["BrightPath Tech"])
    res = state["result"]
    assert state["status"] == "completed_with_warnings"
    assert [e["supplier_name"] for e in res["excluded_suppliers"]] == ["Zenith Infotech"]
    quasar = next(s for s in res["suppliers"] if s["supplier_name"] == "Quasar Solutions")
    imputed = [c["criterion_name"] for c in quasar["criteria"] if "imputed_missing" in c["validation_flags"]]
    assert imputed == ["Commercial Value", "Security & Compliance"]
    bright = next(s for s in res["suppliers"] if s["supplier_name"] == "BrightPath Tech")
    flags = {f for c in bright["criteria"] for f in c["validation_flags"]}
    assert {"clipped", "non_numeric_score", "imputed_missing", "missing_evidence"} <= flags


def test_input_validation_reports_errors_per_row():
    rows = samples.supplier_rows("TECH_AI_GOV", today=TODAY)[:3]
    rows[1]["supplier_name"] = rows[0]["supplier_name"].upper()          # duplicate name (case-insensitive)
    rows[0]["submission_date"] = TODAY + timedelta(days=3)               # future
    rows[2]["submission_date"] = TODAY - timedelta(days=500)             # too old
    rows[2]["experience_rating"] = 140                                    # out of range
    _, errors, per_row = orchestrator.validate_inputs(rows, today=TODAY)
    assert set(per_row) == {0, 1, 2}
    assert any("future" in m for m in per_row[0])
    assert any("already used in row 1" in m for m in per_row[1])
    assert any("days ago" in m for m in per_row[2]) and any("0 and 100" in m for m in per_row[2])
    _, errors, _ = orchestrator.validate_inputs(rows[:1], today=TODAY)
    assert any("at least 2" in e for e in errors)
    dup = samples.supplier_rows("TECH_AI_GOV", today=TODAY)[:2]
    dup[1] = {**dup[1], "file_bytes": dup[0]["file_bytes"], "file_name": dup[0]["file_name"]}
    _, _, per_row = orchestrator.validate_inputs(dup, today=TODAY)
    assert any("Same file as row 1" in m for m in per_row[1])
    blank = {"supplier_name": "", "submission_date": TODAY, "experience_rating": 50, "file_name": "", "file_bytes": b""}
    _, _, per_row = orchestrator.validate_inputs([blank, blank], today=TODAY)
    assert any("supplier name" in m for m in per_row[0]) and any("Attach" in m for m in per_row[0])


def test_run_fails_cleanly_when_no_document_is_readable():
    scan = samples.error_cases()[0]
    rows = [{"supplier_name": n, "submission_date": TODAY, "experience_rating": 50, "file_name": "scan.pdf",
             "file_bytes": samples.read(scan) + extra} for n, extra in (("Zenith", b""), ("Zenith Two", b"\n%"))]
    valid, errors, _ = orchestrator.validate_inputs(rows, today=TODAY)
    assert errors == []
    state = orchestrator.run_evaluation(valid, "evaluator", _category("OTHERS"), "Scanned only")
    assert state["status"] == "failed" and db.get_run(state["rfp_run_id"])["status"] == "failed"


def test_openai_mode_without_key_excludes_suppliers_with_clear_reason():
    state = _run("TECH_AI_GOV", llm_settings=LLMSettings("openai", "gpt-4o-mini", ""), use_cache=False)
    assert state["status"] == "failed" and "no API key" in state["error"]


# ------------------------------------------------------------------------------------------- criteria, users
def test_criteria_changes_are_per_category_audited_and_used_by_next_run():
    reviewer = auth.authenticate("reviewer", "reviewer123")
    assert auth.can_edit_criteria(reviewer)
    assert not auth.can_edit_criteria(auth.authenticate("evaluator", "evaluator123"))
    stat = _category("OFFICE_STATIONERY")["category_id"]
    crit = db.list_criteria(stat)
    crit[0]["weight"], crit[4]["weight"] = 25, 15
    with pytest.raises(ValueError):
        db.save_criteria(stat, crit, "reviewer", "")
    bad = [dict(c) for c in crit]
    bad[0]["weight"] = 50
    with pytest.raises(ValueError, match="total 100"):
        db.save_criteria(stat, bad, "reviewer", "oops")
    out = db.save_criteria(stat, crit, "reviewer", "More weight on sustainability")
    assert out["changes"] == 2
    hist = db.list_criteria_history(stat)
    assert {h["field_name"] for h in hist} == {"weight"} and hist[0]["category_label"] == "Office Supplies – Stationery"
    assert db.list_criteria_history(_category("AUTO_DASHCAM")["category_id"]) == []
    snap = {c["name"]: c["weight"] for c in _run("OFFICE_STATIONERY")["result"]["criteria_snapshot"]}
    assert snap["Pricing & Discounts"] == 25 and snap["Sustainability"] == 15


def test_password_change_policy_and_audit():
    ok, msg = auth.change_password("evaluator", "wrong", "NewPass123", "NewPass123")
    assert not ok and "incorrect" in msg
    assert not auth.change_password("evaluator", "evaluator123", "short1", "short1")[0]
    assert not auth.change_password("evaluator", "evaluator123", "NewPass123", "NewPass124")[0]
    assert not auth.change_password("evaluator", "evaluator123", "evaluator999", "evaluator999")[0]
    ok, _ = auth.change_password("evaluator", "evaluator123", "NewPass123", "NewPass123")
    assert ok
    assert auth.authenticate("evaluator", "evaluator123") is None
    user = auth.authenticate("evaluator", "NewPass123")
    assert user and user["password_set_by"] == "user"
    events = [e["event_type"] for e in db.list_events()]
    assert "password_change" in events and "login" in events
    db.init_db()  # restarting the app must not reset a password the user changed
    assert auth.authenticate("evaluator", "NewPass123")


def test_old_database_is_backed_up_and_recreated(tmp_path, monkeypatch):
    import sqlite3

    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.execute("CREATE TABLE evaluation_criteria (criterion_id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()
    info = db.init_db(old)
    assert info["backup"] and "backup" in info["backup"]
    assert len(db.list_categories(path=old)) == 4


# ------------------------------------------------------------------------------------------- LLM layer
def test_model_filtering_and_sorting():
    ids = ["whisper-1", "gpt-4o-mini", "text-embedding-3-small", "gpt-4o-realtime-preview", "gpt-4.1", "o3-mini",
           "dall-e-3", "gpt-4o-mini-tts", "gpt-4o"]
    chat = [m for m in ids if is_chat_model(m)]
    assert sort_models(chat) == ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "o3-mini"]


def test_openai_path_with_retry_and_cache(monkeypatch):
    """Exercise the OpenAI code path without network: first reply is not JSON, retry returns JSON."""
    calls = []
    crit = db.list_criteria(_category("OTHERS")["category_id"], active_only=True)

    def fake_call(messages, settings):
        calls.append(messages)
        assert settings.api_key == "sk-test-key-123456"
        if len(calls) == 1:
            return "Sure! Here is my evaluation of the supplier."
        return json.dumps({"supplier_name": "Apex Systems", "criteria": [
            {"criterion_id": c["criterion_id"], "score": 6, "max_score": c["max_score"],
             "justification": "j", "evidence": "SOC 2 Type II report"} for c in crit]})

    monkeypatch.setattr(evaluation_agent, "_call_openai", fake_call)
    settings = LLMSettings("openai", "gpt-4o-mini", "sk-test-key-123456", "session")
    msgs = evaluation_agent.build_messages("Apex Systems", crit, "doc text", "Others | RFP: X")
    assert "Use ONLY evidence present" in msgs[0]["content"] and "Procurement context: Others" in msgs[1]["content"]
    out = evaluation_agent.evaluate("Apex Systems", crit, "We hold a SOC 2 Type II report.", settings)
    assert out["source"] == "openai" and len(calls) == 2
    again = evaluation_agent.evaluate("Apex Systems", crit, "We hold a SOC 2 Type II report.", settings)
    assert again["source"] == "cache" and len(calls) == 2
    other_model = LLMSettings("openai", "gpt-4.1", "sk-test-key-123456", "session")
    evaluation_agent.evaluate("Apex Systems", crit, "We hold a SOC 2 Type II report.", other_model)
    assert len(calls) == 3                                       # different model -> not served from cache


# ------------------------------------------------------------------------------------------- tracing
def test_tracing_off_records_nothing_and_on_records_trace_id():
    from rfp.tracing import TracingSettings

    off = _run("TECH_AI_GOV")
    assert off["tracing"]["enabled"] is False and db.list_runs()[0]["trace_id"] is None
    # unreachable endpoint: the evaluation must still succeed and keep the trace ID for a later link lookup
    on = _run("TECH_AI_GOV", tracing=TracingSettings(True, "lsv2_pt_test", "proj", "http://127.0.0.1:9"))
    assert on["status"] == "completed"
    assert on["tracing"]["enabled"] and on["tracing"]["trace_id"] and on["tracing"]["url"] is None
    row = db.list_runs()[0]
    assert row["trace_id"] == on["tracing"]["trace_id"]
    assert db.get_run(on["rfp_run_id"])["data"]["tracing"]["project"] == "proj"
