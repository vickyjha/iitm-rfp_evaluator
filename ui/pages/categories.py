"""Category insights: evaluations and results grouped by procurement category."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from rfp import db
from ui import charts
from ui.components import ai_disclaimer, esc, fmt_date, page_title, status_html
from ui.nav import goto


def render(user: dict) -> None:
    page_title("Category insights", "Evaluations and supplier results for each procurement category.")
    cats = db.list_categories()
    runs = db.list_runs(2000)
    counts = pd.Series([r["category_id"] for r in runs]).value_counts().to_dict() if runs else {}
    by_id = {c["category_id"]: c for c in cats}
    if "cat_pick" not in st.session_state:
        st.session_state.cat_pick = cats[0]["category_id"]
    cat_id = st.segmented_control(
        "Category", list(by_id), key="cat_pick", label_visibility="collapsed",
        format_func=lambda i: f"{by_id[i]['icon']} {by_id[i]['label']} ({counts.get(i, 0)})") or cats[0]["category_id"]
    cat = by_id[cat_id]
    st.caption(cat["description"])

    cat_runs = [r for r in runs if r["category_id"] == cat_id]
    results = pd.DataFrame([r for r in db.supplier_results_table() if r["category_id"] == cat_id])
    ranked = results[results["status"] == "ranked"] if not results.empty else results

    k = st.columns(4)
    k[0].metric("Evaluations", len(cat_runs), border=True)
    k[1].metric("Supplier proposals scored", len(ranked), border=True)
    k[2].metric("Average PPI", f"{ranked['ppi'].mean():.1f}" if not ranked.empty else "—", border=True)
    k[3].metric("Last evaluated", fmt_date(cat_runs[0]["created_at"]) if cat_runs else "—", border=True)

    if not cat_runs:
        with st.container(border=True):
            st.markdown(f"**No evaluations in {cat['label']} yet**")
            st.caption("Start one and choose this category. Sample proposals are available for it.")
            st.button("New evaluation", type="primary", on_click=goto, args=("new",),
                      kwargs={"ne_category": cat_id})
        _criteria(cat_id)
        return

    left, right = st.columns([1.3, 1], gap="medium")
    with left:
        st.markdown("#### Evaluations")
        for r in cat_runs:
            with st.container(border=True):
                a, b = st.columns([3, 1], vertical_alignment="center")
                a.markdown(f"**{esc(r['rfp_title'] or 'Untitled RFP')}**"
                           + (f" <span style='color:#5A6B70'>({esc(r['rfp_reference'])})</span>"
                              if r["rfp_reference"] else "")
                           + f"<br>{status_html(r['status'])} <span style='color:#5A6B70;font-size:.82rem'>"
                             f"&nbsp; {fmt_date(r['created_at'])}, {r['ranked']} ranked"
                           + (f", {r['excluded']} excluded" if r["excluded"] else "") + "</span>"
                           + (f"<br>Rank #1: <b>{esc(r['winner'])}</b> (PPI {r['top_ppi']:.2f})" if r["winner"]
                              else ""), unsafe_allow_html=True)
                b.button("Open", key=f"cat_open_{r['rfp_run_id']}", width="stretch", on_click=goto,
                         args=("results",), kwargs={"current_run": r["rfp_run_id"]})
                if r.get("trace_url"):
                    b.link_button("Trace", r["trace_url"], icon=":material/timeline:", width="stretch",
                                  help="Open this run's trace in LangSmith")
                if r["status"] != "failed":
                    with st.expander("Leaderboard"):
                        run = db.get_run(r["rfp_run_id"])
                        lb = pd.DataFrame(run["data"]["leaderboard"])[["final_rank", "supplier_name", "ppi",
                                                                      "absolute_score"]]
                        lb.columns = ["Rank", "Supplier", "PPI", "Absolute score"]
                        st.dataframe(lb, hide_index=True, width="stretch")
    with right:
        st.markdown("#### Supplier results")
        if ranked.empty:
            st.caption("No ranked suppliers yet.")
        else:
            best = (ranked.sort_values("ppi", ascending=False).groupby("supplier_name", as_index=False)
                    .agg(best_ppi=("ppi", "max"), evaluations=("rfp_run_id", "nunique"),
                         times_first=("final_rank", lambda s: int((s == 1).sum())))
                    .sort_values("best_ppi", ascending=False))
            best.columns = ["Supplier", "Best PPI", "RFPs", "#1 finishes"]
            st.dataframe(best, hide_index=True, width="stretch", column_config={
                "Best PPI": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                "RFPs": st.column_config.NumberColumn(width="small"),
                "#1 finishes": st.column_config.NumberColumn(width="small")})
            ai_disclaimer(compact=True, text="PPI is derived from AI-generated scores. Open an evaluation to check "
                                             "the evidence.")
        _criteria(cat_id)
    if not ranked.empty:
        with st.container(border=True):
            st.markdown("**Supplier PPI in each evaluation**")
            st.altair_chart(charts.ppi_strip(ranked.assign(category_label=ranked["rfp_title"].str.slice(0, 48))),
                            width="stretch")


def _criteria(cat_id: int) -> None:
    with st.expander("Current criteria for this category"):
        crit = db.list_criteria(cat_id, active_only=True)
        df = pd.DataFrame(crit)[["name", "weight", "max_score"]]
        df.columns = ["Criterion", "Weight %", "Max score"]
        st.dataframe(df, hide_index=True, width="stretch",
                     column_config={"Weight %": st.column_config.NumberColumn(format="%g%%")})
