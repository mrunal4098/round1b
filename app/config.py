class Config:
    # Font / size thresholds
    REL_FONT_HEADING_MIN = 1.12
    REL_FONT_HEADING_LOWERED = 1.05  # fallback for small docs
    MAX_HEADING_WORDS = 20
    MAX_SHORT_HEADING_WORDS = 12

    # Repetition
    RUNNING_HEADER_MIN_PAGES = 2
    RUNNING_HEADER_FRACTION = 0.5  # appears on >=50% pages -> header/footer

    # Candidate scoring weights
    W_REL_FONT = 1.6
    W_BOLD = 0.8
    W_NUMBERING = 0.9
    W_GAP_ABOVE = 0.4
    W_TITLE_CASE = 0.2
    W_ALL_CAPS = 0.3

    GAP_ABOVE_MIN_ISOLATION = 6.0  # bigger gap suggests heading separation

    # Caption / noise patterns
    CAPTION_PREFIXES = ("figure","fig.","table","tab.")
    TOC_HINTS = ("......", "page ")  # dot leader patterns
    FOOTER_MAX_FONT_REL = 0.9

    # Debug

# Runtime flag (default off) – set DEBUG=1 environment variable to include debug keys.
import os
Config.INCLUDE_DEBUG = (os.getenv("DEBUG") == "1")

# Runtime flag (default off) – set DEBUG=1 environment variable to include debug keys.
import os
Config.INCLUDE_DEBUG = (os.getenv("DEBUG") == "1")
