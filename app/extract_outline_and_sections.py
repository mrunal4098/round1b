import pathlib, re
from typing import List, Dict, Any
from .pdf_loader import load_document
from .layout import build_lines
from .features import compute_features
from .level_assign import assign_levels

Section = Dict[str, Any]

def extract(pdf_path: pathlib.Path, doc_id: str) -> List[Section]:
    """Return list of section dicts for one PDF."""
    doc_ctx = load_document(str(pdf_path))
    lines   = build_lines(doc_ctx)
    feats   = compute_features(lines, doc_ctx.page_count)

    # ---- headings -------------------------------------------------------
    candidates = [
        {
          "page" : f["page"],
          "text" : f["text"],
          "y0"   : f.get("y0", 0.0),
          "avg_size": f["avg_size"],
          "rel_font_size": f["rel_font_size"],
          "is_bold": f["is_bold"],
          "starts_numbering": f["starts_numbering"]
        }
        for f in feats if f["candidate_heading"]
    ]
    assigned, _title = assign_levels(candidates, doc_ctx.page_count)

    # ---- group by heading boundaries ------------------------------------
    # (reading order already guaranteed)
    sections: List[Section] = []
    for idx, h in enumerate(assigned):
        if h["proposed_level"] == "TITLE":
            continue
        start_line_idx = None
        end_line_idx   = None
        for i, ln in enumerate(lines):
            if ln.page == h["page"] and ln.y0 >= h["y0"] - 1e-3:
                start_line_idx = i + 1  # first line after the heading
                break
        # range until next heading of SAME or HIGHER level
        next_y0   = None
        next_page = None
        for n in assigned[idx + 1 :]:
            if n["proposed_level"] <= h["proposed_level"]:
                next_y0, next_page = n["y0"], n["page"]
                break

        collected = []
        for ln in lines[start_line_idx:]:
            if next_page is not None:
                if ln.page > next_page or (ln.page == next_page and ln.y0 >= next_y0 - 1e-3):
                    break
            collected.append(ln)

        if not collected:
            continue

        txt = "\n".join(ln.text.strip() for ln in collected if ln.text.strip())
        sections.append({
            "doc_id"      : doc_id,
            "doc_name"    : pdf_path.name,
            "heading"     : h["text"].strip(),
            "level"       : h["proposed_level"],
            "page_start"  : collected[0].page,
            "page_end"    : collected[-1].page,
            "text"        : txt
        })
    return sections