import unicodedata

# Digit translation tables
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
EXT_ARABIC_INDIC_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")  # Persian forms
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

def normalize_all_digits(s: str) -> str:
    s2 = s.translate(FULLWIDTH_DIGITS)
    s2 = s2.translate(ARABIC_INDIC_DIGITS)
    s2 = s2.translate(EXT_ARABIC_INDIC_DIGITS)
    s2 = s2.translate(DEVANAGARI_DIGITS)
    return s2

def script_ratios(s: str):
    counts = {"latin":0,"cjk":0,"arabic":0,"devanagari":0,"other":0}
    total = 0
    for ch in s:
        if ch.isspace():
            continue
        if not ch.isprintable():
            continue
        total += 1
        o = ord(ch)
        if 0x0041 <= o <= 0x024F:  # Latin + extended
            counts["latin"] += 1
        elif 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF or 0x3040 <= o <= 0x30FF or 0xFF00 <= o <= 0xFFEF:
            counts["cjk"] += 1
        elif 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0x08A0 <= o <= 0x08FF:
            counts["arabic"] += 1
        elif 0x0900 <= o <= 0x097F:
            counts["devanagari"] += 1
        else:
            counts["other"] += 1
    if total == 0:
        return {k:0.0 for k in counts}
    return {k: v/total for k,v in counts.items()}

def dominant_script(ratios: dict):
    if not ratios:
        return "unknown"
    return max(ratios.items(), key=lambda kv: kv[1])[0]

# -------- RTL logical-order normaliser --------
def normalize_rtl(text: str) -> str:
    """Return display-order → logical-order for Arabic (keeps Latin unchanged)."""
    if not any('\u0600' <= ch <= '\u06FF' for ch in text):
        return text
    try:
        import arabic_reshaper, bidi.algorithm as ba
        reshaped = arabic_reshaper.reshape(text)
        return ba.get_display(reshaped)          #  e.g. "لصفلا1 ..." → "الفصل 1 ..."
    except Exception:
        return text
