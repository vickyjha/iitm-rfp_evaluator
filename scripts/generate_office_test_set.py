"""Generate the independent Office Supplies test set (for trying a real AI model).

    python scripts/generate_office_test_set.py

Writes data/sample_rfps/office_supplies_test/: the buyer's RFP brief (for reference, not for upload) and four
supplier proposals in PDF, DOCX and DOC (DOC needs LibreOffice; otherwise a DOCX is written instead).
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_samples import OUT_DIR, build_docx, build_pdf, docx_to_doc, mm  # noqa: E402
from sample_content_office_test import RFP_BRIEF, TEST_RFP, TEST_SUPPLIERS  # noqa: E402


def _mm(blocks):
    out = copy.deepcopy(blocks)
    for _, items in out:
        for i, b in enumerate(items):
            if b[0] == "table" and b[2]:
                items[i] = ("table", b[1], [w * mm for w in b[2]])
    return out


def main() -> None:
    target = OUT_DIR / "office_supplies_test"
    target.mkdir(parents=True, exist_ok=True)
    brief = {"name": TEST_RFP["buyer"], "tagline": f"Request for Proposal {TEST_RFP['reference']}",
             "submission_date": "Proposals due 28 October 2026", "accent": "#12303A", "sections": _mm(RFP_BRIEF)}
    build_pdf(brief, {**TEST_RFP, "buyer": "All bidders"}, target / "00_RFP_brief_Northgate.pdf")
    print("wrote 00_RFP_brief_Northgate.pdf")
    for s in TEST_SUPPLIERS:
        s = {**s, "sections": _mm(s["sections"])}
        if s["format"] == "pdf":
            path = target / f"{s['file']}.pdf"
            build_pdf(s, TEST_RFP, path)
        else:
            path = target / f"{s['file']}.docx"
            build_docx(s, TEST_RFP, path)
            if s["format"] == "doc" and docx_to_doc(path, target / f"{s['file']}.doc"):
                path.unlink()
                path = target / f"{s['file']}.doc"
        print("wrote", path.name)


if __name__ == "__main__":
    main()
