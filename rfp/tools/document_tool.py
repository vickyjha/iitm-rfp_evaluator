"""Document Tool: validate supplier files and extract clean text from PDF, DOCX and legacy DOC.

* PDF  - PyMuPDF; repeated headers/footers and page numbers removed; "[Page n]" markers inserted.
* DOCX - python-docx; paragraphs and tables in reading order; headings marked with "## ".
* DOC  - antiword when installed, otherwise a built-in reader for the Word 97-2003 binary format.

The file type is detected from the file's content (magic bytes), not just its extension, so a renamed
file is caught before it reaches the LLM.
"""
from __future__ import annotations

import hashlib
import io
import re
import shutil
import struct
import subprocess
import zipfile
from collections import Counter

from langsmith import traceable

from rfp import config

_PAGE_NO = re.compile(r"^\s*(page\s*)?\d+(\s*(of|/)\s*\d+)?\s*$", re.IGNORECASE)
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
TYPE_LABELS = {"pdf": "PDF", "docx": "Word (.docx)", "doc": "Word 97-2003 (.doc)"}


class DocumentError(Exception):
    """Raised when a file is the wrong type, cannot be opened, or contains no usable text."""


# ============================================================================================ validation
def detect_type(data: bytes) -> str | None:
    """Return 'pdf', 'docx', 'doc' or None based on the file content."""
    if data[:1024].lstrip().startswith(b"%PDF"):
        return "pdf"
    if data[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" in z.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            return None
        return None
    if data[:8] == OLE_MAGIC:
        return "doc"
    return None


def check_file(file_name: str, data: bytes) -> tuple[str | None, list[str]]:
    """Validate an uploaded supplier file. Returns (detected_type, errors)."""
    errors: list[str] = []
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in config.ALLOWED_EXTENSIONS:
        errors.append(f"'{file_name}' is not a supported file type. Upload PDF, DOCX or DOC.")
        return None, errors
    if not data:
        errors.append(f"'{file_name}' is empty.")
        return None, errors
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        errors.append(f"'{file_name}' is {len(data) / 1048576:.1f} MB; the limit is {config.MAX_UPLOAD_MB} MB.")
    detected = detect_type(data)
    if detected is None:
        errors.append(f"'{file_name}' is not a valid {ext.upper()} file (its content doesn't match the extension).")
    elif detected != ext:
        errors.append(f"'{file_name}' has a .{ext} extension but is actually a {TYPE_LABELS[detected]} file. "
                      f"Rename it to .{detected}.")
    return detected, errors


# ============================================================================================ extraction
@traceable(name="document_tool.extract_text", run_type="tool")
def extract_text(data: bytes, file_name: str = "document.pdf") -> dict:
    """Return {'text','pages','chars','sha256','file_type','removed_boilerplate_lines','truncated'}."""
    file_type, errors = check_file(file_name, data)
    if errors:
        raise DocumentError(" ".join(errors))
    if file_type == "pdf":
        text, pages, removed = _pdf_text(data, file_name)
    elif file_type == "docx":
        text, pages, removed = _docx_text(data, file_name), None, 0
    else:
        text, pages, removed = _doc_text(data, file_name), None, 0

    body_chars = len(re.sub(r"\[Page \d+\]|#|\s", "", text))
    if body_chars < config.MIN_DOC_CHARS:
        hint = " It may be a scanned image; run OCR or upload a text-based file." if file_type == "pdf" else ""
        raise DocumentError(f"{file_name}: no readable text found ({body_chars} characters).{hint}")
    return {
        "text": text, "pages": pages, "chars": len(text), "file_type": file_type,
        "sha256": hashlib.sha256(data).hexdigest(), "removed_boilerplate_lines": removed,
        "truncated": len(text) > config.MAX_DOC_CHARS,
    }


def _pdf_text(data: bytes, file_name: str) -> tuple[str, int, int]:
    import pymupdf

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise DocumentError(f"{file_name}: could not be opened ({exc}).") from exc
    if doc.needs_pass:
        raise DocumentError(f"{file_name}: the PDF is password protected.")
    pages = [page.get_text("text", sort=True) for page in doc]
    doc.close()
    page_lines = [[ln.strip() for ln in p.splitlines() if ln.strip()] for p in pages]
    repeated: set[str] = set()
    if len(pages) > 1:
        counts = Counter(ln for lines in page_lines for ln in set(lines))
        repeated = {ln for ln, n in counts.items() if n == len(pages) and len(ln) < 160}
    out, removed = [], 0
    for i, lines in enumerate(page_lines, start=1):
        kept = []
        for ln in lines:
            if _PAGE_NO.match(ln) or ln in repeated:
                removed += 1
                continue
            kept.append(re.sub(r"\s+", " ", ln))
        out.append(f"[Page {i}]\n" + "\n".join(kept))
    return "\n\n".join(out).strip(), len(pages), removed


def _docx_text(data: bytes, file_name: str) -> str:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError(f"{file_name}: could not be opened as a Word document ({exc}).") from exc
    lines: list[str] = []
    body = document.element.body
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(child, document)
            text = " ".join(p.text.split())
            if not text:
                continue
            style = (p.style.name if p.style is not None else "") or ""
            if style.lower().startswith(("heading", "title")):
                lines.append(f"\n## {text}")
            elif style.lower().startswith("list"):
                lines.append(f"- {text}")
            else:
                lines.append(text)
        elif tag == "tbl":
            table = Table(child, document)
            for row in table.rows:
                cells, seen = [], set()
                for cell in row.cells:  # merged cells repeat; keep each once
                    if id(cell._tc) in seen:
                        continue
                    seen.add(id(cell._tc))
                    cells.append(" ".join(cell.text.split()))
                if any(cells):
                    lines.append(" | ".join(cells))
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------------- legacy .doc
def _doc_text(data: bytes, file_name: str) -> str:
    if shutil.which("antiword"):
        try:
            proc = subprocess.run(["antiword", "-w", "0", "-"], input=data, capture_output=True, timeout=60)
            if proc.returncode == 0 and proc.stdout.strip():
                return _clean_plain(proc.stdout.decode("utf-8", errors="replace"))
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        return _clean_plain(read_word97(data))
    except DocumentError as exc:
        raise DocumentError(f"{file_name}: {exc}") from exc
    except Exception as exc:  # malformed binary
        raise DocumentError(f"{file_name}: could not read this .doc file ({exc}). Save it as .docx or PDF and "
                            "upload again.") from exc


def _clean_plain(text: str) -> str:
    lines = [" ".join(ln.split()) for ln in text.splitlines()]
    out, blank = [], 0
    for ln in lines:
        blank = blank + 1 if not ln else 0
        if blank <= 1:
            out.append(ln)
    return "\n".join(out).strip()


def read_word97(data: bytes) -> str:
    """Extract the main document text from a Word 97-2003 .doc file ([MS-DOC] piece table)."""
    import olefile

    ole = olefile.OleFileIO(io.BytesIO(data))
    try:
        if not ole.exists("WordDocument"):
            raise DocumentError("this file is not a Word document.")
        word = ole.openstream("WordDocument").read()
        if struct.unpack_from("<H", word, 0)[0] != 0xA5EC:
            raise DocumentError("unrecognised Word file header.")
        flags = struct.unpack_from("<H", word, 0x0A)[0]
        if flags & 0x0100:
            raise DocumentError("the document is password protected.")
        table_name = "1Table" if flags & 0x0200 else "0Table"
        if not ole.exists(table_name):
            raise DocumentError("the document's text table is missing.")
        table = ole.openstream(table_name).read()
    finally:
        ole.close()

    ccp_text = struct.unpack_from("<i", word, 0x4C)[0]
    fc_clx, lcb_clx = struct.unpack_from("<II", word, 0x1A2)
    clx = table[fc_clx:fc_clx + lcb_clx]
    pos = 0
    while pos < len(clx) and clx[pos] == 0x01:          # skip Prc (property modifiers)
        pos += 3 + struct.unpack_from("<h", clx, pos + 1)[0]
    if pos >= len(clx) or clx[pos] != 0x02:
        raise DocumentError("the document's piece table could not be found.")
    lcb = struct.unpack_from("<I", clx, pos + 1)[0]
    plc = clx[pos + 5:pos + 5 + lcb]
    n = (len(plc) - 4) // 12
    cps = struct.unpack_from(f"<{n + 1}I", plc, 0)
    chunks, total = [], 0
    for i in range(n):
        pcd_off = 4 * (n + 1) + 8 * i
        fc = struct.unpack_from("<I", plc, pcd_off + 2)[0]
        count = cps[i + 1] - cps[i]
        if fc & 0x40000000:
            start = (fc & ~0x40000000) // 2
            raw = word[start:start + count].decode("cp1252", errors="replace")
        else:
            raw = word[fc:fc + 2 * count].decode("utf-16-le", errors="replace")
        chunks.append(raw)
        total += count
        if ccp_text and total >= ccp_text:
            break
    text = "".join(chunks)[:ccp_text] if ccp_text > 0 else "".join(chunks)
    text = re.sub(r"\x13[^\x14\x15]*\x14?", "", text)    # drop field instructions, keep results
    text = text.replace("\x15", "").replace("\x07\x07", "\n").replace("\x07", "\t")   # cell / row end marks
    text = text.replace("\x0b", "\n").replace("\x0c", "\n")
    text = text.replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0e-\x1f]", "", text)
    text = re.sub(r"\t+\n", "\n", text).replace("\t", " | ")
    return text
