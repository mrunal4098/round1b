# app/pdf_loader.py
import fitz                       # PyMuPDF
from dataclasses import dataclass
from typing import List

# ───────── your existing Line dataclass (already defined in app/layout.py) ────
from .layout import Line          # <- page, text, x0, y0, x1, y1, avg_size, bold_frac

# ───────── page / document containers ────────────────────────────────────────
@dataclass
class PageContext:
    index:   int
    width:   float
    height:  float
    raw_dict: dict                 # original PyMuPDF dict
    lines:   List[Line]           # fully flattened line list

@dataclass
class DocumentContext:
    path:       str
    page_count: int
    pages:      List[PageContext]

# ───────── helper to flatten PyMuPDF blocks→lines→spans into Line objects ────
def _extract_lines(page_dict: dict, page_index: int) -> List[Line]:
    out: List[Line] = []
    for blk in page_dict.get("blocks", []):
        for ln in blk.get("lines", []):
            spans = ln.get("spans", [])
            if not spans:
                continue
            # concatenate all span texts in logical order
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue

            # average font size, bold fraction
            avg_size  = sum(s["size"] for s in spans) / len(spans)
            bold_frac = sum(1 for s in spans if (s["flags"] & 2)) / len(spans)

            # bounding box coordinates
            x0 = min(s["bbox"][0] for s in spans)
            y0 = min(s["bbox"][1] for s in spans)
            x1 = max(s["bbox"][2] for s in spans)
            y1 = max(s["bbox"][3] for s in spans)

            out.append(
                Line(
                    page      = page_index,
                    text      = text,
                    x0        = x0,
                    y0        = y0,
                    x1        = x1,
                    y1        = y1,
                    spans     = spans,
                    font_sizes= [s["size"] for s in spans],
                    primary_font = spans[0].get("font", "") if spans else "",
                    avg_size  = avg_size,
                    bold_frac = bold_frac,
                )
            )
    # Sort by vertical coordinate so later logic sees top-to-bottom order
    out.sort(key=lambda l: (l.page, l.y0))
    return out

# ───────── public loader ─────────────────────────────────────────────────────
def load_document(pdf_path: str) -> DocumentContext:
    doc   = fitz.open(pdf_path)
    pages = []

    for i, page in enumerate(doc):
        raw = page.get_text("dict")
        page_ctx = PageContext(
            index     = i,
            width     = page.rect.width,
            height    = page.rect.height,
            raw_dict  = raw,
            lines     = _extract_lines(raw, i),
        )
        pages.append(page_ctx)

    return DocumentContext(
        path       = pdf_path,
        page_count = doc.page_count,
        pages      = pages,
    )