# # gear/app/daily_sales/wb_plan_monitor/prophet_note/styles.py

# from __future__ import annotations

# from pathlib import Path

# from matplotlib import font_manager
# from reportlab.lib import colors
# from reportlab.lib.enums import (
#     TA_CENTER,
#     TA_JUSTIFY,
#     TA_LEFT,
#     TA_RIGHT,
# )
# from reportlab.lib.styles import (
#     ParagraphStyle,
#     getSampleStyleSheet,
# )
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont


# # =============================================================================
# # Корпоративная палитра
# # =============================================================================

# PRIMARY = colors.HexColor("#0F172A")
# SECONDARY = colors.HexColor("#334155")
# MUTED = colors.HexColor("#64748B")

# BORDER = colors.HexColor("#D9E2EC")
# GRID = colors.HexColor("#E8EEF4")
# LIGHT_BG = colors.HexColor("#F8FAFC")

# BLUE = colors.HexColor("#2563EB")
# BLUE_BG = colors.HexColor("#EFF6FF")

# ACCENT = colors.HexColor("#0F766E")
# ACCENT_BG = colors.HexColor("#ECFDF5")

# PLAN = colors.HexColor("#F97316")
# PLAN_BG = colors.HexColor("#FFF7ED")

# DANGER = colors.HexColor("#B91C1C")
# RED_BG = colors.HexColor("#FEF2F2")

# SUCCESS = colors.HexColor("#15803D")
# GREEN_BG = colors.HexColor("#F0FDF4")


# # =============================================================================
# # Шрифты
# # =============================================================================

# def _find_dejavu_font(
#     *,
#     bold: bool = False,
# ) -> Path | None:
#     """
#     Находит DejaVu Sans через matplotlib.

#     DejaVu Sans:
#     - корректно поддерживает кириллицу;
#     - содержит знак рубля ₽;
#     - одинаково работает на macOS, Linux и Windows;
#     - обычно уже установлен вместе с matplotlib.
#     """
#     properties = font_manager.FontProperties(
#         family="DejaVu Sans",
#         weight=(
#             "bold"
#             if bold
#             else "normal"
#         ),
#     )

#     try:
#         font_path = Path(
#             font_manager.findfont(
#                 properties,
#                 fallback_to_default=False,
#             )
#         )
#     except Exception:
#         return None

#     return (
#         font_path
#         if font_path.exists()
#         else None
#     )


# def _find_system_font(
#     candidates: list[str],
# ) -> Path | None:
#     for candidate in candidates:
#         path = Path(candidate)

#         if path.exists():
#             return path

#     return None


# def register_fonts() -> tuple[str, str]:
#     """
#     Регистрирует Unicode-шрифт с поддержкой знака рубля.

#     Сначала используется DejaVu Sans из matplotlib.
#     Системные шрифты применяются только как резерв.
#     """
#     regular_path = _find_dejavu_font(
#         bold=False,
#     )
#     bold_path = _find_dejavu_font(
#         bold=True,
#     )

#     if regular_path is None:
#         regular_path = _find_system_font(
#             [
#                 (
#                     "/usr/share/fonts/truetype/"
#                     "dejavu/DejaVuSans.ttf"
#                 ),
#                 "/Library/Fonts/DejaVu Sans.ttf",
#                 "C:/Windows/Fonts/DejaVuSans.ttf",
#             ]
#         )

#     if bold_path is None:
#         bold_path = _find_system_font(
#             [
#                 (
#                     "/usr/share/fonts/truetype/"
#                     "dejavu/DejaVuSans-Bold.ttf"
#                 ),
#                 "/Library/Fonts/DejaVu Sans Bold.ttf",
#                 "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
#             ]
#         )

#     if not regular_path or not bold_path:
#         raise RuntimeError(
#             "Не найден Unicode-шрифт для PDF. "
#             "Установи matplotlib или DejaVu Sans."
#         )

#     regular_name = "ProphetNoteRegular"
#     bold_name = "ProphetNoteBold"

#     registered_fonts = set(
#         pdfmetrics.getRegisteredFontNames()
#     )

#     if regular_name not in registered_fonts:
#         pdfmetrics.registerFont(
#             TTFont(
#                 regular_name,
#                 str(regular_path),
#             )
#         )

#     if bold_name not in registered_fonts:
#         pdfmetrics.registerFont(
#             TTFont(
#                 bold_name,
#                 str(bold_path),
#             )
#         )

#     pdfmetrics.registerFontFamily(
#         "ProphetNote",
#         normal=regular_name,
#         bold=bold_name,
#         italic=regular_name,
#         boldItalic=bold_name,
#     )

#     return regular_name, bold_name


# # =============================================================================
# # Стили текста
# # =============================================================================

# def build_styles():
#     regular, bold = register_fonts()
#     sample = getSampleStyleSheet()

#     return {
#         # -------------------------------------------------------------
#         # Служебные имена шрифтов
#         # -------------------------------------------------------------
#         "font_regular": regular,
#         "font_bold": bold,

#         # -------------------------------------------------------------
#         # Главные заголовки страниц
#         # -------------------------------------------------------------
#         "title": ParagraphStyle(
#             "NoteTitle",
#             parent=sample["Title"],
#             fontName=bold,
#             fontSize=18,
#             leading=23,
#             textColor=PRIMARY,
#             alignment=TA_LEFT,
#             spaceBefore=0,
#             spaceAfter=10,
#             keepWithNext=True,
#         ),

#         # -------------------------------------------------------------
#         # Вводный текст под заголовком
#         # -------------------------------------------------------------
#         "subtitle": ParagraphStyle(
#             "NoteSubtitle",
#             parent=sample["Normal"],
#             fontName=regular,
#             fontSize=10.2,
#             leading=15,
#             textColor=SECONDARY,
#             alignment=TA_JUSTIFY,
#             spaceAfter=14,
#             splitLongWords=False,
#             allowWidows=0,
#             allowOrphans=0,
#         ),

#         # -------------------------------------------------------------
#         # Подзаголовки внутри страницы
#         # -------------------------------------------------------------
#         "heading": ParagraphStyle(
#             "NoteHeading",
#             parent=sample["Heading2"],
#             fontName=regular,
#             fontSize=12.5,
#             leading=16,
#             textColor=PRIMARY,
#             alignment=TA_LEFT,
#             spaceBefore=5,
#             spaceAfter=8,
#             keepWithNext=True,
#         ),

#         # -------------------------------------------------------------
#         # Основной текст
#         # -------------------------------------------------------------
#         "body": ParagraphStyle(
#             "NoteBody",
#             parent=sample["BodyText"],
#             fontName=regular,
#             fontSize=9.2,
#             leading=13.8,
#             textColor=PRIMARY,
#             alignment=TA_JUSTIFY,
#             spaceAfter=7,
#             splitLongWords=False,
#             allowWidows=0,
#             allowOrphans=0,
#         ),

#         # -------------------------------------------------------------
#         # Мелкие пояснения и дисклеймеры
#         # -------------------------------------------------------------
#         "small": ParagraphStyle(
#             "NoteSmall",
#             parent=sample["BodyText"],
#             fontName=regular,
#             fontSize=7.8,
#             leading=10.8,
#             textColor=MUTED,
#             alignment=TA_JUSTIFY,
#             spaceAfter=4,
#             splitLongWords=False,
#             allowWidows=0,
#             allowOrphans=0,
#         ),

#         # -------------------------------------------------------------
#         # Заголовки таблиц
#         # -------------------------------------------------------------
#         "table_header": ParagraphStyle(
#             "NoteTableHeader",
#             parent=sample["BodyText"],
#             fontName=bold,
#             fontSize=7.8,
#             leading=9.5,
#             textColor=colors.white,
#             alignment=TA_CENTER,
#             spaceAfter=0,
#         ),

#         # -------------------------------------------------------------
#         # Обычная ячейка таблицы
#         # -------------------------------------------------------------
#         "table_cell": ParagraphStyle(
#             "NoteTableCell",
#             parent=sample["BodyText"],
#             fontName=regular,
#             fontSize=7.7,
#             leading=9.7,
#             textColor=PRIMARY,
#             alignment=TA_LEFT,
#             spaceAfter=0,
#             splitLongWords=False,
#         ),

#         # -------------------------------------------------------------
#         # Числовая ячейка таблицы
#         # -------------------------------------------------------------
#         "table_cell_right": ParagraphStyle(
#             "NoteTableCellRight",
#             parent=sample["BodyText"],
#             fontName=regular,
#             fontSize=7.7,
#             leading=9.7,
#             textColor=PRIMARY,
#             alignment=TA_RIGHT,
#             spaceAfter=0,
#         ),

#         # -------------------------------------------------------------
#         # Подписи KPI
#         # -------------------------------------------------------------
#         "kpi_label": ParagraphStyle(
#             "NoteKpiLabel",
#             parent=sample["BodyText"],
#             fontName=regular,
#             fontSize=7.6,
#             leading=9.5,
#             textColor=MUTED,
#             alignment=TA_CENTER,
#             spaceAfter=0,
#         ),

#         # -------------------------------------------------------------
#         # Значения KPI
#         # -------------------------------------------------------------
#         "kpi_value": ParagraphStyle(
#             "NoteKpiValue",
#             parent=sample["BodyText"],
#             fontName=bold,
#             fontSize=11.2,
#             leading=14,
#             textColor=colors.HexColor("#111827"),
#             alignment=TA_CENTER,
#             spaceAfter=0,
#         ),

#         # -------------------------------------------------------------
#         # Мелкий центрированный текст
#         # -------------------------------------------------------------
#         "center_small": ParagraphStyle(
#             "NoteCenterSmall",
#             parent=sample["BodyText"],
#             fontName=regular,
#             fontSize=7.8,
#             leading=10.5,
#             textColor=MUTED,
#             alignment=TA_CENTER,
#             spaceAfter=0,
#         ),
#     }



from __future__ import annotations

from pathlib import Path

from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# =============================================================================
# Единая палитра отчёта
# =============================================================================
# Основной принцип: цвет используется только для смысловой иерархии.
# Один тёмно-синий цвет — основа, один бирюзовый — прогноз/акцент.
# Красный применяется только к небольшим значениям риска, без красных заливок.

PRIMARY = colors.HexColor("#142033")
SECONDARY = colors.HexColor("#3F4C5F")
MUTED = colors.HexColor("#788496")

BORDER = colors.HexColor("#D8DEE7")
GRID = colors.HexColor("#E9EDF2")
LIGHT_BG = colors.HexColor("#F7F9FB")
WHITE = colors.white

# Основные смысловые цвета
BLUE = colors.HexColor("#233B5D")
BLUE_BG = colors.HexColor("#F1F4F8")
ACCENT = colors.HexColor("#167C80")
ACCENT_DARK = colors.HexColor("#0F666A")
ACCENT_BG = colors.HexColor("#F1F8F8")

# План — нейтральный графит, а не отдельный яркий цвет
PLAN = colors.HexColor("#7B8796")
PLAN_BG = colors.HexColor("#F4F6F8")

# Статусные цвета применяются точечно
DANGER = colors.HexColor("#B42318")
RED_BG = colors.HexColor("#FFF8F7")
SUCCESS = colors.HexColor("#18794E")
GREEN_BG = colors.HexColor("#F4FAF7")
WARNING = colors.HexColor("#9A6700")
WARNING_BG = colors.HexColor("#FFFBF2")


def _find_dejavu_font(*, bold: bool = False) -> Path | None:
    properties = font_manager.FontProperties(
        family="DejaVu Sans",
        weight="bold" if bold else "normal",
    )
    try:
        path = Path(
            font_manager.findfont(
                properties,
                fallback_to_default=False,
            )
        )
    except Exception:
        return None
    return path if path.exists() else None


def _find_system_font(candidates: list[str]) -> Path | None:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return None


def register_fonts() -> tuple[str, str]:
    """Регистрирует устойчивый Unicode-шрифт с кириллицей и знаком рубля."""
    regular_path = _find_dejavu_font(bold=False) or _find_system_font(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/DejaVu Sans.ttf",
            "C:/Windows/Fonts/DejaVuSans.ttf",
        ]
    )
    bold_path = _find_dejavu_font(bold=True) or _find_system_font(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/DejaVu Sans Bold.ttf",
            "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
        ]
    )

    if not regular_path or not bold_path:
        raise RuntimeError(
            "Не найден Unicode-шрифт. Установи matplotlib или DejaVu Sans."
        )

    regular_name = "ProphetNoteRegular"
    bold_name = "ProphetNoteBold"
    registered = set(pdfmetrics.getRegisteredFontNames())

    if regular_name not in registered:
        pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
    if bold_name not in registered:
        pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))

    pdfmetrics.registerFontFamily(
        "ProphetNote",
        normal=regular_name,
        bold=bold_name,
        italic=regular_name,
        boldItalic=bold_name,
    )
    return regular_name, bold_name


def build_styles():
    regular, bold = register_fonts()
    sample = getSampleStyleSheet()

    return {
        "font_regular": regular,
        "font_bold": bold,
        "title": ParagraphStyle(
            "NoteTitle",
            parent=sample["Title"],
            fontName=bold,
            fontSize=18.2,
            leading=22.5,
            textColor=PRIMARY,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "subtitle": ParagraphStyle(
            "NoteSubtitle",
            parent=sample["Normal"],
            fontName=regular,
            fontSize=9.5,
            leading=13.8,
            textColor=SECONDARY,
            alignment=TA_LEFT,
            spaceAfter=11,
            splitLongWords=False,
        ),
        "heading": ParagraphStyle(
            "NoteHeading",
            parent=sample["Heading2"],
            fontName=bold,
            fontSize=11.8,
            leading=15,
            textColor=PRIMARY,
            alignment=TA_LEFT,
            spaceBefore=5,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "NoteBody",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=8.8,
            leading=13.1,
            textColor=PRIMARY,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            splitLongWords=False,
            allowWidows=0,
            allowOrphans=0,
        ),
        "body_left": ParagraphStyle(
            "NoteBodyLeft",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=8.8,
            leading=13.1,
            textColor=PRIMARY,
            alignment=TA_LEFT,
            spaceAfter=0,
            splitLongWords=False,
        ),
        "small": ParagraphStyle(
            "NoteSmall",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=7.3,
            leading=10.1,
            textColor=MUTED,
            alignment=TA_LEFT,
            spaceAfter=3,
            splitLongWords=False,
        ),
        "table_header": ParagraphStyle(
            "NoteTableHeader",
            parent=sample["BodyText"],
            fontName=bold,
            fontSize=7.4,
            leading=9.1,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "table_header_left": ParagraphStyle(
            "NoteTableHeaderLeft",
            parent=sample["BodyText"],
            fontName=bold,
            fontSize=7.4,
            leading=9.1,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "table_cell": ParagraphStyle(
            "NoteTableCell",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=7.4,
            leading=9.3,
            textColor=PRIMARY,
            alignment=TA_LEFT,
            spaceAfter=0,
            splitLongWords=False,
        ),
        "table_cell_bold": ParagraphStyle(
            "NoteTableCellBold",
            parent=sample["BodyText"],
            fontName=bold,
            fontSize=7.4,
            leading=9.3,
            textColor=PRIMARY,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "table_cell_right": ParagraphStyle(
            "NoteTableCellRight",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=7.4,
            leading=9.3,
            textColor=PRIMARY,
            alignment=TA_RIGHT,
            spaceAfter=0,
        ),
        "table_cell_right_bold": ParagraphStyle(
            "NoteTableCellRightBold",
            parent=sample["BodyText"],
            fontName=bold,
            fontSize=7.6,
            leading=9.5,
            textColor=PRIMARY,
            alignment=TA_RIGHT,
            spaceAfter=0,
        ),
        "kpi_label": ParagraphStyle(
            "NoteKpiLabel",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=7.2,
            leading=9,
            textColor=MUTED,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "kpi_value": ParagraphStyle(
            "NoteKpiValue",
            parent=sample["BodyText"],
            fontName=bold,
            fontSize=10.8,
            leading=13.4,
            textColor=PRIMARY,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "center_small": ParagraphStyle(
            "NoteCenterSmall",
            parent=sample["BodyText"],
            fontName=regular,
            fontSize=7.3,
            leading=9.8,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "eyebrow": ParagraphStyle(
            "NoteEyebrow",
            parent=sample["BodyText"],
            fontName=bold,
            fontSize=7.0,
            leading=8.8,
            textColor=ACCENT,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
    }