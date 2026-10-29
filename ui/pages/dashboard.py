"""Dashboard: portfolio KPIs, charts and recent evaluations."""
from __future__ import annotations

from collections import Counter

import pandas as pd
import streamlit as st

from rfp import db
from rfp.demo import seed_demo_runs
from ui import charts
from ui.components import ai_disclaimer, empty_state, esc, fmt_dt, page_title, status_html
from ui.nav import goto, tracing_settings

FLAG_NAMES = {"clipped": "Score out of range", "non_numeric_score": "Non-numeric score",
              "rescaled": "Different score scale", "imputed_missing": "Criterion missing",
              "missing_evidence": "No evidence quoted", "missing_justification": "No justification",
              "matched_by_name": "Wrong criterion ID", "evidence_not_verified": "Evidence not found in document"}


def _issue_counts(runs: list[dict]) -> pd.DataFrame:
    counts: Counter = Counter()
    for r in runs:
        if r["status"] == "failed":
            continue
        run = db.get_run(r["rfp_run_id"])
        data = run.get("data") if run else None
        if not data:
            continue
        for s in data["suppliers"]:
            for c in s["criteria"]:
                for f in c["validation_flags"]:
                    counts[FLAG_NAMES.get(f, f)] += 1
        counts["Document unreadable / excluded"] += len(data["excluded_suppliers"])
    return pd.DataFrame([{"Issue": k, "Count": v} for k, v in counts.items() if v])


def render(user: dict) -> None:
    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    with c1:
        page_title(f"Welcome back, {user['full_name']}",
                   "Supplier evaluations across all procurement categories.")
    with c2:
        st.button("New evaluation", icon=":material/add:", type="primary", width="stretch", on_click=goto,
                  args=("new",), key="dash_new")

    runs = db.list_runs(1000)
    if not runs:
        empty_state("No evaluations yet",
                    "Start a new evaluation, or create one demo evaluation per category from the bundled sample "
                    "proposals. Demo runs use mock mode, so they cost nothing.")
        if st.button("Create demo evaluations", icon=":material/auto_awesome:", key="dash_seed"):
            with st.spinner("Evaluating the sample proposals in mock mode…"):
                seed_demo_runs(user["username"], tracing=tracing_settings())
            st.toast("Demo evaluations created.", icon="✅")
            st.rerun()
        return

    results = pd.DataFrame(db.supplier_results_table())
    ranked = results[results["status"] == "ranked"] if not results.empty else results
    done = [r for r in runs if r["status"] != "failed"]
    review = sum(1 for r in runs if r["status"] == "completed_with_warnings")
    failed = sum(1 for r in runs if r["status"] == "failed")

    k = st.columns(5)
    k[0].metric("RFPs evaluated", len(done), border=True,
                help="Completed runs, including those with warnings")
    k[1].metric("Supplier proposals scored", len(ranked), border=True)
    k[2].metric("Average suppliers per RFP", f"{len(ranked) / max(1, len(done)):.1f}", border=True)
    k[3].metric("Runs needing review", review, border=True, help="Completed with validation warnings")
    k[4].metric("Failed runs", failed, border=True)

    left, right = st.columns([1, 1], gap="medium")
    with left, st.container(border=True):
        st.markdown("**Evaluations by category**")
        by_cat = pd.DataFrame(done)["category_label"].value_counts().rename_axis("Category").reset_index(name="RFPs")
        st.altair_chart(charts.count_bars(by_cat, "Category", "RFPs", "RFPs evaluated"), width="stretch")
    with right, st.container(border=True):
        t = pd.DataFrame(runs)
        t["day"] = pd.to_datetime(t["created_at"]).dt.tz_localize(None).dt.normalize()
        span_days = (t["day"].max() - t["day"].min()).days
        if span_days > 30:
            st.markdown("**Evaluations per week**")
            t["period"] = t["day"].dt.to_period("W").dt.start_time
        else:
            st.markdown("**Evaluations per day**")
            t["period"] = t["day"]
        per = t.groupby("period").size().reset_index(name="Evaluations")
        st.altair_chart(charts.timeline(per, "period", "Evaluations", "Evaluations", weekly=span_days > 30),
                        width="stretch")

    if not ranked.empty:
        with st.container(border=True):
            st.markdown("**Supplier performance by category**")
            st.caption("Each dot is one supplier in one evaluation. Hover for details. PPI 100 means the supplier "
                       "matched the best score on every criterion.")
            st.altair_chart(charts.ppi_strip(ranked), width="stretch")
            ai_disclaimer(compact=True, text="PPI values are calculated from AI-generated criterion scores. "
                                             "Review the evidence before relying on them.")

    left, right = st.columns([1, 1], gap="medium")
    with left, st.container(border=True):
        st.markdown("**Top-ranked suppliers**")
        if ranked.empty:
            st.caption("No ranked suppliers yet.")
        else:
            top = (ranked[ranked["final_rank"] == 1].sort_values("created_at", ascending=False)
                   [["supplier_name", "category_label", "ppi", "rfp_title"]].head(8))
            top.columns = ["Supplier", "Category", "PPI", "RFP"]
            st.dataframe(top, hide_index=True, width="stretch",
                         column_config={"PPI": st.column_config.NumberColumn(format="%.1f", width="small"),
                                        "RFP": st.column_config.TextColumn(width="medium")})
    with right, st.container(border=True):
        st.markdown("**Validation issues found in AI output**")
        issues = _issue_counts(runs[:200])
        if issues.empty:
            st.caption("No issues found. Every AI response passed validation unchanged.")
        else:
            st.altair_chart(charts.count_bars(issues, "Issue", "Count", "Occurrences"), width="stretch")

    st.markdown("#### Recent evaluations")
    for r in runs[:6]:
        with st.container(border=True):
            a, b, c, d = st.columns([4, 2, 2, 1.2], vertical_alignment="center")
            a.markdown(f"**{esc(r['rfp_title'] or 'Untitled RFP')}**  \n"
                       f"<span style='color:#5A6B70;font-size:.85rem'>{esc(r['category_label'])}"
                       f"{' — ' + esc(r['rfp_reference']) if r['rfp_reference'] else ''}</span>",
                       unsafe_allow_html=True)
            b.markdown(status_html(r["status"]) + f"<br><span style='color:#5A6B70;font-size:.8rem'>"
                       f"{fmt_dt(r['created_at'])}</span>", unsafe_allow_html=True)
            c.markdown(f"Rank #1: **{esc(r['winner'] or '—')}**  \n"
                       f"<span style='color:#5A6B70;font-size:.8rem'>{r['ranked']} ranked"
                       f"{', ' + str(r['excluded']) + ' excluded' if r['excluded'] else ''}</span>",
                       unsafe_allow_html=True)
            d.button("Open", key=f"dash_open_{r['rfp_run_id']}", width="stretch", on_click=goto,
                     args=("results",), kwargs={"current_run": r["rfp_run_id"]})
