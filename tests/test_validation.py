"""Validation Tool: schema checks and normalisation of LLM output."""
import json

from rfp.tools.validation_tool import evidence_in_document, validate


def _card(raw, criteria, doc=""):
    return validate(raw, criteria, "Apex Systems", doc)


def test_valid_output_passes_unchanged(criteria):
    raw = json.dumps({"supplier_name": "Apex Systems", "criteria": [
        {"criterion_id": c["criterion_id"], "score": 7, "max_score": 10, "justification": "ok",
         "evidence": "ISO 27001 certified"} for c in criteria], "risks": ["r"], "overall_summary": "s"})
    card = _card(raw, criteria, "We are ISO 27001 certified.")
    assert card.validation_warnings == []
    assert [c.score for c in card.criteria] == [7] * 5
    assert all(c.evidence_found_in_document for c in card.criteria)


def test_invalid_json_scores_everything_zero(criteria):
    card = _card("Sorry, I cannot help with that.", criteria)
    assert all(c.score == 0 and "imputed_missing" in c.validation_flags for c in card.criteria)
    assert any("not valid JSON" in w for w in card.validation_warnings)


def test_markdown_fenced_json_is_parsed(criteria):
    raw = "```json\n" + json.dumps({"criteria": [{"criterion_id": 1, "score": 6, "justification": "x",
                                                    "evidence": "y"}]}) + "\n```"
    card = _card(raw, criteria)
    assert card.criteria[0].score == 6


def test_out_of_range_clipped_and_negative_clipped(criteria):
    raw = {"criteria": [{"criterion_id": 1, "score": 15, "justification": "j", "evidence": "e"},
                        {"criterion_id": 2, "score": -3, "justification": "j", "evidence": "e"}]}
    card = _card(raw, criteria)
    assert card.criteria[0].score == 10 and "clipped" in card.criteria[0].validation_flags
    assert card.criteria[1].score == 0 and "clipped" in card.criteria[1].validation_flags


def test_non_numeric_and_string_scores(criteria):
    raw = {"criteria": [{"criterion_id": 1, "score": "excellent", "justification": "j", "evidence": "e"},
                        {"criterion_id": 2, "score": "8", "justification": "j", "evidence": "e"},
                        {"criterion_id": 3, "score": "7/10", "justification": "j", "evidence": "e"},
                        {"criterion_id": 4, "score": None, "justification": "j", "evidence": "e"}]}
    card = _card(raw, criteria)
    assert [c.score for c in card.criteria[:4]] == [0, 8, 7, 0]
    assert "non_numeric_score" in card.criteria[0].validation_flags


def test_rescale_when_model_uses_different_max(criteria):
    raw = {"criteria": [{"criterion_id": 1, "score": 80, "max_score": 100, "justification": "j", "evidence": "e"}]}
    card = _card(raw, criteria)
    assert card.criteria[0].score == 8 and "rescaled" in card.criteria[0].validation_flags


def test_missing_unknown_duplicate_and_name_matching(criteria):
    raw = {"criteria": [
        {"criterion_id": 1, "score": 5, "justification": "first", "evidence": "e"},
        {"criterion_id": 1, "score": 9, "justification": "dup", "evidence": "e"},
        {"criterion_id": 42, "score": 9, "justification": "unknown", "evidence": "e"},
        {"criterion_name": "commercial value", "score": 6, "justification": "by name", "evidence": "e"},
    ]}
    card = _card(raw, criteria)
    by_id = {c.criterion_id: c for c in card.criteria}
    assert len(card.criteria) == 5                               # every active criterion present
    assert by_id[1].score == 5 and by_id[1].justification == "first"
    assert by_id[3].score == 6 and "matched_by_name" in by_id[3].validation_flags
    for cid in (2, 4, 5):
        assert by_id[cid].score == 0 and "imputed_missing" in by_id[cid].validation_flags
    joined = " ".join(card.validation_warnings)
    assert "Duplicate" in joined and "Unknown criterion_id 42" in joined


def test_supplier_name_mismatch_keeps_entered_name(criteria):
    card = _card({"supplier_name": "Someone Else", "criteria": []}, criteria)
    assert card.supplier_name == "Apex Systems"
    assert any("Someone Else" in w for w in card.validation_warnings)


def test_evidence_grounding():
    doc = "Support is provided 24x7. P1 incidents receive a 30-minute response; P2 within 2 hours."
    assert evidence_in_document("P1 incidents receive a 30-minute response", doc) is True
    assert evidence_in_document("Holds SOC 2 Type II and FedRAMP High authorisation", doc) is False
    assert evidence_in_document("", doc) is None
