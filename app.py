"""RFP Insight - agentic supplier evaluation (Streamlit entry point).

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import os

import streamlit as st

from rfp import config

config.load_streamlit_secrets()  # secrets become the defaults for the AI engine and Tracing pages
# Tracing is switched on per run from the Tracing page, never globally; the secrets value only sets the default.
os.environ.setdefault("RFP_TRACING_DEFAULT", os.environ.get("LANGSMITH_TRACING", "true"))
os.environ["LANGSMITH_TRACING"] = "false"

from rfp import auth, db  # noqa: E402
from ui.components import app_footer, app_header, esc, inject_css, logo  # noqa: E402
from ui.nav import PAGES, current_page, llm_settings, sidebar  # noqa: E402
from ui.pages import admin, categories, criteria, dashboard, history, new_evaluation, results  # noqa: E402

st.set_page_config(page_title=config.APP_NAME, page_icon="📑", layout="wide", initial_sidebar_state="expanded")


@st.cache_resource
def _init_database() -> dict:
    return db.init_db()


INIT = _init_database()
inject_css()

ROUTES = {
    "dashboard": dashboard.render, "new": new_evaluation.render, "results": results.render,
    "history": history.render, "categories": categories.render, "criteria": criteria.render,
    "audit": admin.render_audit, "ai": admin.render_ai, "tracing": admin.render_tracing,
    "account": admin.render_account, "help": admin.render_help,
}


def login_screen() -> None:
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown(
            f"""<div class="ri-login-hero">{logo(44)}
<h2>Evaluate supplier proposals with evidence you can check.</h2>
<p>{esc(config.APP_NAME)} reads each RFP response, scores it against your category's criteria with an AI agent,
and ranks suppliers with transparent, repeatable formulas.</p>
<ul><li>Category-specific criteria with an audited change history</li>
<li>Every score linked to the passage it came from</li>
<li>PDF, Word and legacy Word documents</li></ul></div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.write("")
        st.markdown(f"### Sign in to {esc(config.APP_NAME)}")
        with st.form("login", border=True):
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            if st.form_submit_button("Sign in", type="primary", width="stretch"):
                user = auth.authenticate(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                st.error("The username or password is incorrect.")
        with st.expander("Demo accounts"):
            st.markdown(
                "| Role | Username | Can |\n|---|---|---|\n"
                "| Evaluator | `evaluator` | Run evaluations and view results |\n"
                "| Senior Reviewer | `reviewer` | Also change criteria and view the audit log |\n\n"
                "Initial passwords are `evaluator123` and `reviewer123` unless set in the app secrets. "
                "Change them under Settings > My account."
            )
        if INIT.get("backup"):
            st.info(f"The database was upgraded to the new format. Your previous database was kept as "
                    f"`{os.path.basename(INIT['backup'])}`.")
    app_footer()


def main() -> None:
    user = st.session_state.get("user")
    if not user:
        login_screen()
        return
    page = sidebar(user)
    group, meta = PAGES[page]
    s = llm_settings()
    app_header(user, group, meta.title, s.label, not s.is_openai)
    if meta.reviewer_only and not auth.can_edit_criteria(user):
        st.warning("This page is available to Senior Reviewers only.")
    else:
        ROUTES[page](user)
    app_footer()


main()
