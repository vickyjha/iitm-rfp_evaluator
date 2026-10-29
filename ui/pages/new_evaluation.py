"""New evaluation: RFP details, category, supplier rows with per-row validation, and the run itself."""
from __future__ import annotations

import re
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from rfp import config, db, samples
from rfp.agents import orchestrator
from rfp.tools.document_tool import TYPE_LABELS, detect_type
from ui.components import esc, page_title
from ui.nav import goto, llm_settings, tracing_settings

ROWS = "ne_rows"
ERRORS = "ne_row_errors"


def _new_row(**kw) -> dict:
    row = {"id": uuid.uuid4().hex[:8], "name": "", "date": date.today(), "rating": 50.0, "file_name": "",
           "file_bytes": b"", "source": ""}
    row.update(kw)
    return row


def _rows() -> list[dict]:
    if ROWS not in st.session_state:
        st.session_state[ROWS] = [_new_row(), _new_row()]
    return st.session_state[ROWS]


def _guess_name(file_name: str) -> str:
    stem = re.sub(r"[_\-]+", " ", Path(file_name).stem)
    stem = re.sub(r"\b(rfp|proposal|response|final|draft|v\d+)\b", "", stem, flags=re.I)
    return " ".join(w.capitalize() for w in stem.split())


def _add_row() -> None:
    rows = _rows()
    if len(rows) < config.MAX_SUPPLIERS:
        rows.append(_new_row())


def _remove_row(row_id: str) -> None:
    st.session_state[ROWS] = [r for r in _rows() if r["id"] != row_id]
    st.session_state.get(ERRORS, {}).pop(row_id, None)


def _clear_file(row_id: str) -> None:
    for r in _rows():
        if r["id"] == row_id:
            r.update(file_name="", file_bytes=b"", source="", uploader_v=r.get("uploader_v", 0) + 1)


def _load_samples(code: str, include_demo: bool) -> None:
    meta = samples.for_category(code)
    if not meta:
        return
    st.session_state[ROWS] = [
        _new_row(name=r["supplier_name"], date=r["submission_date"], rating=float(r["experience_rating"]),
                 file_name=r["file_name"], file_bytes=r["file_bytes"], source="sample")
        for r in samples.supplier_rows(code, include_demo=include_demo)
    ]
    st.session_state["ne_title"] = meta["rfp_title"]
    st.session_state["ne_reference"] = meta["rfp_reference"]
    if meta.get("category_note"):
        st.session_state["ne_note"] = meta["category_note"]
    st.session_state[ERRORS] = {}
    st.session_state.pop("ne_general_errors", None)


def _reset() -> None:
    for k in [ROWS, ERRORS, "ne_title", "ne_reference", "ne_note", "ne_bulk_seen", "ne_general_errors"]:
        st.session_state.pop(k, None)


def _file_chip(row: dict) -> str:
    kind = detect_type(row["file_bytes"]) or "unknown"
    label = TYPE_LABELS.get(kind, "Unrecognised file")
    return (f"<div style='border:1px solid #D6DFDC;border-radius:8px;padding:7px 10px;background:#fff;"
            f"font-size:.86rem'>📄 <b>{esc(row['file_name'])}</b><br><span style='color:#5A6B70'>{label}, "
            f"{len(row['file_bytes']) / 1024:,.0f} KB{' — sample' if row['source'] == 'sample' else ''}"
            f"</span></div>")


def _supplier_row(i: int, row: dict, today: date) -> None:
    errors = st.session_state.get(ERRORS, {}).get(row["id"], [])
    with st.container(border=True):
        c = st.columns([0.35, 2.4, 1.45, 1.25, 3.0, 0.45], vertical_alignment="center", gap="small")
        c[0].markdown(f"**{i + 1}**")
        row["name"] = c[1].text_input("Supplier name", row["name"], key=f"ne_name_{row['id']}_{row.get('name_v', 0)}",
                                      placeholder="e.g. Apex Systems", max_chars=120)
        row["date"] = c[2].date_input("Submission date", row["date"], key=f"ne_date_{row['id']}",
                                      min_value=today - timedelta(days=config.MAX_SUBMISSION_AGE_DAYS),
                                      max_value=today, format="DD/MM/YYYY")
        row["rating"] = c[3].number_input("Past performance", 0.0, 100.0, float(row["rating"]), step=5.0, format="%.0f",
                                          key=f"ne_rating_{row['id']}",
                                          help="Historical experience rating, 0-100. Used only as a tie-break.")
        with c[4]:
            if row["file_bytes"]:
                fc = st.columns([5, 1], vertical_alignment="center")
                fc[0].markdown(_file_chip(row), unsafe_allow_html=True)
                fc[1].button("", key=f"ne_clear_{row['id']}", icon=":material/swap_horiz:", help="Replace file",
                             on_click=_clear_file, args=(row["id"],), type="tertiary")
            else:
                up = st.file_uploader("Proposal file", type=list(config.ALLOWED_EXTENSIONS),
                                      key=f"ne_file_{row['id']}_{row.get('uploader_v', 0)}",
                                      help=f"PDF, DOCX or DOC, up to {config.MAX_UPLOAD_MB} MB")
                if up is not None:
                    row.update(file_name=up.name, file_bytes=up.getvalue(), source="upload")
                    if not row["name"].strip():
                        row.update(name=_guess_name(up.name), name_v=row.get("name_v", 0) + 1)
                    st.rerun()
        c[5].button("", key=f"ne_del_{row['id']}", icon=":material/delete:", help="Remove this supplier",
                    on_click=_remove_row, args=(row["id"],), type="tertiary")
        for e in errors:
            st.markdown(f"<div style='color:#B42318;font-size:.84rem;margin-left:2.2rem'>⚠ {esc(e)}</div>",
                        unsafe_allow_html=True)


def render(user: dict) -> None:
    page_title("New evaluation", "Choose a category, add the supplier proposals, and run the evaluation. "
                                 "Scores are produced by the AI engine and ranked with fixed formulas.")
    today = date.today()
    cats = db.list_categories()
    by_id = {c["category_id"]: c for c in cats}

    # ------------------------------------------------------------------ RFP details
    with st.container(border=True):
        st.markdown("##### RFP details")
        a, b = st.columns([1.2, 1])
        cat_id = a.selectbox("Category", list(by_id), key="ne_category",
                             format_func=lambda i: f"{by_id[i]['icon']}  {by_id[i]['label']}",
                             help="Each category has its own evaluation criteria and weights.")
        category = by_id[cat_id]
        a.caption(category["description"])
        b.text_input("RFP title", key="ne_title", max_chars=150,
                     placeholder="e.g. Annual stationery rate contract 2027")
        b.text_input("RFP reference (optional)", key="ne_reference", max_chars=40, placeholder="e.g. PROC-2026-014")
        if category["requires_note"]:
            a.text_input("Describe the category", key="ne_note", max_chars=120,
                         placeholder="e.g. Facilities management, Cloud hosting")
        criteria = db.list_criteria(cat_id, active_only=True)
        crit_errors = db.validate_criteria_set(criteria)
        with st.expander(f"Criteria for {category['label']} ({len(criteria)} active)"):
            if criteria:
                df = pd.DataFrame(criteria)[["name", "description", "weight", "max_score"]]
                df.columns = ["Criterion", "What the AI looks for", "Weight %", "Max score"]
                st.dataframe(df, hide_index=True, width="stretch",
                             column_config={"Weight %": st.column_config.NumberColumn(format="%g%%")})
            st.caption("A senior reviewer can change these under Administration > Evaluation criteria.")
        if crit_errors:
            st.error("This category's criteria are not valid, so it can't be evaluated yet: " + " ".join(crit_errors))

    # ------------------------------------------------------------------ suppliers
    rows = _rows()
    with st.container(border=True):
        h1, h2 = st.columns([3, 2], vertical_alignment="bottom")
        h1.markdown(f"##### Suppliers ({len(rows)})")
        h1.caption("Add one row per supplier. Submission date defaults to today. Accepted files: PDF, DOCX, DOC.")
        with h2:
            meta = samples.for_category(category["code"])
            demo = st.checkbox("Include error examples", key="ne_demo",
                               help="Adds a scanned PDF with no readable text"
                                    + (" and an incomplete proposal" if category["code"] == "OTHERS" else "")
                                    + ", to show how validation handles them.") if meta else False
            st.button("Load sample proposals", icon=":material/folder_open:", width="stretch",
                      disabled=not meta, on_click=_load_samples, args=(category["code"], demo),
                      help="Fill the rows with the bundled fictional proposals for this category.")

        for i, row in enumerate(rows):
            _supplier_row(i, row, today)

        f1, f2, f3 = st.columns([1.2, 2.2, 1])
        f1.button("Add supplier", icon=":material/add:", on_click=_add_row,
                  disabled=len(rows) >= config.MAX_SUPPLIERS)
        with f2.popover("Add several files at once", icon=":material/upload_file:"):
            bulk = st.file_uploader("Drop proposal files", type=list(config.ALLOWED_EXTENSIONS),
                                    accept_multiple_files=True, key="ne_bulk")
            seen = st.session_state.setdefault("ne_bulk_seen", set())
            added = 0
            for f in bulk or []:
                if f.file_id in seen:
                    continue
                seen.add(f.file_id)
                empty = next((r for r in rows if not r["file_bytes"] and not r["name"].strip()), None)
                data = dict(name=_guess_name(f.name), file_name=f.name, file_bytes=f.getvalue(), source="upload")
                if empty:
                    empty.update(data, name_v=empty.get("name_v", 0) + 1)
                elif len(rows) < config.MAX_SUPPLIERS:
                    rows.append(_new_row(**data))
                added += 1
            if added:
                st.rerun()
            st.caption("One row is created per file. Check the supplier names afterwards.")
        f3.button("Clear all", icon=":material/restart_alt:", on_click=_reset, width="stretch")

    # ------------------------------------------------------------------ engine + run
    s = llm_settings()
    with st.container(border=True):
        e1, e2 = st.columns([4, 1], vertical_alignment="center")
        if s.is_openai:
            e1.markdown(f"**Scoring engine:** OpenAI, model `{s.model}`. Each supplier is sent to the model "
                        "separately; files never leave this app except as extracted text.")
        else:
            e1.markdown("**Scoring engine:** Mock mode. Offline and free; scores are simulated for demonstration.")
        e2.button("Change engine", on_click=goto, args=("ai",), width="stretch")
        tr = tracing_settings()
        e1.caption(f"Tracing: on, LangSmith project “{tr.project}”." if tr.active else
                   "Tracing: off. Turn it on under Settings > Tracing to record this run in LangSmith.")
        with st.expander("Advanced options"):
            use_cache = st.checkbox("Reuse saved AI results for identical documents and criteria", value=True,
                                    help="Makes re-runs reproducible and avoids paying twice. Untick to force a "
                                         "fresh AI call.")
            names = [r["name"].strip() for r in rows if r["name"].strip()]
            inject = st.multiselect("Demo: corrupt the AI response for", names,
                                    help="Simulates a malformed AI response (out-of-range and non-numeric scores, a "
                                         "missing and an unknown criterion) so you can see validation repair it.")

    pending = st.session_state.get("ne_general_errors")
    if pending:
        st.error("Fix the following before evaluating:\n\n" + "\n".join(f"- {g}" for g in pending))
    ready = sum(1 for r in rows if r["file_bytes"])
    clicked = st.button(f"Evaluate {len(rows)} supplier{'s' if len(rows) != 1 else ''}", type="primary",
                        icon=":material/play_arrow:", disabled=bool(crit_errors))
    st.caption(f"{ready} of {len(rows)} rows have a file attached.")
    if not clicked:
        return

    # ------------------------------------------------------------------ validation
    general: list[str] = []
    title = (st.session_state.get("ne_title") or "").strip()
    reference = (st.session_state.get("ne_reference") or "").strip()
    note = (st.session_state.get("ne_note") or "").strip() if category["requires_note"] else ""
    if len(title) < 3:
        general.append("Enter an RFP title (at least 3 characters).")
    if reference and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._/\-]{0,39}", reference):
        general.append("RFP reference can contain letters, numbers, spaces and . _ / - only.")
    if category["requires_note"] and len(note) < 3:
        general.append("Describe the category (for example 'Facilities management').")
    if s.is_openai and not s.api_key:
        general.append("OpenAI is selected but no API key is set. Add one under Settings > AI engine.")
    payload = [{"supplier_name": r["name"], "submission_date": r["date"], "experience_rating": r["rating"],
                "file_name": r["file_name"], "file_bytes": r["file_bytes"]} for r in rows]
    valid, errors, row_errors = orchestrator.validate_inputs(payload, today=today)
    st.session_state[ERRORS] = {rows[i]["id"]: msgs for i, msgs in row_errors.items()}
    general += [e for e in errors if not e.startswith("Row ")]
    if row_errors:
        general.append(f"{len(row_errors)} supplier row(s) have problems. See the messages under each row.")
    st.session_state["ne_general_errors"] = general
    if general:
        st.rerun()

    bar = st.progress(0.0, text="Starting…")
    with st.status("Running the evaluation workflow…", expanded=True) as status:
        def progress(step: str, message: str, fraction: float) -> None:
            bar.progress(min(fraction, 1.0), text=message)
            status.write(message)

        try:
            final = orchestrator.run_evaluation(
                valid, user["username"], category, title, rfp_reference=reference, category_note=note,
                llm_settings=s, use_cache=use_cache, inject_malformed_for=inject, progress=progress,
                tracing=tracing_settings())
        except Exception as exc:  # unexpected failure, already recorded on the run
            status.update(label="The evaluation failed", state="error")
            st.exception(exc)
            return
        if final["status"] == "failed":
            status.update(label="The evaluation failed", state="error")
            st.error(final.get("error"))
            st.caption(f"Run {final['rfp_run_id']} was saved with status 'failed' so it appears in Run history.")
            return
        status.update(label=f"Evaluation {final['rfp_run_id']} complete", state="complete", expanded=False)
    _reset()
    goto("results", current_run=final["rfp_run_id"])
    st.rerun()
