"""Results: leaderboard, scorecards with evidence snippets, peer comparison and run details."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from rfp import db
from ui import charts
from ui.components import (ai_disclaimer, chip, empty_state, esc, fmt_date, fmt_dt, page_title, status_html)
from rfp.tracing import fetch_run_url
from ui.nav import goto, tracing_settings
from ui.snippets import evidence_dialog, snippet_html

FLAG_LABELS = {"clipped": "Score clipped to range", "non_numeric_score": "Non-numeric score set to 0",
               "rescaled": "Rescaled to max score", "imputed_missing": "Missing from AI output (scored 0)",
               "missing_evidence": "No evidence quoted", "missing_justification": "No justification",
               "matched_by_name": "Matched by name", "evidence_not_verified": "Evidence not found in document"}


def _run_picker(runs: list[dict]) -> str:
    cats = sorted({r["category_label"] for r in runs if r["category_label"]})
    requested = st.session_state.get("current_run")
    if requested and requested != st.session_state.get("res_run"):
        # navigated here for a specific run: show it whatever filter was selected before
        st.session_state["res_cat"] = "All categories"
        if any(r["rfp_run_id"] == requested for r in runs):
            st.session_state["res_run"] = requested
    a, b = st.columns([1, 2.4])
    cat = a.selectbox("Category", ["All categories", *cats], key="res_cat")
    shown = [r for r in runs if cat == "All categories" or r["category_label"] == cat]
    if not shown:
        shown = runs
    ids = [r["rfp_run_id"] for r in shown]
    current = st.session_state.get("current_run")
    by_id = {r["rfp_run_id"]: r for r in shown}
    if st.session_state.get("res_run") not in ids:
        st.session_state["res_run"] = current if current in ids else ids[0]
    run_id = b.selectbox(
        "Evaluation", ids, key="res_run",
        format_func=lambda i: f"{by_id[i]['rfp_title'] or 'Untitled'}  ({fmt_date(by_id[i]['created_at'])}, "
                              f"{by_id[i]['rfp_run_id']})")
    st.session_state.current_run = run_id
    return run_id


def render(user: dict) -> None:
    page_title("Results", "Ranking, scores and the evidence behind them.")
    runs = db.list_runs(500)
    if not runs:
        empty_state("No evaluations yet", "Run your first evaluation to see results here.")
        st.button("New evaluation", type="primary", on_click=goto, args=("new",))
        return
    run_id = _run_picker(runs)
    run = db.get_run(run_id)
    if not run:
        st.error("This evaluation no longer exists.")
        return
    if run["status"] == "failed" or not run.get("data"):
        st.error(f"This evaluation failed: {'; '.join(json.loads(run.get('warnings_json') or '[]'))}")
        return
    data = run["data"]
    mock = data["llm"]["mode"] == "mock"

    with st.container(border=True):
        h1, h2 = st.columns([3, 1.3])
        h1.markdown(f"### {esc(data.get('rfp_title') or 'Untitled RFP')}")
        cat = data.get("category", {})
        h1.markdown(" ".join(filter(None, [
            chip(cat.get("label", "")), chip(cat["note"]) if cat.get("note") else "",
            chip(data["rfp_reference"]) if data.get("rfp_reference") else "", status_html(data["status"])])),
            unsafe_allow_html=True)
        h2.markdown(f"<div style='font-size:.85rem;color:#5A6B70;text-align:right'>Run {esc(data['rfp_run_id'])}<br>"
                    f"{fmt_dt(data['created_at'])}<br>by {esc(data['created_by'])}, "
                    f"{'mock mode' if mock else 'OpenAI ' + esc(data['llm']['model'])}</div>",
                    unsafe_allow_html=True)
        with h2:
            _trace_link(run)
    ai_disclaimer(mock=mock)

    tabs = st.tabs(["Leaderboard", "Scorecards and evidence", "Peer comparison", "Run details"])
    with tabs[0]:
        _leaderboard(data)
    with tabs[1]:
        _scorecards(data)
    with tabs[2]:
        _comparison(data)
    with tabs[3]:
        _details(data)


def _trace_link(run: dict) -> None:
    """'View trace in LangSmith' for runs recorded with tracing on."""
    trace = json.loads(run.get("trace_json") or "null") or (run.get("data") or {}).get("tracing") or {}
    if not trace.get("enabled"):
        st.markdown("<div style='text-align:right;font-size:.8rem;color:#5A6B70'>Not traced</div>",
                    unsafe_allow_html=True)
        return
    if trace.get("url"):
        st.link_button("View trace in LangSmith", trace["url"], icon=":material/timeline:", width="stretch")
        return
    settings = tracing_settings()
    if st.button("Get LangSmith link", icon=":material/link:", width="stretch", key=f"trace_{run['rfp_run_id']}",
                 help=f"Trace {trace.get('trace_id')} in project {trace.get('project')}"):
        if not settings.api_key:
            st.error("Add your LangSmith key under Settings > Tracing first.")
            return
        url, err = fetch_run_url(settings, trace["trace_id"], trace["project"])
        if url:
            trace["url"], trace["error"] = url, None
            db.set_run_trace(run["rfp_run_id"], trace)
            st.rerun()
        st.error(err)


# ----------------------------------------------------------------------------------------------- leaderboard
def _leaderboard(data: dict) -> None:
    if not data["leaderboard"]:
        st.info("No supplier could be ranked in this run.")
        return
    top = data["suppliers"][0]
    runner = data["suppliers"][1] if len(data["suppliers"]) > 1 else None
    margin = f"{top['ppi'] - runner['ppi']:.2f} PPI ahead of {runner['supplier_name']}" if runner else ""
    tie = next((t for t in data["tie_break_explanations"] if t["higher"] == top["supplier_name"]
                and t["tie_break_used"]), None)
    why = tie["explanation"] if tie else (top["overall_summary"] or margin)
    st.markdown(
        f"""<div class="ri-winner"><div><div class="ri-medal">Ranked #1</div>
        <div class="who">{esc(top['supplier_name'])}</div><div class="why">{esc(why)}</div></div>
        <div class="nums"><div><b>{top['ppi']:.2f}</b><span>PPI</span></div>
        <div><b>{top['absolute_score']:.2f}</b><span>Absolute score</span></div></div></div>""",
        unsafe_allow_html=True)
    st.write("")
    lb = pd.DataFrame(data["leaderboard"]).rename(columns={
        "final_rank": "Rank", "supplier_name": "Supplier", "absolute_score": "Absolute score", "ppi": "PPI",
        "submission_date": "Submitted", "experience_rating": "Past performance"})
    left, right = st.columns([1.5, 1], gap="medium")
    with left:
        st.dataframe(lb, hide_index=True, width="stretch", column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "Absolute score": st.column_config.NumberColumn(format="%.2f", help="Σ (score / max) × weight"),
            "PPI": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.2f",
                                                   help="Peer Performance Index"),
            "Past performance": st.column_config.NumberColumn(format="%g"),
        })
    with right:
        st.altair_chart(charts.supplier_ppi_bars(lb), width="stretch")
    if data["excluded_suppliers"]:
        st.warning("**Not ranked**\n\n" + "\n".join(
            f"- **{e['supplier_name']}** ({e.get('file_name', '')}): {e['reason']}" for e in data["excluded_suppliers"]))
    used = [t for t in data["tie_break_explanations"] if t["tie_break_used"]]
    if used:
        st.info("**Tie-break applied**\n\n" + "\n".join(f"- {t['explanation']}" for t in used))


# ----------------------------------------------------------------------------------------------- scorecards
def _scorecards(data: dict) -> None:
    names = [s["supplier_name"] for s in data["suppliers"]]
    if not names:
        st.info("No scorecards in this run.")
        return
    name = st.segmented_control("Supplier", names, default=names[0], key=f"sc_{data['rfp_run_id']}",
                                format_func=lambda n: f"#{names.index(n) + 1} {n}") or names[0]
    s = next(x for x in data["suppliers"] if x["supplier_name"] == name)
    m = st.columns(4)
    m[0].metric("Rank", f"#{s['final_rank']}", border=True)
    m[1].metric("PPI", f"{s['ppi']:.2f}", border=True)
    m[2].metric("Absolute score", f"{s['absolute_score']:.2f}", border=True)
    m[3].metric("Submitted", fmt_date(s["submission_date"]), border=True,
                help=f"Past performance rating {s['experience_rating']:g}")
    if s["overall_summary"] or s["risks"]:
        with st.container(border=True):
            if s["overall_summary"]:
                st.markdown(f"**AI summary:** {s['overall_summary']}")
            if s["risks"]:
                st.markdown("**Risks identified:** " + "; ".join(s["risks"]))
    doc = s.get("document", {})
    st.caption(f"Source document: {s.get('file_name', '')}"
               + (f", {doc.get('pages')} pages" if doc.get("pages") else ""))

    for c in s["criteria"]:
        with st.container(border=True):
            left, right = st.columns([1, 1.45], gap="medium")
            with left:
                pct = c["score"] / c["max_score"] * 100 if c["max_score"] else 0
                lead = " · best in field" if c["is_benchmark_leader"] else ""
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;align-items:baseline'>"
                    f"<b>{esc(c['criterion_name'])}</b><span style='color:#5A6B70;font-size:.8rem'>weight "
                    f"{c['weight']:g}%</span></div><div class='ri-score'>{c['score']:g}"
                    f"<small> / {c['max_score']}</small></div><div class='ri-bar'><div style='width:{pct:.0f}%'>"
                    f"</div></div><div style='font-size:.8rem;color:#5A6B70'>Benchmark {c['benchmark_score']:g}, "
                    f"relative {c['relative_pct']:.1f}%, adds {c['weighted_points']:.2f} points{lead}</div>",
                    unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:.9rem;margin-top:8px'>{esc(c['justification'] or '—')}</div>",
                            unsafe_allow_html=True)
                if c["validation_flags"]:
                    st.markdown("".join(f"<span class='ri-flag'>{esc(FLAG_LABELS.get(f, f))}</span>"
                                        for f in c["validation_flags"]), unsafe_allow_html=True)
            with right:
                st.markdown("<div style='font-size:.8rem;color:#5A6B70;margin-bottom:4px'>Evidence in the "
                            "document</div>" + snippet_html(c.get("evidence_location"), c["evidence"]),
                            unsafe_allow_html=True)
                loc = c.get("evidence_location") or {}
                if loc.get("match_text") and st.button(
                        "Open in document", key=f"ev_{data['rfp_run_id']}_{name}_{c['criterion_id']}",
                        icon=":material/find_in_page:", type="tertiary"):
                    evidence_dialog(data["rfp_run_id"], name, c)
    if s["validation_warnings"]:
        with st.expander(f"Validation warnings for {name} ({len(s['validation_warnings'])})", expanded=True):
            st.markdown("\n".join(f"- {w}" for w in s["validation_warnings"]))
    with st.expander("Raw AI response"):
        st.caption(f"Source: {s['llm']['source']}, model {s['llm']['model']}"
                   + (". Malformed output was injected for the demo." if s["llm"]["fault_injected"] else ""))
        st.code(s["llm"]["raw_response"], language="json", wrap_lines=True)
    doc_row = db.get_document(data["rfp_run_id"], name)
    if doc_row:
        st.download_button("Download original document", bytes(doc_row["file_bytes"]),
                           file_name=doc_row["file_name"], icon=":material/download:",
                           key=f"dl_doc_{data['rfp_run_id']}_{name}")


# ----------------------------------------------------------------------------------------------- comparison
def _comparison(data: dict) -> None:
    sups = data["suppliers"]
    if not sups:
        st.info("Nothing to compare.")
        return
    crit_names = [c["name"] for c in data["criteria_snapshot"]]
    rows = [{"Supplier": s["supplier_name"], "Criterion": r["criterion_name"], "Score": r["score"],
             "Relative %": r["relative_pct"]} for s in sups for r in s["criteria"]]
    st.markdown("**Score by criterion**")
    st.caption("Numbers are AI scores; colour shows how close each score is to the best score for that criterion.")
    st.altair_chart(charts.relative_heatmap(pd.DataFrame(rows), crit_names, [s["supplier_name"] for s in sups]),
                    width="stretch")
    st.markdown("**Benchmarks**")
    b = pd.DataFrame([{"Criterion": x["criterion_name"], "Weight %": x["weight"], "Max": x["max_score"],
                       "Best score": x["benchmark_score"], "Best supplier(s)": ", ".join(x["leaders"])}
                      for x in data["benchmarks"]])
    st.dataframe(b, hide_index=True, width="stretch",
                 column_config={"Weight %": st.column_config.NumberColumn(format="%g%%")})
    with st.expander("Table view of all scores"):
        table = pd.DataFrame(rows).pivot(index="Supplier", columns="Criterion", values="Score")
        st.dataframe(table.reindex(columns=crit_names).reindex([s["supplier_name"] for s in sups]), width="stretch")


# ----------------------------------------------------------------------------------------------- run details
def _details(data: dict) -> None:
    a, b = st.columns([1, 1])
    with a:
        st.markdown(f"**Run ID:** `{data['rfp_run_id']}`  \n**Status:** {data['status'].replace('_', ' ')}  \n"
                    f"**Started:** {fmt_dt(data['created_at'])}  \n**Completed:** {fmt_dt(data['completed_at'])}  \n"
                    f"**Engine:** {data['llm']['mode']}, {data['llm']['model']}, prompt {data['llm']['prompt_version']}")
        export = dict(data)
        export.setdefault("disclaimer", "AI-generated assessment; verify before use.")
        st.download_button("Download full result (JSON)", json.dumps(export, indent=2),
                           file_name=f"{data['rfp_run_id']}.json", mime="application/json", type="primary",
                           icon=":material/download:")
    with b:
        st.markdown("**Tie-break order**")
        st.markdown("\n".join(f"{t}  " for t in data["tie_break_order"]))
    st.markdown("**Why each supplier is ranked where it is**")
    for t in data["tie_break_explanations"]:
        st.markdown(f"- {t['explanation']}" + (f" (tie-break rule {t['deciding_rule']})" if t["tie_break_used"]
                                                 else ""))
    st.markdown(f"**Warnings ({len(data['warnings'])})**")
    if data["warnings"]:
        st.dataframe(pd.DataFrame({"Warning": data["warnings"]}), hide_index=True, width="stretch")
    else:
        st.caption("None.")
    with st.expander("Criteria used for this run"):
        st.dataframe(pd.DataFrame(data["criteria_snapshot"]), hide_index=True, width="stretch")
    with st.expander("Formulas"):
        for k, v in data["formulas"].items():
            st.markdown(f"- **{k.replace('_', ' ').capitalize()}**: {v}")
    with st.expander("Agent log"):
        st.dataframe(pd.DataFrame(data["agent_log"]), hide_index=True, width="stretch")
