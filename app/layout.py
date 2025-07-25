# ─── app/layout.py ────────────────────────────────────────────────────────────
from __future__ import annotations          # so we can quote forward refs
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

# ↓ prevent circular import: only import for type-checking, not at runtime
if TYPE_CHECKING:                           # this block is ignored when running
    from .pdf_loader import DocumentContext

@dataclass
class Line:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    spans: list = field(default_factory=list)
    font_sizes: list = field(default_factory=list)
    primary_font: str = ""
    avg_size: float = 0.0
    bold_frac: float = 0.0

# ─── helper ----------------------------------------------------------
def _is_span_bold(font_name: str) -> bool:
    fn = font_name.lower()
    return any(key in fn for key in ("bold", "black", "semibold", "heavy"))

# ─── main ------------------------------------------------------------
def build_lines(doc_ctx: "DocumentContext") -> List[Line]:
    """Convert PyMuPDF ‘dict’ blocks → flat list of Line objects."""
    lines: List[Line] = []
    for page_ctx in doc_ctx.pages:
        for blk in page_ctx.raw_dict.get("blocks", []):
            if blk.get("type", 0) != 0:
                continue
            for l in blk.get("lines", []):
                spans = l.get("spans", [])
                if not spans:
                    continue
                raw_text = "".join(s.get("text", "") for s in spans).strip()
                if not raw_text:
                    continue

                x0 = min(s["bbox"][0] for s in spans)
                y0 = min(s["bbox"][1] for s in spans)
                x1 = max(s["bbox"][2] for s in spans)
                y1 = max(s["bbox"][3] for s in spans)

                sizes = [float(s.get("size", 0)) for s in spans]
                bolds = [_is_span_bold(s.get("font", "")) for s in spans]

                lines.append(
                    Line(
                        page=page_ctx.index,
                        text=raw_text,
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        spans=spans,
                        font_sizes=sizes,
                        primary_font=spans[0].get("font", "") if spans else "",
                        avg_size=sum(sizes) / len(sizes) if sizes else 0.0,
                        bold_frac=sum(bolds) / len(bolds) if bolds else 0.0,
                    )
                )

    # Sort top-to-bottom, left-to-right
    lines.sort(key=lambda ln: (ln.page, ln.y0, ln.x0))
    return lines