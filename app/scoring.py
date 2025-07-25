from typing import Dict
from .config import Config

def score_candidate(feat: Dict) -> float:
    s = 0.0
    rel = feat["rel_font_size"]
    s += Config.W_REL_FONT * min(rel, 2.0)
    if feat["is_bold"]:
        s += Config.W_BOLD
    if feat["starts_numbering"]:
        s += Config.W_NUMBERING
    gap = feat.get("gap_above")
    if gap is not None and gap >= Config.GAP_ABOVE_MIN_ISOLATION:
        s += Config.W_GAP_ABOVE
    # English-centric casing only if Latin dominant
    if feat.get("script_dom") == "latin":
        if feat.get("title_case"):
            s += Config.W_TITLE_CASE
        if feat.get("all_caps"):
            s += Config.W_ALL_CAPS
    else:
        # Non-Latin scripts slight neutral boost (lack capitalization signal)
        s += 0.2
    # Penalties (soft)
    if feat["ends_with_period"] and rel < 1.15 and feat.get("script_dom") == "latin":
        s -= 0.6
    if feat["word_count"] > Config.MAX_HEADING_WORDS:
        s -= 1.0
    if feat["word_count"] == 1 and feat["text"].islower() and feat.get("script_dom")=="latin":
        s -= 0.3
    return round(s, 3)
