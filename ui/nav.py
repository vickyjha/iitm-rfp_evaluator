"""Sidebar accordion navigation and page routing helpers."""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from rfp import auth, config
from rfp.llm import LLMSettings, default_settings
from rfp.tracing import TracingSettings, default_tracing
from ui.components import esc, logo


@dataclass(frozen=True)
class Page:
    key: str
    title: str
    icon: str
    reviewer_only: bool = False


GROUPS: list[tuple[str, str, list[Page]]] = [
    ("Overview", ":material/space_dashboard:", [Page("dashboard", "Dashboard", ":material/space_dashboard:")]),
    ("Evaluations", ":material/fact_check:", [
        Page("new", "New evaluation", ":material/add_circle:"),
        Page("results", "Results", ":material/leaderboard:"),
        Page("history", "Run history", ":material/history:"),
    ]),
    ("Categories", ":material/category:", [Page("categories", "Category insights", ":material/category:")]),
    ("Administration", ":material/admin_panel_settings:", [
        Page("criteria", "Evaluation criteria", ":material/tune:"),
        Page("audit", "Audit log", ":material/policy:", reviewer_only=True),
    ]),
    ("Settings", ":material/settings:", [
        Page("ai", "AI engine", ":material/smart_toy:"),
        Page("tracing", "Tracing", ":material/timeline:"),
        Page("account", "My account", ":material/manage_accounts:"),
    ]),
    ("Help", ":material/help:", [Page("help", "How it works", ":material/menu_book:")]),
]
PAGES = {p.key: (group, p) for group, _, pages in GROUPS for p in pages}


def current_page() -> str:
    page = st.session_state.get("page") or st.query_params.get("page") or "dashboard"
    return page if page in PAGES else "dashboard"


def goto(page: str, **state) -> None:
    """Navigate to a page (call from a button callback or followed by st.rerun())."""
    st.session_state.page = page
    st.query_params["page"] = page
    for k, v in state.items():
        st.session_state[k] = v


def llm_settings() -> LLMSettings:
    if "llm" not in st.session_state:
        st.session_state.llm = default_settings()
    return st.session_state.llm


def tracing_settings() -> TracingSettings:
    if "tracing" not in st.session_state:
        st.session_state.tracing = default_tracing()
    return st.session_state.tracing


def _toggle_compact() -> None:
    st.session_state.nav_compact = not st.session_state.get("nav_compact", False)


def _sign_out() -> None:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.query_params.clear()


def sidebar(user: dict) -> str:
    active = current_page()
    is_reviewer = auth.can_edit_criteria(user)
    compact = st.session_state.get("nav_compact", False)
    groups = [(g, icon, [p for p in pages if is_reviewer or not p.reviewer_only]) for g, icon, pages in GROUPS]
    groups = [(g, icon, pages) for g, icon, pages in groups if pages]
    with st.sidebar:
        if compact:
            _rail(groups, active)
        else:
            _full(groups, active)
    return active


def _full(groups, active: str) -> None:
    st.markdown(f'<div class="ri-side-brand">{logo(32)}<div class="name">{esc(config.APP_NAME)}</div></div>',
                unsafe_allow_html=True)
    for group, icon, pages in groups:
        if len(pages) == 1 and group == "Overview":
            p = pages[0]
            st.button(p.title, key=f"nav_{p.key}", icon=p.icon, width="stretch",
                      type="primary" if p.key == active else "tertiary", on_click=goto, args=(p.key,))
            continue
        with st.expander(group, expanded=any(p.key == active for p in pages), icon=icon):
            for p in pages:
                st.button(p.title, key=f"nav_{p.key}", icon=p.icon, width="stretch",
                          type="primary" if p.key == active else "tertiary", on_click=goto, args=(p.key,))
    st.divider()
    s = llm_settings()
    st.caption(f"Engine: {s.label}  \n{tracing_settings().label}")
    st.button("Sign out", icon=":material/logout:", width="stretch", key="nav_signout", on_click=_sign_out)
    st.button("Collapse menu", key="nav_collapse", icon=":material/keyboard_double_arrow_left:", width="stretch",
              help="Show icons only", on_click=_toggle_compact)


def _rail(groups, active: str) -> None:
    """Collapsed menu: one icon per group. Single pages open directly; groups open a small menu."""
    from ui.components import inject_compact_css

    inject_compact_css()
    st.markdown(f'<div class="ri-side-logo">{logo(32)}</div>', unsafe_allow_html=True)
    for group, icon, pages in groups:
        in_group = any(p.key == active for p in pages)
        if len(pages) == 1:
            p = pages[0]
            st.button("", key=f"rail_{p.key}", icon=p.icon, help=p.title, width="stretch",
                      type="primary" if in_group else "tertiary", on_click=goto, args=(p.key,))
            continue
        with st.popover("", icon=icon, help=group, width="stretch", type="primary" if in_group else "tertiary"):
            st.markdown(f"**{group}**")
            for p in pages:
                st.button(p.title, key=f"rail_{p.key}", icon=p.icon, width="stretch",
                          type="primary" if p.key == active else "tertiary", on_click=goto, args=(p.key,))
    st.divider()
    st.button("", key="rail_signout", icon=":material/logout:", help="Sign out", width="stretch", type="tertiary",
              on_click=_sign_out)
    st.button("", key="nav_expand", icon=":material/keyboard_double_arrow_right:", type="tertiary",
              help="Expand menu", on_click=_toggle_compact, width="stretch")
