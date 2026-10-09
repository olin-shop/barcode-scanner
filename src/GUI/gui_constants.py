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

GREEN_BLUE: str = "#26AAA5"
GREEN_BLUE_HOVER: str = "#00677E"

OLIN_BLUE: str = "#009BDF"  # Olin Cerulean / Light Blue Accent
OLIN_BLUE_HOVER: str = "#0045BC"
OLIN_LIGHT_BLUE: str = "#68C1D3"
OLIN_LIGHT_BLUE_HOVER: str = "#D4ECF9"

OLIN_PINK: str = "#ED037C"

DARK_BLUE_TEXT: str = "#0F2537"  # Primary text color
MUTED_BLUE_TEXT: str = "#4A6572"  # Subtitles & dates

DARK_BLUE: str = "#009DD1"  # Primary Olin Blue
LIGHT_BLUE: str = "#EBF6FC"  # Soft Light Blue

CONFIRM_BLUE: str = "#009DD1"  # Olin Blue confirm action
CONFIRM_BLUE_HOVER: str = "#0086B3"

CANCEL_RED: str = "#E31D3C"
CANCEL_RED_HOVER: str = "#750324"

MISSING_RED: str = "#E31D3C"
MISSING_RED_HOVER: str = "#750324"

TIMEOUT_BG: str = "#F0F7FC"
TIMEOUT_TEXT: str = "#0F2537"
TIMEOUT_SUBTEXT: str = "#4A6572"

# ---------------------------------------------------------------------------
# Fonts (All fonts set to DIN OT bold per user directive)
# ---------------------------------------------------------------------------
import sys
import ctypes
import customtkinter as ctk
import tkinter.font as tkfont

# Automatically register any .ttf or .otf font files placed anywhere inside static/
loaded_files = []
try:
    font_files = (
        list(STATIC_DIR.rglob("*.otf")) +
        list(STATIC_DIR.rglob("*.ttf")) +
        list(STATIC_DIR.rglob("*.OTF")) +
        list(STATIC_DIR.rglob("*.TTF"))
    )
    for font_file in font_files:
        path_str = str(font_file.resolve())
        # CustomTkinter font loader
        ctk.FontManager.load_font(path_str)
        # On Windows, also register with GDI AddFontResourceExW for process-wide font availability
        if sys.platform == "win32":
            try:
                ctypes.windll.gdi32.AddFontResourceExW(path_str, 0x10, 0)
            except (AttributeError, OSError, TypeError):
                pass
        loaded_files.append(font_file.name)
except (OSError, RuntimeError, TypeError) as e:
    print(f"[gui_constants] Font loading exception: {e}")

def _resolve_din_font_family() -> str:
    """Finds the registered DIN font family name in Tkinter, or defaults to 'DIN OT'."""
    try:
        root = ctk.CTk()
        root.withdraw()
        families = tkfont.families(root)
        din_families = [f for f in families if "DIN" in f.upper()]
        root.destroy()
        if din_families:
            print(f"[gui_constants] Found DIN font families in system: {din_families}")
            return din_families[0]
    except Exception as e:
        print(f"[gui_constants] Exception querying font families: {e}")
    return "DIN OT"

FONT_FAMILY: str = _resolve_din_font_family()
print(f"[gui_constants] FONT_FAMILY set to: {FONT_FAMILY!r} (Loaded {len(loaded_files)} font files)")

FONT_TITLE = (FONT_FAMILY, 32, "bold")
FONT_HEADING = (FONT_FAMILY, 38, "bold")
FONT_HUGE = (FONT_FAMILY, 88, "bold")
FONT_CONFIRM_HUGE = (FONT_FAMILY, 80, "bold") #?
FONT_BODY = (FONT_FAMILY, 28, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 25, "bold")
FONT_BUTTON = (FONT_FAMILY, 36, "bold")
FONT_ITEM_ROW = (FONT_FAMILY, 22, "bold")
FONT_DATE = (FONT_FAMILY, 15, "bold")
FONT_POPUP = (FONT_FAMILY, 16, "bold")
FONT_HEADING_HUGE = (FONT_FAMILY, 56, "bold") # large heading

# ---------------------------------------------------------------------------
# Timing (milliseconds)
# ---------------------------------------------------------------------------
SESSION_TIMEOUT_MS: int = 50_000
TIMEOUT_DISMISS_MS: int = 3_000
FINAL_CONFIRM_DISMISS_MS: int = 3_000

# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
WINDOW_SIZE: str = "1024x600"
WINDOW_TITLE: str = "Barcode System - Olin Shop"
