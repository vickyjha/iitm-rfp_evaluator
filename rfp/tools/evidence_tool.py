"""Evidence Tool: find where an LLM's quoted evidence sits in the supplier document.

The quote is matched word by word (case and punctuation ignored), so small differences such as line breaks,
curly quotes or a dropped word still match. Each word of the quote "votes" for the place in the document
where it would line up; the place with the most votes wins. The share of matching words is the match ratio.

Returns the page (PDF), nearest section heading (DOCX/DOC), character offsets and surrounding context,
which the UI uses to show the snippet next to the score.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

_WORD = re.compile(r"[A-Za-z0-9]+")
_PAGE = re.compile(r"\[Page (\d+)\]")
_HEADING = re.compile(r"^(?:##\s*(.+)|(\d{1,2}\.\s+[A-Z][^\n.]{2,70}))$", re.MULTILINE)
VERIFIED_RATIO = 0.8
CONTEXT_CHARS = 280


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group().lower(), m.start(), m.end()) for m in _WORD.finditer(text)]


def _fragments(evidence: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\.\.\.|…|\||;|\n", evidence) if p.strip()]
    long_parts = [p for p in parts if len(_WORD.findall(p)) >= 3]
    return long_parts or [evidence]


def _best_alignment(doc_words: list[str], index: dict[str, list[int]], ev_words: list[str]) -> tuple[int, float]:
    votes: Counter = Counter()
    for i, w in enumerate(ev_words):
        for p in index.get(w, ()):
            votes[p - i] += 1
    if not votes:
        return -1, 0.0
    # highest votes; on ties prefer the earliest position (deterministic)
    start, count = min(votes.items(), key=lambda kv: (-kv[1], kv[0]))
    return start, count / len(ev_words)


def _snap(text: str, pos: int, direction: int) -> int:
    """Move a context boundary to the nearest whitespace so words aren't cut."""
    limit = 40
    while 0 < pos < len(text) and not text[pos].isspace() and limit:
        pos += direction
        limit -= 1
    return max(0, min(len(text), pos))


def locate(evidence: str, text: str) -> dict | None:
    """Locate evidence in text. Returns None when there is no evidence to look for."""
    if not evidence or not evidence.strip() or not text:
        return None
    doc_tokens = _tokens(text)
    if not doc_tokens:
        return None
    doc_words = [t[0] for t in doc_tokens]
    index: dict[str, list[int]] = defaultdict(list)
    for pos, w in enumerate(doc_words):
        index[w].append(pos)

    results = []
    for frag in _fragments(evidence):
        ev_words = [w.lower() for w in _WORD.findall(frag)]
        if not ev_words:
            continue
        start, ratio = _best_alignment(doc_words, index, ev_words)
        if start == -1:
            results.append((0.0, 0, 0))
            continue
        first = max(start, 0)
        last = min(start + len(ev_words) - 1, len(doc_tokens) - 1)
        results.append((ratio, doc_tokens[first][1], doc_tokens[last][2]))
    if not results:
        return None

    min_ratio = min(r[0] for r in results)
    best = max(results, key=lambda r: r[0])
    ratio, start_char, end_char = best
    if ratio == 0:
        return {"found": False, "match_ratio": 0.0, "page": None, "section": None, "start": None, "end": None,
                "context_before": "", "match_text": "", "context_after": ""}

    ctx_start = _snap(text, max(0, start_char - CONTEXT_CHARS), -1)
    ctx_end = _snap(text, min(len(text), end_char + CONTEXT_CHARS), 1)
    pages = [(m.start(), int(m.group(1))) for m in _PAGE.finditer(text)]
    page = next((n for pos, n in reversed(pages) if pos <= start_char), None)
    headings = [(m.start(), (m.group(1) or m.group(2)).strip()) for m in _HEADING.finditer(text)]
    section = next((h for pos, h in reversed(headings) if pos <= start_char), None)

    def clean(s: str) -> str:
        return _PAGE.sub("", s).replace("## ", "")

    return {
        "found": min_ratio >= VERIFIED_RATIO,
        "match_ratio": round(min_ratio, 3),
        "page": page,
        "section": section,
        "start": start_char,
        "end": end_char,
        "context_before": ("…" if ctx_start > 0 else "") + clean(text[ctx_start:start_char]),
        "match_text": clean(text[start_char:end_char]),
        "context_after": clean(text[end_char:ctx_end]) + ("…" if ctx_end < len(text) else ""),
    }
