"""Run history: every evaluation with filters."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from rfp import db
from ui.components import empty_state, page_title, status_label
from ui.nav import goto


def render(user: dict) -> None:
    page_title("Run history", "Every evaluation, including failed runs. Filter, then open one to see its results.")
    runs = db.list_runs(2000)
    if not runs:
        empty_state("No evaluations yet", "Runs appear here as soon as they finish.")
        return
    df = pd.DataFrame(runs)
    df["created"] = pd.to_datetime(df["created_at"]).dt.tz_localize(None)

    f = st.columns([1.4, 1, 1, 1.2])
    cats = f[0].multiselect("Category", sorted(df["category_label"].dropna().unique()), key="hist_cat")
    statuses = f[1].multiselect("Status", sorted(df["status"].unique()), format_func=status_label, key="hist_status")
    people = f[2].multiselect("Run by", sorted(df["created_by"].dropna().unique()), key="hist_user")
    lo, hi = df["created"].min().date(), df["created"].max().date()
    span = f[3].date_input("Date range", (lo, hi), min_value=lo, max_value=hi, format="DD/MM/YYYY", key="hist_dates")
    q = st.text_input("Search RFP title, reference or supplier", key="hist_q", placeholder="Type to filter…")

    view = df
    if cats:
        view = view[view["category_label"].isin(cats)]
    if statuses:
        view = view[view["status"].isin(statuses)]
    if people:
        view = view[view["created_by"].isin(people)]
    if isinstance(span, tuple) and len(span) == 2:
        view = view[(view["created"].dt.date >= span[0]) & (view["created"].dt.date <= span[1])]
    if q.strip():
        needle = q.strip().lower()
        view = view[view.apply(lambda r: needle in " ".join(str(r[c] or "") for c in
                                                            ("rfp_title", "rfp_reference", "winner")).lower(), axis=1)]

    table = view.assign(Status=view["status"].map(status_label))[
        ["rfp_title", "category_label", "Status", "created", "winner", "top_ppi", "ranked", "excluded", "created_by",
         "model", "trace_url", "rfp_run_id"]]
    table.columns = ["RFP", "Category", "Status", "Created (UTC)", "Rank #1", "Top PPI", "Ranked", "Excluded",
                     "Run by", "Model", "LangSmith trace", "Run ID"]
    st.caption(f"{len(table)} of {len(df)} runs")
    event = st.dataframe(table, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                         key="hist_table", column_config={
                             "Created (UTC)": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm"),
                             "Top PPI": st.column_config.NumberColumn(format="%.2f"),
                             "LangSmith trace": st.column_config.LinkColumn(display_text="Open trace",
                                                                            help="Runs recorded with tracing on")})
    selected = event.selection.rows if event and event.selection else []
    a, b = st.columns([1, 4])
    if selected:
        run_id = table.iloc[selected[0]]["Run ID"]
        a.button("Open results", type="primary", on_click=goto, args=("results",),
                 kwargs={"current_run": run_id}, width="stretch")
        b.caption(f"Selected {run_id}")
    else:
        a.button("Open results", disabled=True, width="stretch")
        b.caption("Select a row to open it.")
    st.download_button("Download this list (CSV)", table.to_csv(index=False), file_name="rfp_run_history.csv",
                       icon=":material/download:")
