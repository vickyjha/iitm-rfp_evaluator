"""Shared UI building blocks: global styles, header, footer, AI disclaimer, chips and formatting helpers."""
from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

from rfp import config
from rfp.auth import ROLE_LABELS

INK = "#12303A"        # header band, headings
TEAL = "#0F766E"       # primary actions
BRASS = "#B7791F"      # rank #1 marker - the one accent used for "winner"
MUTED = "#5A6B70"
LINE = "#D6DFDC"
SERIES = "#2a78d6"     # single-series chart colour
STATUS = {             # reserved status colours, always shown with an icon + label
    "completed": ("#1b7f4c", "Completed", "✓"),
    "completed_with_warnings": ("#b26a00", "Needs review", "!"),
    "failed": ("#c0392b", "Failed", "✕"),
    "running": ("#5A6B70", "Running", "…"),
}

CSS = f"""
<style>
:root {{ --ink:{INK}; --teal:{TEAL}; --brass:{BRASS}; --muted:{MUTED}; --line:{LINE}; }}
/* ---------- page frame: no empty band above the header ---------- */
.block-container, [data-testid="stMainBlockContainer"] {{ padding-top: 0 !important; padding-bottom: 0 !important;
  padding-left: 2rem; padding-right: 2rem; max-width: 1400px; }}
[data-testid="stHeaderActionElements"], .ri-title a, h1 a, h2 a, h3 a, h4 a {{ display: none !important; }}
/* style-only blocks take no space (otherwise each adds a 1rem gap above the header) */
div[data-testid="stElementContainer"]:has(> div > div > style),
div[data-testid="stElementContainer"]:has(style:only-child) {{ display: none !important; }}
/* footer sits at the bottom of short pages */
[data-testid="stMainBlockContainer"] > div[data-testid="stVerticalBlock"] {{ min-height: 100vh; }}
div[data-testid="stElementContainer"]:has(.ri-footer) {{ margin-top: auto; }}
@media (min-width: 768px) {{
  header[data-testid="stHeader"] {{ display: none; }}
  [data-testid="stSidebarHeader"] {{ display: none; }}
  section[data-testid="stSidebar"] {{ width: 228px !important; min-width: 228px !important; max-width: 228px !important; }}
}}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding: 0 0.75rem 1rem 0.75rem; }}
h1, h2, h3 {{ color: var(--ink); letter-spacing: -0.01em; }}
[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
[data-testid="stMetricLabel"] p {{ color: var(--muted); }}

/* ---------- app header ---------- */
/* one row at every width: items shrink and secondary text drops out instead of wrapping */
.ri-header, .ri-footer {{ background: var(--ink); color: #fff; border-radius: 10px; padding: 10px 18px;
  display: flex; align-items: center; gap: 16px; flex-wrap: nowrap; min-height: 56px; box-sizing: border-box; }}
.ri-header {{ margin-bottom: 18px; border-radius: 0 0 12px 12px; }}
/* keep the header pinned to the top while the page scrolls */
div[data-testid="stElementContainer"]:has(> div > div > div > .ri-header),
div[data-testid="stElementContainer"]:has(.ri-header) {{ position: sticky; top: 0; z-index: 990; }}
.ri-brand {{ display: flex; align-items: center; gap: 11px; flex: 0 0 auto; }}
.ri-brand svg {{ flex: none; }}
.ri-brand .name {{ font-size: 1.05rem; font-weight: 700; line-height: 1.15; white-space: nowrap; }}
.ri-brand .tag {{ font-size: 0.76rem; color: #B9CCD0; white-space: nowrap; }}
.ri-crumb {{ color: #CFE0E2; font-size: 0.84rem; flex: 1 1 auto; min-width: 0; text-align: center; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }}
.ri-crumb b {{ color: #fff; font-weight: 600; }}
.ri-right {{ display: flex; align-items: center; gap: 12px; flex: 0 0 auto; }}
.ri-pill {{ border: 1px solid rgba(255,255,255,.28); border-radius: 999px; padding: 3px 11px; font-size: 0.78rem;
  color: #fff; white-space: nowrap; }}
.ri-pill.mock {{ border-color: #E9B44C; color: #FFE3A8; }}
.ri-user {{ display: flex; align-items: center; gap: 8px; font-size: 0.84rem; line-height: 1.2; white-space: nowrap; }}
.ri-user .role {{ color: #B9CCD0; font-size: 0.74rem; }}
.ri-avatar {{ width: 30px; height: 30px; border-radius: 50%; background: #E8F2F1; color: var(--ink); flex: none;
  display: grid; place-items: center; font-weight: 700; font-size: 0.78rem; }}
@media (max-width: 1180px) {{ .ri-brand .tag, .ri-user .who {{ display: none; }} }}
@media (max-width: 900px) {{ .ri-crumb {{ display: none; }} .ri-header {{ justify-content: space-between; }} }}

/* ---------- page title ---------- */
.ri-title h1 {{ font-size: 1.65rem; margin: 0 0 2px 0; padding: 0; }}
.ri-title p {{ color: var(--muted); margin: 0 0 14px 0; max-width: 72ch; }}

/* ---------- AI disclaimer ---------- */
.ri-disclaimer {{ display: flex; gap: 10px; align-items: flex-start; border: 1px solid #E7CF9C; background: #FFF8EA;
  border-radius: 8px; padding: 9px 13px; font-size: 0.86rem; color: #5B4410; margin: 4px 0 12px 0; }}
.ri-disclaimer .icon {{ font-weight: 700; color: #9A6A00; }}
.ri-disclaimer.compact {{ padding: 6px 11px; font-size: 0.8rem; }}

/* ---------- chips & badges ---------- */
.ri-chip {{ display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 2px 10px;
  font-size: 0.8rem; font-weight: 500; border: 1px solid var(--line); background: #fff; color: var(--ink);
  white-space: nowrap; }}
.ri-status {{ display: inline-flex; align-items: center; gap: 6px; font-size: 0.82rem; font-weight: 600; }}
.ri-status .dot {{ width: 18px; height: 18px; border-radius: 50%; color: #fff; display: grid; place-items: center;
  font-size: 0.7rem; }}

/* ---------- winner card ---------- */
.ri-winner {{ border: 1px solid #E6D3AE; border-left: 6px solid var(--brass); background: #FFFCF5; border-radius: 10px;
  padding: 14px 18px; display: flex; justify-content: space-between; gap: 20px; flex-wrap: wrap; }}
.ri-winner .who {{ font-size: 1.3rem; font-weight: 700; color: var(--ink); }}
.ri-winner .why {{ color: var(--muted); font-size: 0.9rem; max-width: 70ch; }}
.ri-winner .nums {{ display: flex; gap: 26px; }}
.ri-winner .nums div {{ text-align: right; }}
.ri-winner .nums b {{ display: block; font-size: 1.4rem; font-variant-numeric: tabular-nums; color: var(--ink); }}
.ri-winner .nums span {{ font-size: 0.78rem; color: var(--muted); }}
.ri-medal {{ color: var(--brass); font-weight: 700; font-size: 0.8rem; }}

/* ---------- evidence snippet ---------- */
.ri-snippet {{ background: #FBFCFC; border: 1px solid var(--line); border-radius: 8px; padding: 10px 13px;
  font-size: 0.86rem; line-height: 1.55; color: #33464B; max-height: 240px; overflow: auto; }}
.ri-snippet mark {{ background: #FFE58A; color: #1d1d1d; padding: 1px 2px; border-radius: 3px; }}
.ri-snippet.empty {{ color: var(--muted); font-style: italic; }}
.ri-loc {{ font-size: 0.78rem; color: var(--muted); margin-top: 4px; }}
.ri-score {{ font-size: 1.35rem; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; }}
.ri-score small {{ font-size: 0.85rem; color: var(--muted); font-weight: 500; }}
.ri-bar {{ height: 6px; background: #E4EBE9; border-radius: 4px; overflow: hidden; margin: 6px 0 4px 0; }}
.ri-bar > div {{ height: 100%; background: var(--teal); border-radius: 4px; }}
.ri-flag {{ display: inline-block; font-size: 0.74rem; border-radius: 4px; padding: 1px 7px; margin: 2px 4px 0 0;
  background: #FDEEDC; color: #8A4B00; border: 1px solid #F3D3AA; }}

/* ---------- sidebar navigation (dark, matches header and footer) ---------- */
[data-testid="stSidebar"] {{ border-right: none; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.3rem; }}
[data-testid="stSidebar"] .stButton button {{ justify-content: flex-start; text-align: left; padding: 0.25rem 0.65rem;
  min-height: 2.05rem; border-radius: 7px; border: none; background: transparent; color: #C9DADD; }}
[data-testid="stSidebar"] .stButton button > div {{ justify-content: flex-start; width: 100%; }}
[data-testid="stSidebar"] .stButton button p {{ font-size: 0.88rem; }}
[data-testid="stSidebar"] .stButton button:hover {{ background: rgba(255,255,255,.08); color: #FFFFFF; }}
[data-testid="stSidebar"] .stButton button[kind="primary"] {{ background: rgba(94,208,192,.16); color: #FFFFFF;
  font-weight: 600; box-shadow: inset 3px 0 0 #5ED0C0; }}
[data-testid="stSidebar"] [data-testid="stExpander"] details {{ border: none; background: transparent; }}
[data-testid="stSidebar"] details summary {{ padding: 0.4rem 0.65rem; border-radius: 7px; }}
[data-testid="stSidebar"] details summary:hover {{ background: rgba(255,255,255,.06); }}
[data-testid="stSidebar"] details summary p {{ font-weight: 600; color: #FFFFFF; font-size: 0.88rem; }}
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {{ padding: 0 0 0.3rem 0.5rem; }}
[data-testid="stSidebar"] hr {{ border-color: #24505D; margin: 0.6rem 0; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ color: #9FB7BC; font-size: 0.76rem; }}
.ri-side-brand {{ display: flex; gap: 10px; align-items: center; height: 56px; margin: 0 0 10px 4px;
  border-bottom: 1px solid #24505D; }}
.ri-side-brand .name {{ font-weight: 700; color: #FFFFFF; font-size: 1rem; line-height: 1.15; }}
.ri-side-brand .tag {{ font-size: 0.72rem; color: #9FB7BC; }}
.ri-side-section {{ font-size: 0.7rem; color: #7F9CA2; margin: 6px 0 2px 10px; }}
[data-testid="stPopoverBody"] .stButton button {{ justify-content: flex-start; padding: 0.25rem 0.7rem; }}
[data-testid="stPopoverBody"] .stButton button > div {{ justify-content: flex-start; width: 100%; }}
[data-testid="stPopoverBody"] .stButton button[kind="primary"] {{ background: #E1F0EE; color: var(--teal); border: none;
  font-weight: 600; box-shadow: inset 3px 0 0 var(--teal); }}
[data-testid="stPopoverBody"] .stButton button[kind="tertiary"]:hover {{ background: #F0F4F3; }}

/* ---------- footer ---------- */
.ri-footer {{ margin-top: 36px; border-radius: 12px 12px 0 0; justify-content: space-between; font-size: 0.8rem;
  color: #CFE0E2; }}
.ri-footer .brand {{ display: flex; align-items: center; gap: 10px; white-space: nowrap; }}
.ri-footer b {{ color: #fff; font-weight: 600; }}
.ri-footer .mid {{ flex: 1 1 auto; text-align: center; min-width: 0; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; }}
.ri-footer .links {{ white-space: nowrap; }}
.ri-footer .links span + span {{ margin-left: 14px; }}
@media (max-width: 1180px) {{ .ri-footer .links {{ display: none; }} }}
@media (max-width: 760px) {{ .ri-footer .mid {{ display: none; }} }}

/* ---------- login ---------- */
.ri-login-hero {{ background: var(--ink); color: #fff; border-radius: 14px; padding: 34px 32px; min-height: 420px; }}
.ri-login-hero h2 {{ color: #fff; font-size: 1.9rem; line-height: 1.2; margin: 18px 0 10px 0; }}
.ri-login-hero p {{ color: #C9DADD; max-width: 46ch; }}
.ri-login-hero ul {{ padding-left: 1.1rem; color: #E6F0F1; line-height: 1.9; }}
</style>
"""

LOGO = """<svg width="{s}" height="{s}" viewBox="0 0 32 32" aria-hidden="true">
<rect x="1" y="1" width="30" height="30" rx="8" fill="{bg}"/>
<path d="M9 22V10h6.2c2.6 0 4.3 1.5 4.3 3.8 0 1.7-1 2.9-2.5 3.4L20 22h-3.2l-2.7-4.5H12V22z M12 15.1h3
c1 0 1.6-.5 1.6-1.3s-.6-1.3-1.6-1.3h-3z" fill="{fg}"/>
<circle cx="23.5" cy="21.5" r="2.6" fill="#E3B04B"/></svg>"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def logo(size: int = 34, bg: str = "#E8F2F1", fg: str = INK) -> str:
    return LOGO.format(s=size, bg=bg, fg=fg)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    return (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper() if parts else "?"


def app_header(user: dict, section: str, page: str, engine_label: str, is_mock: bool) -> None:
    st.markdown(
        f"""<div class="ri-header" role="banner">
  <div class="ri-brand">{logo(34)}<div><div class="name">{esc(config.APP_NAME)}</div>
    <div class="tag">{esc(config.APP_TAGLINE)}</div></div></div>
  <div class="ri-crumb">{esc(section)} / <b>{esc(page)}</b></div>
  <div class="ri-right">
    <span class="ri-pill {'mock' if is_mock else ''}" title="Scoring engine">{esc(engine_label)}</span>
    <span class="ri-user" title="{esc(user['full_name'])} ({esc(ROLE_LABELS[user['role']])})">
      <span class="ri-avatar">{esc(initials(user['full_name']))}</span>
      <span class="who">{esc(user['full_name'])}<br><span class="role">{esc(ROLE_LABELS[user['role']])}</span></span>
    </span>
  </div></div>""",
        unsafe_allow_html=True,
    )


def page_title(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="ri-title"><h1>{esc(title)}</h1>'
                + (f"<p>{esc(subtitle)}</p>" if subtitle else "") + "</div>", unsafe_allow_html=True)


def app_footer() -> None:
    year = datetime.now().year
    st.markdown(
        f"""<div class="ri-footer" role="contentinfo">
  <div class="brand">{logo(26)}<span><b>{esc(config.APP_NAME)}</b> v{esc(config.APP_VERSION)}
    &nbsp;&copy; {year} Procurement Analytics</span></div>
  <div class="mid">AI-assisted scoring. Final decisions need human review.</div>
  <div class="links"><span>Streamlit</span><span>LangGraph</span><span>OpenAI</span><span>SQLite</span></div>
</div>""",
        unsafe_allow_html=True,
    )


def ai_disclaimer(text: str | None = None, compact: bool = False, mock: bool = False) -> None:
    if text is None:
        text = ("Mock mode: these scores come from the offline simulator, not an AI model. Use them for "
                "demonstration only.") if mock else (
            "AI-generated content. Scores, justifications and evidence were produced by a language model and can be "
            "incomplete or wrong. Check them against the supplier documents before you make a decision.")
    st.markdown(f'<div class="ri-disclaimer {"compact" if compact else ""}" role="note">'
                f'<span class="icon">AI</span><span>{esc(text)}</span></div>', unsafe_allow_html=True)


def status_html(status: str) -> str:
    color, label, icon = STATUS.get(status, ("#5A6B70", status, "•"))
    return (f'<span class="ri-status" style="color:{color}"><span class="dot" style="background:{color}">{icon}'
            f"</span>{esc(label)}</span>")


def status_label(status: str) -> str:
    return STATUS.get(status, ("", status, ""))[1]


def chip(text: str) -> str:
    return f'<span class="ri-chip">{esc(text)}</span>'


def fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M UTC")
    except ValueError:
        return iso


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except ValueError:
        return iso


def empty_state(title: str, body: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(body)


# Icon rail used when the menu is collapsed: narrow sidebar, icon-only buttons centred, labels in tooltips/popovers.
COMPACT_CSS = """
<style>
@media (min-width: 768px) {
  html body section[data-testid="stSidebar"] { width: 72px !important; min-width: 72px !important; max-width: 72px !important; }
}
html body [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding: 0 0.5rem 1rem 0.5rem; }
html body [data-testid="stSidebar"] .stButton button, html body [data-testid="stSidebar"] [data-testid="stPopover"] button {
  justify-content: center !important; padding: 0.35rem 0 !important; min-height: 2.3rem; }
html body [data-testid="stSidebar"] .stButton button > div { justify-content: center !important; }
html body [data-testid="stSidebar"] [data-testid="stPopover"] button div[aria-hidden="true"] { display: none; }
html body [data-testid="stSidebar"] [data-testid="stPopover"] button > div { justify-content: center; width: 100%; }
html body [data-testid="stSidebar"] .stButton button [data-testid="stIconMaterial"],
html body [data-testid="stSidebar"] [data-testid="stPopover"] button [data-testid="stIconMaterial"] { font-size: 1.3rem; }
html body [data-testid="stSidebar"] [data-testid="stPopover"] button { background: transparent; border: none;
  color: #C9DADD; }
html body [data-testid="stSidebar"] [data-testid="stPopover"] button[kind="primary"] {
  background: rgba(94,208,192,.16); color: #FFFFFF; box-shadow: inset 3px 0 0 #5ED0C0; }
html body [data-testid="stSidebar"] [data-testid="stPopover"] button:hover { background: rgba(255,255,255,.08);
  color: #FFFFFF; }
html body [data-testid="stSidebar"] [data-testid="stPopover"], html body [data-testid="stSidebar"] [data-testid="stPopover"] > div,
html body [data-testid="stSidebar"] [data-testid="stPopover"] button { width: 100% !important; min-width: 52px; }
.ri-side-logo { display: flex; justify-content: center; align-items: center; height: 56px; margin: 0 0 10px 0;
  border-bottom: 1px solid #24505D; }
.ri-side-logo svg { width: 32px; height: 32px; flex: none; }
</style>
"""


def inject_compact_css() -> None:
    st.markdown(COMPACT_CSS, unsafe_allow_html=True)
