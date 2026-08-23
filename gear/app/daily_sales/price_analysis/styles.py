# gear/app/daily_sales/price_analysis/styles.py
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

COLORS = {
    "dark": "22312D",
    "dark_green": "2F6656",
    "green": "3C7A67",
    "light_green": "E7F1ED",
    "very_light_green": "F3F8F6",
    "orange": "B45309",
    "light_orange": "FEF3E7",
    "red": "A33A3A",
    "light_red": "FDECEC",
    "yellow": "9A6700",
    "light_yellow": "FFF6D8",
    "blue": "3B6B8F",
    "light_blue": "EDF4FA",
    "gray": "6B7280",
    "light_gray": "F6F7F8",
    "border": "D9DEE2",
    "white": "FFFFFF",
    "text": "111827",
    "link": "0563C1",
}

FONT_NAME = "Roboto Light"
FONT_NAME_BOLD = "Roboto"
FONT_MONO = "Consolas"

THIN_BORDER = Border(
    left=Side(style="thin", color=COLORS["border"]),
    right=Side(style="thin", color=COLORS["border"]),
    top=Side(style="thin", color=COLORS["border"]),
    bottom=Side(style="thin", color=COLORS["border"]),
)

HEADER_FONT = Font(
    name=FONT_NAME_BOLD,
    size=9,
    bold=True,
    color=COLORS["white"],
)

BODY_FONT = Font(
    name=FONT_NAME,
    size=10,
    color=COLORS["text"],
)

TITLE_FONT = Font(
    name=FONT_NAME_BOLD,
    size=17,
    bold=True,
    color=COLORS["dark_green"],
)

SUBTITLE_FONT = Font(
    name=FONT_NAME,
    size=10,
    color=COLORS["gray"],
)

SMALL_MUTED_FONT = Font(
    name=FONT_NAME,
    size=9,
    italic=True,
    color=COLORS["gray"],
)

BUTTON_FONT = Font(
    name=FONT_NAME_BOLD,
    size=10,
    bold=True,
    color=COLORS["dark_green"],
)

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
RIGHT = Alignment(horizontal="right", vertical="center")
