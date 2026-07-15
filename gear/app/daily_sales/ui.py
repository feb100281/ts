# gear/app/daily_sales/ui.py

from datetime import date, timedelta

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from .wb_plan_monitor import wb_plan_button, wb_plan_modal
from .ai_analysis import ai_analysis_button, ai_analysis_modal
from .price_analysis.config import (
    PRICE_ANALYSIS_EXPORT_BTN_ID,
    PRICE_ANALYSIS_DOWNLOAD_ID,
    PRICE_ANALYSIS_LOADING_ID,
)


# ============================================================
# ID
# ============================================================

STOCKS_DATE_PICKER_ID = "daily-sales-stocks-date-picker"
STOCKS_EXPORT_BTN_ID = "daily-sales-stocks-export-btn"
STOCKS_EXPORT_DOWNLOAD_ID = "daily-sales-stocks-export-download"
STOCKS_EXPORT_LOADING_ID = "daily-sales-stocks-export-loading"


# ============================================================
# ЦВЕТА
# ============================================================

PANEL_BORDER = "#DEE2E6"
BLOCK_BORDER = "#E9ECEF"

TEXT_COLOR = "#212529"
MUTED_TEXT_COLOR = "#868E96"

GREEN = "#2FB344"
GREEN_BG = "#EBFBEE"

ORANGE = "#F76707"
ORANGE_BG = "#FFF4E6"

VIOLET = "#7950F2"
VIOLET_BG = "#F3F0FF"

BLUE = "#228BE6"
BLUE_BG = "#E7F5FF"


# ============================================================
# ИКОНКА РАЗДЕЛА
# ============================================================

def section_icon(icon, color, background_color):
    return dmc.Center(
        w=34,
        h=34,
        style={
            "backgroundColor": background_color,
            "border": f"1px solid {color}22",
            "flexShrink": 0,
        },
        children=DashIconify(
            icon=icon,
            width=19,
            height=19,
            color=color,
        ),
    )


# ============================================================
# ЗАГОЛОВОК РАЗДЕЛА
# ============================================================

def section_title(title, subtitle=None):
    children = [
        dmc.Text(
            title,
            fw=700,
            size="sm",
            c=TEXT_COLOR,
            lh=1.1,
            style={
                "whiteSpace": "nowrap",
            },
        ),
    ]

    if subtitle:
        children.append(
            dmc.Text(
                subtitle,
                size="xs",
                c=MUTED_TEXT_COLOR,
                lh=1.1,
                mt=3,
                style={
                    "whiteSpace": "nowrap",
                },
            )
        )

    return dmc.Stack(
        gap=0,
        children=children,
    )


# ============================================================
# ИКОНКА ДЕЙСТВИЯ
# ============================================================

def action_icon(
    button_id,
    tooltip,
    icon,
    color,
    background_color,
    icon_width=19,
):
    return dmc.Tooltip(
        label=tooltip,
        position="top",
        withArrow=True,
        openDelay=300,
        children=dmc.ActionIcon(
            id=button_id,
            variant="outline",
            radius="sm",
            size=36,
            color=color,
            children=DashIconify(
                icon=icon,
                width=icon_width,
                height=icon_width,
            ),
            styles={
                "root": {
                    "backgroundColor": background_color,
                    "borderColor": color,
                    "flexShrink": 0,
                },
            },
        ),
    )


def download_action_icon(
    button_id,
    tooltip,
    color,
    background_color,
):
    return action_icon(
        button_id=button_id,
        tooltip=tooltip,
        icon="solar:download-minimalistic-linear",
        color=color,
        background_color=background_color,
        icon_width=19,
    )


def excel_action_icon(
    button_id,
    tooltip="Скачать Excel",
):
    return action_icon(
        button_id=button_id,
        tooltip=tooltip,
        icon="catppuccin:ms-excel",
        color="green",
        background_color=GREEN_BG,
        icon_width=20,
    )


def csv_action_icon(
    button_id,
    tooltip="Скачать CSV",
):
    return action_icon(
        button_id=button_id,
        tooltip=tooltip,
        icon="catppuccin:csv",
        color="blue",
        background_color=BLUE_BG,
        icon_width=20,
    )


# ============================================================
# БЛОК ПАНЕЛИ
# ============================================================

def panel_block(
    children,
    min_width=None,
    grow=False,
    border_right=True,
):
    style = {
        "minHeight": "68px",
        "padding": "10px 12px",
        "display": "flex",
        "alignItems": "center",
        "backgroundColor": "#FFFFFF",
        "boxSizing": "border-box",
    }

    if border_right:
        style["borderRight"] = f"1px solid {BLOCK_BORDER}"

    if min_width:
        style["minWidth"] = min_width

    if grow:
        style["flex"] = "1 1 auto"

    return html.Div(
        children=children,
        style=style,
    )


# ============================================================
# LOADING ДЛЯ АНАЛИЗА СЕБЕСТОИМОСТИ
# ============================================================

def loading_placeholder(component_id, color):
    return dcc.Loading(
        type="cube",
        color=color,
        fullscreen=True,
        children=html.Div(
            id=component_id,
            style={
                "width": "1px",
                "height": "34px",
                "overflow": "hidden",
            },
        ),
    )

# ============================================================
# ОСНОВНАЯ ПАНЕЛЬ
# ============================================================

def export_panel_main():
    yesterday = date.today() - timedelta(days=1)

    return dmc.Paper(
        withBorder=True,
        radius="sm",
        p=0,
        mb="sm",
        style={
            "backgroundColor": "#FFFFFF",
            "borderColor": PANEL_BORDER,
            "overflow": "hidden",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "stretch",
                    "width": "100%",
                    "overflowX": "auto",
                    "overflowY": "hidden",
                },
                children=[
                    # =================================================
                    # 1. ОСТАТКИ
                    # =================================================
panel_block(
    min_width="410px",
    children=dmc.Group(
        gap="sm",
        align="center",
        wrap="nowrap",
        children=[
            section_icon(
                icon="solar:box-linear",
                color=GREEN,
                background_color=GREEN_BG,
            ),

            section_title(
                title="Остатки",
                subtitle="На выбранную дату",
            ),

            dmc.DatePickerInput(
                id=STOCKS_DATE_PICKER_ID,
                value=yesterday,
                valueFormat="DD.MM.YYYY",
                clearable=False,
                radius="sm",
                size="xs",
                w=130,
                h=34,
                styles={
                    "input": {
                        "height": "34px",
                        "minHeight": "34px",
                        "fontSize": "12px",
                        "fontWeight": 500,
                        "borderColor": "#CED4DA",
                        "backgroundColor": "#FFFFFF",
                    },
                },
            ),

            dmc.Group(
                gap=4,
                align="center",
                wrap="nowrap",
                children=[
                    download_action_icon(
                        button_id=STOCKS_EXPORT_BTN_ID,
                        tooltip="Скачать остатки товаров",
                        color="green",
                        background_color=GREEN_BG,
                    ),

                    loading_placeholder(
                        component_id=STOCKS_EXPORT_LOADING_ID,
                        color=GREEN,
                    ),
                ],
            ),
        ],
    ),
),

                    # =================================================
                    # 2. АНАЛИЗ СЕБЕСТОИМОСТИ
                    # =================================================
                    panel_block(
                        min_width="250px",
                        children=dmc.Group(
                            gap="sm",
                            align="center",
                            wrap="nowrap",
                            children=[
                                section_icon(
                                    icon="solar:chart-square-linear",
                                    color=ORANGE,
                                    background_color=ORANGE_BG,
                                ),

                                section_title(
                                    title="С/сть",
                                    subtitle="Анализ отклонений",
                                ),

                                dmc.Group(
                                    gap=3,
                                    align="center",
                                    wrap="nowrap",
                                    children=[
                                        download_action_icon(
                                            button_id=PRICE_ANALYSIS_EXPORT_BTN_ID,
                                            tooltip=(
                                                "Скачать анализ себестоимости"
                                            ),
                                            color="orange",
                                            background_color=ORANGE_BG,
                                        ),

                                        loading_placeholder(
                                            component_id=PRICE_ANALYSIS_LOADING_ID,
                                            color=ORANGE,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),

                    # =================================================
                    # 3. ПЛАН WB
                    # =================================================
                    panel_block(
                        min_width="245px",
                        children=dmc.Group(
                            gap="sm",
                            align="center",
                            wrap="nowrap",
                            children=[
                                section_icon(
                                    icon="solar:chart-2-linear",
                                    color=VIOLET,
                                    background_color=VIOLET_BG,
                                ),

                                section_title(
                                    title="План WB",
                                    subtitle="Контроль выполнения",
                                ),

                                wb_plan_button(),
                            ],
                        ),
                    ),

                    # =================================================
                    # 4. AI-АНАЛИЗ
                    # =================================================
                    panel_block(
                        min_width="235px",
                        children=dmc.Group(
                            gap="sm",
                            align="center",
                            wrap="nowrap",
                            children=[
                                section_icon(
                                    icon="solar:magic-stick-3-linear",
                                    color=VIOLET,
                                    background_color=VIOLET_BG,
                                ),

                                section_title(
                                    title="AI-анализ",
                                    subtitle="Продажи и товары",
                                ),

                                ai_analysis_button(),
                            ],
                        ),
                    ),

                    # =================================================
                    # 5. ЭКСПОРТ ТАБЛИЦЫ
                    # =================================================
                    panel_block(
                        min_width="245px",
                        grow=True,
                        border_right=False,
                        children=dmc.Group(
                            gap="md",
                            align="center",
                            wrap="nowrap",
                            justify="space-between",
                            style={
                                "width": "100%",
                            },
                            children=[
                                dmc.Group(
                                    gap="sm",
                                    align="center",
                                    wrap="nowrap",
                                    children=[
                                        section_icon(
                                            icon=(
                                                "solar:"
                                                "download-minimalistic-linear"
                                            ),
                                            color=BLUE,
                                            background_color=BLUE_BG,
                                        ),

                                        section_title(
                                            title="Таблица",
                                            subtitle="Экспорт данных",
                                        ),
                                    ],
                                ),

                                dmc.Group(
                                    gap=8,
                                    align="center",
                                    wrap="nowrap",
                                    children=[
                                        excel_action_icon(
                                            button_id={
                                                "type": "main-dnl",
                                                "index": "xls",
                                            },
                                            tooltip=(
                                                "Скачать таблицу в Excel"
                                            ),
                                        ),

                                        csv_action_icon(
                                            button_id={
                                                "type": "main-dnl",
                                                "index": "csv",
                                            },
                                            tooltip=(
                                                "Скачать таблицу в CSV"
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),

            # =========================================================
            # DOWNLOAD И МОДАЛЬНЫЕ ОКНА
            # =========================================================
            dcc.Download(
                id="daily-sales-main-excel-download",
            ),

            dcc.Download(
                id=STOCKS_EXPORT_DOWNLOAD_ID,
            ),

            dcc.Download(
                id=PRICE_ANALYSIS_DOWNLOAD_ID,
            ),

    
            wb_plan_modal(),
            ai_analysis_modal(),
        ],
    )


# ============================================================
# ПАНЕЛЬ ДЕТАЛИЗАЦИИ
# ============================================================

def export_panel_details(date_value):
    return dmc.Paper(
        withBorder=True,
        radius="sm",
        p=0,
        mb="sm",
        style={
            "backgroundColor": "#FFFFFF",
            "borderColor": PANEL_BORDER,
            "overflow": "hidden",
        },
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                wrap="nowrap",
                gap="sm",
                px="sm",
                py=9,
                children=[
                    dmc.Group(
                        gap="sm",
                        align="center",
                        wrap="nowrap",
                        children=[
                            section_icon(
                                icon="solar:table-2-linear",
                                color=BLUE,
                                background_color=BLUE_BG,
                            ),

                            section_title(
                                title="Детализация",
                                subtitle="По выбранной дате",
                            ),
                        ],
                    ),

                    dmc.Group(
                        gap=8,
                        align="center",
                        wrap="nowrap",
                        children=[
                            excel_action_icon(
                                button_id={
                                    "type": "xls-dnl",
                                    "index": date_value,
                                },
                                tooltip="Скачать детализацию в Excel",
                            ),

                            csv_action_icon(
                                button_id={
                                    "type": "csv-dnl",
                                    "index": date_value,
                                },
                                tooltip="Скачать детализацию в CSV",
                            ),
                        ],
                    ),
                ],
            ),

            dcc.Download(
                id="daily-sales-details-excel-download",
            ),
        ],
    )