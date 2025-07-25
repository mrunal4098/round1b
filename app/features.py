# app/features.py
import re, statistics
from typing import List, Dict, Any

from .layout import Line
from .config import Config
from .text_utils import (
    normalize_all_digits,
    normalize_rtl,
    script_ratios,
    dominant_script,
)

# ── numbering / chapter patterns ──────────────────────────────────────────────
_numbering_re       = re.compile(r'^\d+(?:\.\d+)*\s')                     # latin 1.2.3<space>
_jp_chapter_re      = re.compile(r'^第[0-9\uFF10-\uFF19]+章')
_romaji_jp_re       = re.compile(r'^Dai[0-9]+sho', re.IGNORECASE)
_ar_chapter_re      = re.compile(r'^(?:الفصل|الباب|المبحث)\s*[0-9٠-٩]+')
_hi_chapter_re      = re.compile(r'^अध्याय\s*[0-9]+')
_appendix_re        = re.compile(r'^Appendix\s+[A-Z]\b', re.IGNORECASE)
_roman_re           = re.compile(r'^[IVXLC]+\.?\s')
# JP numeric headings like “1.1 背景” (ASCII or full-width digits/dots)
_jp_numdot_re       = re.compile(r'^[0-9\uFF10-\uFF19]+(?:[.\uFF0E][0-9\uFF10-\uFF19]+)+')

_word_split_re      = re.compile(r'\s+')
_caption_prefix_re  = re.compile(r'^(figure|fig\.|table|tab\.)\b', re.IGNORECASE)
_dot_leader_re      = re.compile(r'\.{3,}')
_tail_page_num_re   = re.compile(r'\d{1,4}\s*$')

_AR_RANGE_RE        = re.compile(r'[\u0600-\u06FF\uFB50-\uFEFC]')
_CJK_RANGE_RE       = re.compile(r'[\u3040-\u30FF\u4E00-\u9FFF]')

# ---- D-3 heuristics ----
_LEFT_SLACK_PT      = 50.0
_TOC_RATIO_THRESH   = 0.40

_NUMERIC_SINGLE_RE  = re.compile(r'^\d+(?:\.\d+)?[KkMm]?$')
_NUMERIC_LIST_RE    = re.compile(r'^(?:\d+(?:\.\d+)?\s+){1,3}\d+(?:\.\d+)?$')
_PAGE_NUM_TOKEN_RE  = re.compile(r'^\d+\.?$')

_INST_RE            = re.compile(r'\b(university|department|laboratory|college|school|institute)\b', re.IGNORECASE)

# ────────────────────────────────── helpers ───────────────────────────────────
def _median_body_font(lines: List[Line]) -> float:
    sizes = [ln.avg_size for ln in lines if ln.avg_size > 0]
    if not sizes:
        return 1.0
    sizes.sort()
    trimmed = sizes[: int(len(sizes) * 0.95)] or sizes
    try:
        return statistics.median(trimmed) or 1.0
    except statistics.StatisticsError:
        return trimmed[0]

def _page_left_margins(lines: List[Line]) -> Dict[int, float]:
    by_page: Dict[int, List[float]] = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln.x0)
    return {p: (statistics.median(xs) if xs else 0.0) for p, xs in by_page.items()}

def _detect_toc_pages(lines: List[Line]) -> set[int]:
    by_page: Dict[int, List[Line]] = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln)
    toc_pages = set()
    for p, lns in by_page.items():
        if not lns:
            continue
        toc_like = 0
        for ln in lns:
            t = ln.text.strip()
            if _dot_leader_re.search(t) and _tail_page_num_re.search(t):
                toc_like += 1
        if toc_like / len(lns) >= _TOC_RATIO_THRESH and len(lns) >= 5:
            toc_pages.add(p)
    return toc_pages

# ────────────────────────────── main feature fn ───────────────────────────────
def compute_features(lines: List[Line], page_count: int) -> List[Dict[str, Any]]:
    body_med   = _median_body_font(lines)
    left_edge  = _page_left_margins(lines)
    toc_pages  = _detect_toc_pages(lines)

    # repetition map for running headers
    text_pages: Dict[str, set[int]] = {}
    for ln in lines:
        text_pages.setdefault(normalize_rtl(ln.text.strip()), set()).add(ln.page)

    feats: List[Dict[str, Any]] = []

    for idx, ln in enumerate(lines):
        raw         = normalize_rtl(ln.text.strip())
        norm_digits = normalize_all_digits(raw)

        words        = [w for w in _word_split_re.split(raw) if w]
        word_count   = len(words)
        char_count   = len(raw)
        rel_font     = (ln.avg_size / body_med) if body_med else 1.0
        is_bold      = ln.bold_frac >= 0.6

        # script detection
        ratios     = script_ratios(raw)
        dom_script = dominant_script(ratios)
        if dom_script == "unknown" and _AR_RANGE_RE.search(raw):
            dom_script = "arabic"
        if dom_script == "unknown" and _CJK_RANGE_RE.search(raw):
            dom_script = "cjk"

        # numbering / chapter patterns
        starts_numbering = False
        # Latin refinement: digits(.digits)* space + *letter* afterwards
        if dom_script == "latin":
            if re.match(r'^\d+(?:\.\d+)*\s+[A-Za-z]', norm_digits):
                starts_numbering = True
        else:
            if _numbering_re.match(norm_digits):
                starts_numbering = True
        if _jp_chapter_re.match(norm_digits):  starts_numbering = True
        if _romaji_jp_re.match(norm_digits):   starts_numbering = True
        if _ar_chapter_re.match(norm_digits):  starts_numbering = True
        if _hi_chapter_re.match(norm_digits):  starts_numbering = True
        if _appendix_re.match(raw):            starts_numbering = True
        if _roman_re.match(raw):               starts_numbering = True
        if _jp_numdot_re.match(norm_digits):   starts_numbering = True
        if dom_script == "arabic" and re.search(r'[0-9٠-٩]', norm_digits):
            starts_numbering = True

        ends_with_period = raw.endswith(('.', '?', '!', '。', '؟'))
        letters          = [c for c in raw if c.isalpha()]
        all_caps         = bool(letters) and all(ch.isupper() for ch in letters)
        title_case       = bool(words) and all((w[0].isupper() or not w[0].isalpha()) for w in words if w)

        # vertical gap above
        gap_above = None
        for j in range(idx - 1, -1, -1):
            if lines[j].page == ln.page:
                gap_above = ln.y0 - lines[j].y1
                break

        repeat_count    = len(text_pages.get(raw, set()))
        is_caption_like = bool(_caption_prefix_re.match(raw.lower()))
        has_dot_leader  = bool(_dot_leader_re.search(raw))

        feat = {
            "page"               : ln.page + 1,
            "text"               : raw,
            "avg_size"           : ln.avg_size,
            "rel_font_size"      : round(rel_font, 3),
            "is_bold"            : is_bold,
            "word_count"         : word_count,
            "char_count"         : char_count,
            "starts_numbering"   : starts_numbering,
            "all_caps"           : all_caps,
            "title_case"         : title_case,
            "ends_with_period"   : ends_with_period,
            "gap_above"          : gap_above,
            "repeat_count"       : repeat_count,
            "is_caption_like"    : is_caption_like,
            "has_dot_leader"     : has_dot_leader,
            "lower_text"         : raw.lower(),
            "script_dom"         : dom_script,
            "script_ratios"      : ratios,
            "x0"                 : ln.x0,
            "y0"                 : ln.y0,
            "_page_idx"          : ln.page,
        }
        feats.append(feat)

    # ───────────────────────── candidate decision ────────────────────────────
    for f in feats:
        script_dom  = f["script_dom"]
        non_latin   = script_dom in ("cjk", "arabic", "devanagari")
        page_idx    = f["_page_idx"]
        page_left   = left_edge.get(page_idx, 0.0)
        in_toc_page = page_idx in toc_pages

        font_ok = (
            f["rel_font_size"] >= Config.REL_FONT_HEADING_MIN
            or (f["rel_font_size"] >= Config.REL_FONT_HEADING_LOWERED and f["is_bold"])
        )
        if script_dom in ("arabic", "cjk") and f["starts_numbering"]:
            font_ok = True

        casing_ok = f["is_bold"] or f["title_case"] or f["all_caps"]
        if non_latin:
            casing_ok = True

        candidate = (
            (
                font_ok
                or (f["is_bold"] and f["word_count"] <= Config.MAX_SHORT_HEADING_WORDS and not f["ends_with_period"])
                or f["starts_numbering"]
            )
            and 1 <= f["word_count"] <= Config.MAX_HEADING_WORDS
            and f["char_count"] >= 2
            and casing_ok
        )

        # rescues
        if not candidate and non_latin and f["starts_numbering"]:
            candidate = True
        if not candidate and script_dom == "cjk" and _jp_numdot_re.match(normalize_all_digits(f["text"])):
            candidate = True
        if not candidate and script_dom == "arabic" and f["rel_font_size"] >= 1.05 and f["word_count"] <= 12:
            candidate = True

        # numeric-only / axis labels (Latin only)
        if candidate and script_dom == "latin":
            txt = f["text"].strip()
            if (
                _NUMERIC_SINGLE_RE.fullmatch(txt)
                or _NUMERIC_LIST_RE.fullmatch(txt)
                or (f["word_count"] == 1 and txt.endswith(".") and len(txt) <= 4 and _PAGE_NUM_TOKEN_RE.fullmatch(txt))
            ):
                candidate = False
            # page number match (e.g., "2" / "2.")
            else:
                stripped = txt.rstrip(".")
                if stripped.isdigit() and int(stripped) == f["page"]:
                    candidate = False
        if candidate and script_dom in ("cjk", "arabic", "devanagari", "unknown"):
            txt = f["text"].strip()
            norm = normalize_all_digits(txt)
            # letters excluding common axis units
            letters = [c for c in norm if c.isalpha()]
            letters_join = "".join(letters).lower()
            has_digit = any(ch.isdigit() for ch in norm)
            # heuristics: only digits + separators + units/percent, or MHz/KHz/GHz axis ticks
            units_tokens = any(u in norm for u in ("兆", "億", "万", "円", "%", "％"))
            mhz_like = letters_join in ("mhz", "khz", "ghz")
            only_punct = re.fullmatch(r'^[\d,，.\s％%]+$', norm) is not None
            yen_amount = re.fullmatch(r'^[\d,，\s]+(?:兆|億|万)?[\d,，\s]*(?:円)?[，,]?$', norm)
            percent_only = re.fullmatch(r'^[\d,，]+(?:\.\d+)?[％%]$', norm)
            freq_only = re.fullmatch(r'^\d+(?:\.\d+)?\s*[mMkKgG]?[hH][zZ]$', norm)
            if has_digit and (
                percent_only or freq_only or yen_amount or
                (only_punct and not letters) or
                (units_tokens and (not letters or mhz_like))
            ):
                candidate = False

        # negative filters / FP killers
        if candidate:
            if (
                f["repeat_count"] >= Config.RUNNING_HEADER_MIN_PAGES
                and (f["repeat_count"] / page_count) >= Config.RUNNING_HEADER_FRACTION
            ):
                candidate = False
            elif f["is_caption_like"] or f["has_dot_leader"]:
                candidate = False
            elif f["rel_font_size"] < 1.02 and not f["is_bold"] and not f["starts_numbering"] and not non_latin:
                candidate = False
            elif f["lower_text"].startswith("page "):
                candidate = False
            elif (
                script_dom == "latin"
                and (f["x0"] >= page_left + _LEFT_SLACK_PT)
                and not (font_ok or f["is_bold"] or f["starts_numbering"])
            ):
                candidate = False
            elif (
                script_dom == "latin"
                and not f["is_bold"]
                and not f["starts_numbering"]
                and (f["text"].count(".") >= 1 or f["word_count"] >= 10)
            ):
                candidate = False
            elif in_toc_page and script_dom == "latin" and not (f["rel_font_size"] >= 1.25 or f["starts_numbering"]):
                candidate = False

        f["candidate_heading"] = candidate

    # Arabic basic words
    _ar_basic_re = re.compile(r'^(المقدمة|الخاتمة)$')
    for f in feats:
        if _ar_basic_re.match(f["text"]):
            f["starts_numbering"]  = True
            f["candidate_heading"] = True

    # prune body-ish lines
    for f in feats:
        if not f["candidate_heading"]:
            continue
        if f["script_dom"] == "latin":
            multi_sent = (
                f["text"].count(".")
                + f["text"].count("؟")
                + f["text"].count("۔")
                + f["text"].count("।")
            )
            if multi_sent >= 2 and f["rel_font_size"] < 1.30:
                f["candidate_heading"] = False
                continue
            if f["word_count"] >= 12 and f["rel_font_size"] < 1.20:
                f["candidate_heading"] = False
                continue
        else:
            if (
                f["word_count"] >= 15
                and f["rel_font_size"] < 1.15
                and not f["starts_numbering"]
            ):
                f["candidate_heading"] = False

    # final rescue for numbered non-Latin lines
    for f in feats:
        if f["starts_numbering"] and f["script_dom"] in ("cjk", "arabic", "devanagari"):
            f["candidate_heading"] = True

    # --- Author / affiliation suppression (page 1) ---
    page1_feats = [f for f in feats if f["page"] == 1]
    has_email   = any("@" in f["text"] for f in page1_feats)
    abstract_pos = None
    for i, f in enumerate(page1_feats):
        if f["candidate_heading"] and f["text"].strip().upper() == "ABSTRACT":
            abstract_pos = i
            break
    for i, f in enumerate(page1_feats):
        if not f["candidate_heading"]:
            continue
        if f["text"].strip().upper() == "ABSTRACT":
            continue
        before_abstract = abstract_pos is not None and i < abstract_pos
        txt = f["text"]
        if has_email and "," in txt:
            f["candidate_heading"] = False
        elif before_abstract and ("," in txt or _INST_RE.search(txt)):
            f["candidate_heading"] = False

    return feats