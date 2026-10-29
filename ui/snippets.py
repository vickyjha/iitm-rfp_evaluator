"""Evidence snippets: highlighted text context and PDF page previews with the evidence highlighted."""
from __future__ import annotations

import re

import streamlit as st

from rfp import db
from ui.components import esc

_WORD = re.compile(r"\S+")
_MD_CHARS = {"*": "&#42;", "_": "&#95;", "`": "&#96;", "#": "&#35;", "[": "&#91;", "]": "&#93;", "|": "&#124;",
             "~": "&#126;", ">": "&gt;"}


def esc_block(text: str) -> str:
    """Escape text for an HTML block rendered through st.markdown: no markdown parsing, line breaks kept."""
    text = re.sub(r"\n{2,}", "\n", text.replace("\r", ""))
    out = esc(text)
    out = "".join(_MD_CHARS.get(ch, ch) for ch in out.replace("&gt;", ">")).replace("&amp;", "&amp;")
    out = re.sub(r"^(\s*)(\d+)\.", r"\1\2&#46;", out, flags=re.MULTILINE)
    return out.replace("\n", "<br>")


def snippet_html(loc: dict | None, evidence: str) -> str:
    """Context before + highlighted match + context after."""
    if not evidence:
        return '<div class="ri-snippet empty">No evidence was quoted for this score.</div>'
    if not loc or not loc.get("match_text"):
        return (f'<div class="ri-snippet"><mark>{esc_block(evidence)}</mark></div>'
                '<div class="ri-loc">This quote could not be located in the document. Review it manually.</div>')
    body = (f'{esc_block(loc["context_before"])}<mark>{esc_block(loc["match_text"])}</mark>'
            f'{esc_block(loc["context_after"])}')
    return f'<div class="ri-snippet">{body}</div><div class="ri-loc">{esc(location_text(loc))}</div>'


def location_text(loc: dict) -> str:
    parts = []
    if loc.get("page"):
        parts.append(f"Page {loc['page']}")
    if loc.get("section"):
        parts.append(f"section “{loc['section']}”")
    where = ", ".join(parts) if parts else "Location in document"
    ratio = loc.get("match_ratio") or 0
    quality = "exact match" if ratio >= 0.99 else (f"{ratio:.0%} of words matched" if ratio else "not matched")
    return f"{where} ({quality})"


@st.cache_data(show_spinner=False, max_entries=64)
def pdf_page_png(run_id: str, supplier: str, page_no: int, match_text: str) -> bytes | None:
    """Render a PDF page with the evidence highlighted. Cached per run/supplier/page/quote."""
    import pymupdf

    doc_row = db.get_document(run_id, supplier)
    if not doc_row or doc_row["file_type"] != "pdf":
        return None
    doc = pymupdf.open(stream=bytes(doc_row["file_bytes"]), filetype="pdf")
    try:
        if not 1 <= page_no <= doc.page_count:
            return None
        page = doc[page_no - 1]
        words = _WORD.findall(match_text)
        size = 6 if len(words) > 6 else max(1, len(words))
        rects = []
        for i in range(0, max(1, len(words) - size + 1), max(1, size // 2)):
            rects += page.search_for(" ".join(words[i:i + size]), quads=True)
        if not rects and words:
            rects = page.search_for(" ".join(words[:4]), quads=True)
        for q in rects:
            annot = page.add_highlight_annot(q)
            annot.set_colors(stroke=(1, 0.86, 0.3))
            annot.update()
        return page.get_pixmap(dpi=110).tobytes("png")
    finally:
        doc.close()


def document_context_html(text: str, loc: dict, radius: int = 700) -> str:
    """A larger window of the extracted text around the evidence (used for DOCX/DOC)."""
    start, end = loc.get("start") or 0, loc.get("end") or 0
    a, b = max(0, start - radius), min(len(text), end + radius)
    clean = lambda s: re.sub(r"\[Page \d+\]\n?", "", s).replace("## ", "")  # noqa: E731
    return (f'<div class="ri-snippet" style="max-height:520px">{"…" if a else ""}{esc_block(clean(text[a:start]))}'
            f'<mark>{esc_block(clean(text[start:end]))}</mark>{esc_block(clean(text[end:b]))}'
            f'{"…" if b < len(text) else ""}</div>')


@st.dialog("Evidence in the supplier document", width="large")
def evidence_dialog(run_id: str, supplier: str, criterion: dict) -> None:
    loc = criterion.get("evidence_location") or {}
    st.markdown(f"**{criterion['criterion_name']}**: {criterion['score']:g}/{criterion['max_score']} for "
                f"{supplier}")
    doc_row = db.get_document(run_id, supplier)
    if not doc_row:
        st.info("The original document isn't stored for this run.")
        return
    st.caption(f"{doc_row['file_name']}, {location_text(loc)}" if loc else doc_row["file_name"])
    if doc_row["file_type"] == "pdf" and loc.get("page"):
        png = pdf_page_png(run_id, supplier, int(loc["page"]), loc.get("match_text", ""))
        if png:
            st.image(png, caption=f"Page {loc['page']} with the quoted evidence highlighted", width="stretch")
            return
    if loc.get("match_text") and doc_row.get("extracted_text"):
        st.markdown(document_context_html(doc_row["extracted_text"], loc), unsafe_allow_html=True)
    else:
        st.info("The quoted evidence could not be located in this document.")
