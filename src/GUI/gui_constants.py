"""
Centralized UI configuration: theme colors, fonts, asset paths, and timing.
Styled according to Olin College branding (White & Light Blue, DIN OT bold).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# GUI/gui_constants.py -> parent (GUI/) -> parent (project root)
BASE_DIR: Path = Path(__file__).resolve().parent.parent
STATIC_DIR: Path = BASE_DIR / "static"

# ---------------------------------------------------------------------------
# Colors (Olin College Website Palette: White & Light Blue)
# ---------------------------------------------------------------------------
BG_WHITE: str = "#FFFFFF"
BG_LIGHT_BLUE: str = "#F0F7FC"
SURFACE_CARD: str = "#FAFDFF"
BORDER_BLUE: str = "#BCE3F7"

OLIN_BLUE: str = "#009DD1"            # Olin Cerulean / Light Blue Accent
OLIN_BLUE_HOVER: str = "#0086B3"
OLIN_LIGHT_BLUE: str = "#EBF6FC"
OLIN_LIGHT_BLUE_HOVER: str = "#D4ECF9"

DARK_BLUE_TEXT: str = "#0F2537"       # Primary text color
MUTED_BLUE_TEXT: str = "#4A6572"      # Subtitles & dates

DARK_BLUE: str = "#009DD1"            # Primary Olin Blue
LIGHT_BLUE: str = "#EBF6FC"           # Soft Light Blue

CONFIRM_BLUE: str = "#009DD1"         # Olin Blue confirm action
CONFIRM_BLUE_HOVER: str = "#0086B3"

CANCEL_RED: str = "#D9383A"
CANCEL_RED_HOVER: str = "#B82A2C"

MISSING_RED: str = "#D9383A"
MISSING_RED_HOVER: str = "#B82A2C"

TIMEOUT_BG: str = "#F0F7FC"
TIMEOUT_TEXT: str = "#0F2537"
TIMEOUT_SUBTEXT: str = "#4A6572"

# ---------------------------------------------------------------------------
# Fonts (All fonts set to DIN OT bold per user directive)
# ---------------------------------------------------------------------------
FONT_FAMILY: str = "DIN OT"

FONT_TITLE = (FONT_FAMILY, 32, "bold")
FONT_HEADING = (FONT_FAMILY, 36, "bold")
FONT_HUGE = (FONT_FAMILY, 88, "bold")
FONT_CONFIRM_HUGE = (FONT_FAMILY, 80, "bold")
FONT_BODY = (FONT_FAMILY, 28, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 18, "bold")
FONT_BUTTON = (FONT_FAMILY, 30, "bold")
FONT_ITEM_ROW = (FONT_FAMILY, 22, "bold")
FONT_DATE = (FONT_FAMILY, 15, "bold")
FONT_POPUP = (FONT_FAMILY, 16, "bold")
FONT_LOADING = (FONT_FAMILY, 56, "bold")
FONT_TIMEOUT_TITLE = (FONT_FAMILY, 56, "bold")
FONT_TIMEOUT_SUBTITLE = (FONT_FAMILY, 24, "bold")
FONT_CLOSING_SESSION = (FONT_FAMILY, 28, "bold")

# ---------------------------------------------------------------------------
# Timing (milliseconds)
# ---------------------------------------------------------------------------
SESSION_TIMEOUT_MS: int = 30_000
TIMEOUT_DISMISS_MS: int = 3_000
FINAL_CONFIRM_DISMISS_MS: int = 3_000

# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
WINDOW_SIZE: str = "800x480"
WINDOW_TITLE: str = "Barcode System - Olin Shop"
