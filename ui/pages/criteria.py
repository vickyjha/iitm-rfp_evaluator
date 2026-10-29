"""Evaluation criteria per category. Senior reviewers can edit; every change is audited."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from rfp import auth, db
from ui.components import fmt_dt, page_title


def render(user: dict) -> None:
    page_title("Evaluation criteria", "Each category has its own criteria and weights. New evaluations always use "
                                      "the current set; past evaluations keep the set they were scored with.")
    cats = db.list_categories()
    by_id = {c["category_id"]: c for c in cats}
    cat_id = st.selectbox("Category", list(by_id), key="crit_cat",
                          format_func=lambda i: f"{by_id[i]['icon']}  {by_id[i]['label']}")
    is_reviewer = auth.can_edit_criteria(user)
    tab_edit, tab_hist = st.tabs(["Criteria", "Change history"])
    with tab_edit:
        _editor(user, cat_id, is_reviewer)
    with tab_hist:
        _history(cat_id)


def _editor(user: dict, cat_id: int, is_reviewer: bool) -> None:
    criteria = db.list_criteria(cat_id)
    df = pd.DataFrame(criteria)[["criterion_id", "name", "description", "weight", "max_score", "is_active",
                                 "updated_by", "updated_at"]]
    df["is_active"] = df["is_active"].astype(bool)
    df["updated_at"] = df["updated_at"].map(fmt_dt)
    cfg = {
        "criterion_id": st.column_config.NumberColumn("ID", width="small"),
        "name": st.column_config.TextColumn("Criterion", required=True, max_chars=60),
        "description": st.column_config.TextColumn("What the AI looks for", width="large", required=True,
                                                   max_chars=400),
        "weight": st.column_config.NumberColumn("Weight %", min_value=0, max_value=100, step=0.5, format="%g"),
        "max_score": st.column_config.NumberColumn("Max score", min_value=1, max_value=100, step=1),
        "is_active": st.column_config.CheckboxColumn("Active"),
        "updated_by": "Last changed by", "updated_at": "Last changed",
    }
    if not is_reviewer:
        st.info("Read-only. Only a Senior Reviewer can change criteria.", icon=":material/lock:")
        st.dataframe(df, hide_index=True, width="stretch", column_config=cfg)
        return

    st.caption("Edit cells directly. Criteria can't be deleted; untick Active instead so past runs stay traceable.")
    version = st.session_state.get(f"crit_v_{cat_id}", 0)
    edited = st.data_editor(df, hide_index=True, width="stretch", num_rows="fixed", column_config=cfg,
                            disabled=["criterion_id", "updated_by", "updated_at"], key=f"crit_ed_{cat_id}_{version}")
    staged = st.session_state.setdefault(f"crit_new_{cat_id}", [])
    with st.expander("Add a criterion"):
        with st.form(f"add_crit_{cat_id}", clear_on_submit=True):
            n = st.text_input("Name", max_chars=60)
            d = st.text_area("What the AI should look for", max_chars=400)
            c1, c2 = st.columns(2)
            w = c1.number_input("Weight %", 0.0, 100.0, 0.0, step=0.5)
            mx = c2.number_input("Max score", 1, 100, 10)
            if st.form_submit_button("Stage criterion"):
                if n.strip() and d.strip():
                    staged.append({"criterion_id": None, "name": n.strip(), "description": d.strip(), "weight": w,
                                   "max_score": int(mx), "is_active": 1})
                    st.rerun()
                else:
                    st.error("Enter a name and a description.")
    if staged:
        st.markdown("**New criteria to be added when you save**")
        st.dataframe(pd.DataFrame(staged).drop(columns=["criterion_id"]), hide_index=True, width="stretch")
        if st.button("Discard new criteria"):
            st.session_state[f"crit_new_{cat_id}"] = []
            st.rerun()

    proposed = [{"criterion_id": int(r.criterion_id), "name": r.name, "description": r.description,
                 "weight": float(r.weight or 0), "max_score": int(r.max_score or 0), "is_active": int(bool(r.is_active))}
                for r in edited.itertuples()] + staged
    total = sum(p["weight"] for p in proposed if p["is_active"])
    errs = db.validate_criteria_set(proposed)
    if errs:
        st.error(f"Active weights total {total:g}%. " + " ".join(errs))
    else:
        st.success(f"Active weights total {total:g}%.")
    reason = st.text_input("Reason for the change", key=f"crit_reason_{cat_id}", max_chars=300,
                           placeholder="Required. Stored in the change history.")
    if st.button("Save criteria", type="primary", disabled=bool(errs), icon=":material/save:"):
        if not reason.strip():
            st.error("Enter a reason for the change.")
            return
        try:
            res = db.save_criteria(cat_id, proposed, user["username"], reason)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.session_state[f"crit_new_{cat_id}"] = []
        st.session_state[f"crit_v_{cat_id}"] = version + 1
        st.session_state.pop(f"crit_reason_{cat_id}", None)
        st.toast(f"Saved {res['changes']} change(s)." if res["changes"] else "Nothing changed.", icon="✅")
        st.rerun()


def _history(cat_id: int) -> None:
    hist = db.list_criteria_history(cat_id)
    if not hist:
        st.caption("No changes yet. This category still uses its original criteria.")
        return
    h = pd.DataFrame(hist)
    who = st.multiselect("Reviewer", sorted(h["changed_by"].unique()), key=f"crit_who_{cat_id}")
    if who:
        h = h[h["changed_by"].isin(who)]
    h["changed_at"] = h["changed_at"].map(fmt_dt)
    st.dataframe(h[["changed_at", "changed_by", "criterion_name", "field_name", "old_value", "new_value", "reason"]]
                 .rename(columns={"changed_at": "When", "changed_by": "Reviewer", "criterion_name": "Criterion",
                                  "field_name": "Field", "old_value": "Old value", "new_value": "New value",
                                  "reason": "Reason"}), hide_index=True, width="stretch")
