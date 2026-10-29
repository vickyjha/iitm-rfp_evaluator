"""Audit log (senior reviewer), AI engine settings, account and help pages."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from rfp import auth, config, db
from rfp.agents import orchestrator
from rfp.llm import LLMSettings, RECOMMENDED_MODELS, friendly_error, list_models, test_connection
from rfp.tools import ranking_tool
from ui.components import fmt_dt, page_title
from rfp.tracing import ENDPOINTS, TracingSettings
from rfp.tracing import test_connection as test_tracing
from ui.nav import llm_settings, tracing_settings

EVENT_LABELS = {"login": "Sign-in", "password_change": "Password change"}


# =============================================================================================== audit log
def render_audit(user: dict) -> None:
    page_title("Audit log", "Sign-ins, password changes and criteria changes across all categories.")
    if not auth.can_edit_criteria(user):
        st.warning("Only a Senior Reviewer can view the audit log.")
        return
    t1, t2 = st.tabs(["Account activity", "Criteria changes"])
    with t1:
        ev = pd.DataFrame(db.list_events(500))
        if ev.empty:
            st.caption("No activity yet.")
        else:
            ev["Event"] = ev["event_type"].map(lambda e: EVENT_LABELS.get(e, e))
            ev["Result"] = ev["success"].map({1: "Succeeded", 0: "Failed"})
            ev["When"] = ev["event_at"].map(fmt_dt)
            st.dataframe(ev[["When", "username", "Event", "Result", "detail"]].rename(
                columns={"username": "User", "detail": "Detail"}), hide_index=True, width="stretch")
    with t2:
        hist = pd.DataFrame(db.list_criteria_history())
        if hist.empty:
            st.caption("No criteria changes yet.")
        else:
            hist["When"] = hist["changed_at"].map(fmt_dt)
            st.dataframe(hist[["When", "changed_by", "category_label", "criterion_name", "field_name", "old_value",
                               "new_value", "reason"]].rename(columns={
                "changed_by": "Reviewer", "category_label": "Category", "criterion_name": "Criterion",
                "field_name": "Field", "old_value": "Old value", "new_value": "New value", "reason": "Reason"}),
                hide_index=True, width="stretch")


# =============================================================================================== AI engine
def render_ai(user: dict) -> None:
    page_title("AI engine", "Choose how proposals are scored. Mock mode is free and offline; OpenAI gives real AI "
                            "assessments.")
    s = llm_settings()
    secrets_key = config.get("OPENAI_API_KEY") or ""
    mode = st.segmented_control("Scoring engine", ["Mock mode", "OpenAI"], key="ai_mode",
                                default="OpenAI" if s.is_openai else "Mock mode") or "Mock mode"

    if mode == "Mock mode":
        with st.container(border=True):
            st.markdown("**Mock mode** uses a built-in simulator. It returns realistic scores for the bundled sample "
                        "proposals and a simple keyword-based estimate for any other document. Nothing is sent "
                        "outside this app and there is no cost.")
            if st.button("Use mock mode", type="primary", disabled=not s.is_openai):
                st.session_state.llm = LLMSettings("mock", "mock-evaluator", s.api_key, s.key_source)
                st.toast("Mock mode selected.", icon="✅")
                st.rerun()
            if not s.is_openai:
                st.success("Mock mode is active.")
        return

    with st.container(border=True):
        st.markdown("**1. API key**")
        source = "session"
        key = ""
        if secrets_key:
            use_secret = st.toggle(f"Use the key from app secrets ({secrets_key[:3]}…{secrets_key[-4:]})",
                                   value=s.key_source != "session", key="ai_use_secret")
            if use_secret:
                key, source = secrets_key, "secrets"
        if not key:
            key = st.text_input("OpenAI API key", type="password", key="ai_key",
                                value=s.api_key if s.key_source == "session" else "", placeholder="sk-…",
                                help="Kept only in this browser session. It is never saved to the database or "
                                     "written to results.")
        st.caption("Your key stays in this browser session and is cleared when you sign out or close the tab.")
        load = st.button("Connect and load models", icon=":material/link:", disabled=not key)
        if load:
            with st.spinner("Checking the key and loading available models…"):
                try:
                    models = list_models(key)
                except Exception as exc:  # noqa: BLE001
                    st.session_state.pop("ai_models", None)
                    st.error(friendly_error(exc))
                else:
                    if not models:
                        st.error("The key works, but no chat models are available to it.")
                    st.session_state.ai_models = {"fp": key[-8:], "models": models}

    models_state = st.session_state.get("ai_models")
    if not key or not models_state or models_state["fp"] != key[-8:]:
        st.info("Connect with an API key to choose a model.")
        return

    models = models_state["models"]
    with st.container(border=True):
        st.markdown("**2. Model**")
        default = s.model if s.model in models else next((m for m in RECOMMENDED_MODELS if m in models), models[0])
        model = st.selectbox("Model", models, index=models.index(default), key="ai_model",
                             format_func=lambda m: f"{m}  (recommended)" if m in RECOMMENDED_MODELS[:2] else m,
                             help="Models that support chat and JSON output. gpt-4o-mini is fast and inexpensive.")
        st.caption(f"{len(models)} chat models available to this key.")
        c1, c2 = st.columns([1, 1])
        candidate = LLMSettings("openai", model, key, source)
        if c1.button("Test connection", icon=":material/network_check:", width="stretch"):
            with st.spinner(f"Sending a test request to {model}…"):
                ok, msg = test_connection(candidate)
            (st.success if ok else st.error)(msg)
        if c2.button("Use this model", type="primary", icon=":material/check:", width="stretch"):
            st.session_state.llm = candidate
            st.toast(f"Scoring with OpenAI {model}.", icon="✅")
            st.rerun()
    if s.is_openai:
        st.success(f"Active: OpenAI {s.model} (key from {'app secrets' if s.key_source == 'secrets' else 'this session'}).")


# =============================================================================================== tracing
def render_tracing(user: dict) -> None:
    page_title("Tracing", "Record every evaluation in LangSmith: each workflow step, tool call and AI request, "
                          "with inputs, outputs and timings. Each run in Results then links to its trace.")
    t = tracing_settings()
    secrets_key = config.get("LANGSMITH_API_KEY") or ""
    with st.container(border=True):
        enabled = st.toggle("Trace new evaluations in LangSmith", value=t.enabled, key="tr_enabled")
        c1, c2 = st.columns(2)
        project = c1.text_input("Project name", value=t.project, key="tr_project", max_chars=100,
                                help="Traces are grouped under this LangSmith project. It is created if missing.")
        regions = list(ENDPOINTS)
        current = next((k for k, v in ENDPOINTS.items() if v == t.endpoint), regions[0])
        region = c2.selectbox("Region", regions, index=regions.index(current), key="tr_region")
        source, key = "session", ""
        if secrets_key:
            if st.toggle(f"Use the key from app secrets ({secrets_key[:5]}…{secrets_key[-4:]})",
                         value=t.key_source != "session", key="tr_use_secret"):
                key, source = secrets_key, "secrets"
        if not key:
            key = st.text_input("LangSmith API key", type="password", key="tr_key", placeholder="lsv2_…",
                                value=t.api_key if t.key_source == "session" else "",
                                help="Kept only in this browser session; never saved to the database.")
        st.caption("Create a key in LangSmith under Settings > API Keys. Supplier files and OpenAI keys are never "
                   "sent to traces; extracted document text and AI responses are.")
        candidate = TracingSettings(enabled=enabled, api_key=key, project=project.strip() or "rfp-evaluator",
                                    endpoint=ENDPOINTS[region], key_source=source if key else "")
        b1, b2, _ = st.columns([1, 1, 2])
        if b1.button("Test connection", icon=":material/network_check:", disabled=not key, width="stretch"):
            with st.spinner("Contacting LangSmith…"):
                ok, msg = test_tracing(candidate)
            (st.success if ok else st.error)(msg)
        if b2.button("Save", type="primary", icon=":material/check:", width="stretch"):
            if enabled and not key:
                st.error("Add an API key to turn tracing on.")
            else:
                st.session_state.tracing = candidate
                st.toast("Tracing is on." if candidate.active else "Tracing is off.", icon="✅")
                st.rerun()
    t = tracing_settings()
    if t.active:
        st.success(f"Tracing is on. New evaluations are recorded in the project “{t.project}”.")
        st.link_button("Open LangSmith", t.web_url, icon=":material/open_in_new:")
    else:
        st.info("Tracing is off. Evaluations still run normally; they just aren't recorded in LangSmith.")


# =============================================================================================== account
def render_account(user: dict) -> None:
    page_title("My account", "Your profile and password.")
    fresh = db.get_user(user["username"]) or {}
    with st.container(border=True):
        a, b, c = st.columns(3)
        a.markdown(f"**Name**  \n{user['full_name']}")
        b.markdown(f"**Username**  \n{user['username']}")
        c.markdown(f"**Role**  \n{auth.ROLE_LABELS[user['role']]}")
        changed = fresh.get("password_changed_at")
        st.caption(f"Password last changed {fmt_dt(changed)}." if changed else
                   "You are still using the initial password. Change it now.")
    st.markdown("#### Change password")
    with st.form("pw_form", clear_on_submit=True, border=True):
        cur = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password",
                            help=f"At least {auth.MIN_PASSWORD_LENGTH} characters, with a letter and a number.")
        rep = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Change password", type="primary"):
            ok, msg = auth.change_password(user["username"], cur, new, rep)
            if ok:
                st.success("Password changed. Use the new password next time you sign in.")
            else:
                st.error(msg)


# =============================================================================================== help
def render_help(user: dict) -> None:
    page_title("How it works", "The workflow, formulas and rules behind every ranking.")
    st.markdown("""
The **Orchestrator** is a LangGraph workflow that calls each step in a fixed order. The AI only judges
proposal content, one supplier at a time; every number after that is calculated with fixed formulas.

| Step | Component | What it does |
|---|---|---|
| 1 | Orchestrator | Loads the active criteria for the chosen category and checks the weights total 100% |
| 2 | Document reader | Reads PDF, DOCX or DOC files; rejects wrong file types and scanned files with no text |
| 3 | Evaluation agent (AI) | Scores one supplier against each criterion, with a justification and a quoted piece of evidence |
| 4 | Validation | Repairs the AI output (missing, duplicate or out-of-range scores) and finds the quote in the document |
| 5–7 | Ranking | Weighted score, benchmarks and gaps, relative %, PPI, tie-breaks and ranks |
| 8 | Storage | Saves the run, results, original files and the full JSON under one run ID |
""")
    st.markdown("**Formulas**")
    for k, v in ranking_tool.FORMULAS.items():
        st.markdown(f"- **{k.replace('_', ' ').capitalize()}**: {v}")
    st.markdown("**Tie-break order**")
    st.markdown("\n".join(f"- {t}" for t in ranking_tool.TIE_BREAK_ORDER))
    st.markdown("**AI disclaimer**")
    st.markdown(f"> {orchestrator.AI_DISCLAIMER}")
    with st.expander("Workflow graph (Mermaid source)"):
        st.code(orchestrator.graph_mermaid(), language="text")
