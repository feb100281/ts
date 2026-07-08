from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


COLORS = {
    "dark_green": "2F6656",
    "light_green": "E6F1ED",
    "success": "EDF7F3",
    "warning": "FDECEC",
    "light_gray": "F7F7F7",
    "border_gray": "D9D9D9",
    "white": "FFFFFF",
    "text": "050505",
    "muted": "6B7280",
    "link": "0563C1",
    "discount": "A33A3A",
    "money": "EEF7F2",
    "qty": "EEF4FF",
    "delta_plus": "FDECEC",
    "delta_minus": "EDF7F3",
    "delta_zero": "F7F7F7",
}

FONT_NAME = "Roboto Light"
FONT_NAME_BOLD = "Roboto"
FONT_MONO = "Consolas"

THIN_BORDER = Border(
    left=Side(style="thin", color=COLORS["border_gray"]),
    right=Side(style="thin", color=COLORS["border_gray"]),
    top=Side(style="thin", color=COLORS["border_gray"]),
    bottom=Side(style="thin", color=COLORS["border_gray"]),
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

BODY_MONO_FONT = Font(
    name=FONT_MONO,
    size=9,
    color=COLORS["text"],
)

TITLE_FONT = Font(
    name=FONT_NAME_BOLD,
    size=16,
    bold=True,
    color=COLORS["dark_green"],
)

SUBTITLE_FONT = Font(
    name=FONT_NAME,
    size=10,
    color=COLORS["muted"],
)

SMALL_MUTED_FONT = Font(
    name=FONT_NAME,
    size=9,
    italic=True,
    color=COLORS["muted"],
)

BUTTON_FONT = Font(
    name=FONT_NAME_BOLD,
    size=10,
    bold=True,
    color=COLORS["dark_green"],
)

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)