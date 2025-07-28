import pathlib, re
from typing import List, Dict, Any
from .pdf_loader   import load_document
from .layout       import build_lines
from .features     import compute_features
from .level_assign import assign_levels

Section      = Dict[str, Any]
APPENDIX_RE  = re.compile(r'^(Appendix [A-Z]):\s*(.+)$')
UPPER_RATIO  = 0.70                     # >70 % caps → likely junk

# ──────────────────────────────────────────────────────────────
def _merge_headings(assigned: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge split-word fragments and pull full Appendix subtitles onto one line."""
    merged: List[Dict[str, Any]] = []
    for h in assigned:
        txt = h["text"].strip()
        if merged:
            prev = merged[-1]
            same_page  = h["page"] == prev["page"]
            same_level = h["proposed_level"] == prev["proposed_level"]
            very_close = abs(h["y0"] - prev["y0"]) < 1.0

            # (a) mid-word continuation  →  “Working T” + “ogether”
            if same_page and same_level and very_close and txt and txt[0].islower():
                prev["text"] += txt
                continue

            # (b) Appendix subtitle
            m = APPENDIX_RE.match(txt)
            if m and same_page and same_level:
                prev["text"] = f"{m.group(1)}: {m.group(2)}"
                continue
        merged.append(h)
    return merged

# ──────────────────────────────────────────────────────────────
def _paragraphs_with_page(lines_block) -> List[Dict[str, Any]]:
    """Convert a list of Line objects into paragraphs, preserving PDF page numbers."""
    paragraphs, buf, cur_page = [], [], lines_block[0].page

    def flush():
        if buf:
            paragraphs.append({"page": cur_page, "text": " ".join(buf).strip()})
            buf.clear()

    for ln in lines_block:
        if ln.page != cur_page:          # page break
            flush()
            cur_page = ln.page
        if ln.text.strip() == "":        # blank line
            flush()
            continue
        buf.append(ln.text.strip())
    flush()
    return paragraphs

# ──────────────────────────────────────────────────────────────
def extract(pdf_path: pathlib.Path, doc_id: str) -> List[Section]:
    """
    Return list of section dicts for one PDF (with accurate paragraph-level page tracking).
    """
    doc_ctx = load_document(str(pdf_path))
    lines   = build_lines(doc_ctx)
    feats   = compute_features(lines, doc_ctx.page_count)

    # 1 · candidate headings
    cands = [f | {"y0": f.get("y0", 0.0)} for f in feats if f["candidate_heading"]]
    assigned, _ = assign_levels(cands, doc_ctx.page_count)

    # 2 · merge fragments / subtitles
    merged = _merge_headings(assigned)

    # 3 · FILTER  – drop TITLE, too-short, or all-caps junk
    headings = []
    for h in merged:
        if h["proposed_level"] == "TITLE":
            continue

        txt = h["text"].strip()
        if not re.search(r"[A-Za-z]", txt):      # no letters
            continue
        tokens = [t for t in re.split(r"\W+", txt) if len(t) >= 3]   # ignore 1-2-char junk
        if len(tokens) < 3:
            continue
        if sum(map(str.isupper, txt)) / len(txt) > UPPER_RATIO:   # mostly CAPS
            continue

        headings.append(h)

    # 4 · build sections
    sections: List[Section] = []
    for idx, h in enumerate(headings):

        # find first content line after heading
        start_idx = None
        for i, ln in enumerate(lines):
            if ln.page == h["page"] and ln.y0 >= h["y0"] - 1e-3:
                start_idx = i + 1
                break
        if start_idx is None or start_idx >= len(lines):
            continue                              # orphan heading

        # locate next heading (same / higher level)
        next_y0 = next_page = None
        for nxt in headings[idx + 1:]:
            if nxt["proposed_level"] <= h["proposed_level"]:
                next_y0, next_page = nxt["y0"], nxt["page"]
                break

        block = []
        for ln in lines[start_idx:]:
            if next_page is not None and (
                ln.page > next_page or (ln.page == next_page and ln.y0 >= next_y0 - 1e-3)
            ):
                break
            block.append(ln)
        if not block:
            continue

        para_objs = _paragraphs_with_page(block)
        full_txt  = "\n\n".join(p["text"] for p in para_objs)

        sections.append({
            "doc_id"     : doc_id,
            "doc_name"   : pdf_path.name,
            "heading"    : h["text"].strip(),
            "level"      : h["proposed_level"],       # numeric level from assign_levels
            "page_start" : block[0].page,
            "page_end"   : block[-1].page,
            "full_text"  : full_txt,
            "paragraphs" : para_objs
        })

    return sections