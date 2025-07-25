# app/level_assign.py
import re
from typing import List, Dict, Any, Tuple

# latin/fullwidth/arabic digits + dot/fullwidth dot
_NUMBERING_RE = re.compile(r'^([0-9\uFF10-\uFF19٠-٩]+(?:[.\uFF0E][0-9\uFF10-\uFF19٠-٩]+)*)')

_ar_head_re    = re.compile(r'^(?:الفصل|الباب|المبحث)\s*[0-9٠-٩]+')
_jp_chapter_re = re.compile(r'^第[0-9\uFF10-\uFF19]+章')

_PURE_NUMBER_RE = re.compile(r'^\d+(?:\.\d+)*\.?$')
_CAPS_STOP = {
    "RELATED WORK", "CONCLUSIONS", "APPENDIX",
    "ADDITIONAL", "USER STUDY RESULTS"
}

def _extract_number_depth(text: str) -> int | None:
    m = _NUMBERING_RE.match(text)
    if not m:
        return None
    seq = m.group(1).replace("\uFF0E", ".")
    return min(seq.count(".") + 1, 3)

def _looks_like_heading(text: str) -> bool:
    return (
        _extract_number_depth(text) is not None
        or _ar_head_re.match(text)
        or _jp_chapter_re.match(text)
    )

def _is_all_caps(txt: str) -> bool:
    letters = [c for c in txt if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)

def _cluster_font_sizes(cands: List[Dict[str, Any]], tol: float = 0.75) -> list[list[float]]:
    sizes = sorted({round(c["avg_size"], 2) for c in cands}, reverse=True)
    tiers: list[list[float]] = []
    for s in sizes:
        for tier in tiers:
            if abs(tier[0] - s) <= tol:
                tier.append(s)
                break
        else:
            tiers.append([s])
    return tiers

def assign_levels(candidates: List[Dict[str,Any]], page_count: int) -> Tuple[List[Dict[str,Any]], Dict[str,Any]]:
    if not candidates:
        return [], {}

    # ensure reading order
    candidates.sort(key=lambda c: (c["page"], c.get("y0", 0.0)))

    # 1) forward merge (block for ALL-CAPS stoplist pairs)
    merged: list[Dict[str, Any]] = []
    skip = False
    for i, c in enumerate(candidates):
        if skip:
            skip = False
            continue
        if i + 1 < len(candidates):
            n = candidates[i + 1]
            gap = n.get("gap_above")
            cap_stop = (
                _is_all_caps(c["text"]) and _is_all_caps(n["text"]) and
                c["text"].strip().upper() in _CAPS_STOP and
                n["text"].strip().upper() in _CAPS_STOP
            )
            if (
                not cap_stop
                and c["page"] == n["page"]
                and gap is not None and gap <= 2
                and abs(c["avg_size"] - n["avg_size"]) <= 0.5
                and _extract_number_depth(n["text"]) is None
            ):
                c["text"] = (c["text"] + " " + n["text"]).strip()
                skip = True
        merged.append(c)
    candidates = merged

    # 2) backward merge: number-only line prepended to previous heading
    i = 1
    while i < len(candidates):
        cur = candidates[i]
        prev = candidates[i - 1]
        if (
            _PURE_NUMBER_RE.fullmatch(cur["text"].strip())
            and prev["page"] == cur["page"]
            and cur.get("gap_above") is not None and cur["gap_above"] <= 3
            and abs(prev["avg_size"] - cur["avg_size"]) <= 0.5
        ):
            prev["text"] = (cur["text"].strip() + " " + prev["text"]).strip()
            candidates.pop(i)
            continue
        i += 1

    # 3) choose title
    pool = [c for c in candidates if c["page"] == 1] or candidates
    title_candidate = max(pool, key=lambda x: (x["rel_font_size"], x["avg_size"]))
    title_candidate["proposed_level"] = "TITLE"

    remaining = [c for c in candidates if c is not title_candidate]

    # 4) If title looks like heading, also emit as H1
    if _looks_like_heading(title_candidate["text"]):
        clone = dict(title_candidate)
        clone["proposed_level"] = "H1"
        remaining.insert(0, clone)

    # 5) numbering depth
    for c in remaining:
        depth = _extract_number_depth(c["text"])
        if depth:
            c["proposed_level"] = {1: "H1", 2: "H2", 3: "H3"}[depth]

    # 6) font tiers for rest
    unassigned = [c for c in remaining if "proposed_level" not in c]
    tiers = _cluster_font_sizes(remaining)
    tier_to_level = {}
    for i, tier in enumerate(tiers):
        lvl = "H1" if i == 0 else "H2" if i == 1 else "H3"
        for s in tier:
            tier_to_level[s] = lvl
    for c in unassigned:
        c["proposed_level"] = tier_to_level.get(round(c["avg_size"], 2), "H3")

    # 7) context promotions
    seen_h1 = False
    last_level = None
    for c in remaining:
        lvl = c["proposed_level"]
        if lvl == "H1":
            seen_h1 = True
        elif lvl == "H2" and not seen_h1:
            c["proposed_level"] = "H1"
            seen_h1 = True
        elif lvl == "H3" and last_level not in ("H2", "H3"):
            c["proposed_level"] = "H2"
        last_level = c["proposed_level"]

    # final ordering by reading order
    ordered = sorted(candidates + [c for c in remaining if c not in candidates],
                     key=lambda c: (c["page"], c.get("y0", 0.0)))
    return ordered, title_candidate

def dedupe_outline(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for e in entries:
        key = (e["level"], e["text"], e["page"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out