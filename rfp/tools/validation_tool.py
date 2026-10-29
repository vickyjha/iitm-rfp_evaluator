"""Validation Tool: turn raw LLM output into a complete, in-range, typed scorecard.

Rules (every repair is recorded as a warning and as a flag on the affected criterion):
  1. Parse JSON (strips ``` fences, falls back to the first {...} block). Unparseable -> empty result.
  2. Map each item to an active criterion by criterion_id, or by name if the id is missing/wrong.
     Unknown criteria are dropped; duplicates keep the first occurrence.
  3. Coerce scores to numbers ("8", "8/10", 8.0). Non-numeric or missing -> 0.
  4. If the model used a different max_score than the database, rescale to the database maximum.
  5. Clip scores to [0, max_score].
  6. Every active criterion missing from the output gets score 0 (imputed).
  7. Missing justification/evidence -> empty string + warning. Evidence is checked against the document text.
  8. The supplier name entered by the user is always the source of truth.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from langsmith import traceable

from rfp.models import CriterionScore, ValidatedScorecard
from rfp.tools import evidence_tool

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_FRACTION = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")
MAX_TEXT = 1500


def parse_json(raw: Any) -> tuple[dict | None, str | None]:
    """Return (dict, None) or (None, error message)."""
    if raw is None:
        return None, "LLM returned no output"
    if isinstance(raw, dict):
        return raw, None
    if not isinstance(raw, str):
        return None, f"LLM output has unexpected type {type(raw).__name__}"
    text = _FENCE.sub("", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None, "LLM output is not valid JSON"
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            return None, f"LLM output is not valid JSON ({exc.msg})"
    if not isinstance(data, dict):
        return None, "LLM output JSON is not an object"
    return data, None


def _to_number(value: Any) -> tuple[float | None, int | None]:
    """Return (score, max_from_fraction)."""
    if isinstance(value, bool):
        return None, None
    if isinstance(value, (int, float)):
        return (float(value), None) if math.isfinite(value) else (None, None)
    if isinstance(value, str):
        m = _FRACTION.match(value)
        if m:
            return float(m.group(1)), int(float(m.group(2)))
        try:
            v = float(value.strip().rstrip("%"))
            return (v, None) if math.isfinite(v) else (None, None)
        except ValueError:
            return None, None
    return None, None


def _to_int(value: Any) -> int | None:
    try:
        f = float(value)
        return int(f) if f.is_integer() else None
    except (TypeError, ValueError):
        return None


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " | ".join(str(v) for v in value if v is not None)
    return str(value).strip()[:MAX_TEXT]


def evidence_in_document(evidence: str, document_text: str) -> bool | None:
    """True if the evidence is (approximately) present in the document. None when there is no evidence."""
    loc = evidence_tool.locate(evidence, document_text)
    return None if loc is None else loc["found"]


@traceable(name="validation_tool.validate", run_type="tool")
def validate(raw: Any, criteria: list[dict], supplier_name: str, document_text: str = "") -> ValidatedScorecard:
    warnings: list[str] = []
    by_id = {int(c["criterion_id"]): c for c in criteria}
    by_name = {str(c["name"]).strip().lower(): c for c in criteria}

    data, err = parse_json(raw)
    if err:
        warnings.append(f"{err}; all criteria scored 0.")
        data = {}

    reported_name = str(data.get("supplier_name", "")).strip()
    if reported_name and reported_name.lower() != supplier_name.lower():
        warnings.append(f"LLM reported supplier name '{reported_name}'; using the entered name '{supplier_name}'.")

    items = data.get("criteria", [])
    if data and not isinstance(items, list):
        warnings.append("'criteria' field is not a list; all criteria scored 0.")
        items = []

    results: dict[int, CriterionScore] = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            warnings.append(f"Criteria item #{idx + 1} is not an object; ignored.")
            continue
        flags: list[str] = []
        cid = _to_int(item.get("criterion_id"))
        crit = by_id.get(cid) if cid is not None else None
        if crit is None:
            name = str(item.get("criterion_name") or item.get("name") or "").strip().lower()
            crit = by_name.get(name)
            if crit is None:
                warnings.append(f"Unknown criterion_id {item.get('criterion_id')!r} in LLM output; ignored.")
                continue
            flags.append("matched_by_name")
            warnings.append(f"Criterion '{crit['name']}' matched by name (criterion_id was {item.get('criterion_id')!r}).")
        cid = int(crit["criterion_id"])
        if cid in results:
            warnings.append(f"Duplicate result for '{crit['name']}'; kept the first one.")
            continue

        db_max = int(crit["max_score"])
        score, fraction_max = _to_number(item.get("score"))
        reported_max = _to_int(item.get("max_score")) or fraction_max
        if score is None:
            warnings.append(f"'{crit['name']}': score {item.get('score')!r} is not numeric; set to 0.")
            flags.append("non_numeric_score")
            score = 0.0
        elif reported_max and reported_max > 0 and reported_max != db_max and 0 <= score <= reported_max:
            new = score / reported_max * db_max
            warnings.append(f"'{crit['name']}': score {score:g}/{reported_max} rescaled to {new:.2f}/{db_max}.")
            flags.append("rescaled")
            score = new
        if score < 0 or score > db_max:
            clipped = min(max(score, 0.0), float(db_max))
            warnings.append(f"'{crit['name']}': score {score:g} outside 0-{db_max}; clipped to {clipped:g}.")
            flags.append("clipped")
            score = clipped

        justification = _to_text(item.get("justification"))
        evidence = _to_text(item.get("evidence"))
        if not justification:
            flags.append("missing_justification")
            warnings.append(f"'{crit['name']}': justification missing.")
        if not evidence:
            flags.append("missing_evidence")
            warnings.append(f"'{crit['name']}': evidence missing.")
        location = evidence_tool.locate(evidence, document_text)
        found = None if location is None else location["found"]
        if found is False:
            flags.append("evidence_not_verified")
            warnings.append(f"'{crit['name']}': evidence could not be matched to the document text (review manually).")

        results[cid] = CriterionScore(
            criterion_id=cid, criterion_name=crit["name"], score=round(score, 2), max_score=db_max,
            justification=justification, evidence=evidence, validation_flags=flags,
            evidence_found_in_document=found, evidence_location=location,
        )

    for c in criteria:  # fill missing criteria
        cid = int(c["criterion_id"])
        if cid not in results:
            warnings.append(f"'{c['name']}': no result returned by the LLM; scored 0.")
            results[cid] = CriterionScore(
                criterion_id=cid, criterion_name=c["name"], score=0.0, max_score=int(c["max_score"]),
                justification="No result was returned for this criterion; scored 0 by validation rule.",
                evidence="", validation_flags=["imputed_missing"],
            )

    risks = data.get("risks", [])
    if isinstance(risks, str):
        risks = [risks]
    if not isinstance(risks, list):
        risks = []
    return ValidatedScorecard(
        supplier_name=supplier_name,
        criteria=[results[int(c["criterion_id"])] for c in criteria],
        risks=[_to_text(r) for r in risks if _to_text(r)][:10],
        overall_summary=_to_text(data.get("overall_summary")),
        validation_warnings=warnings,
    )
