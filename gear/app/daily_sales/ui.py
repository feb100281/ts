# # gear/app/daily_sales/ui.py
# import dash_mantine_components as dmc
# from dash_iconify import DashIconify
# from dash import dcc, html
# from datetime import date, timedelta
# # from .wb_plan_monitor import wb_plan_button, wb_plan_modal
# from .wb_plan_monitor import wb_plan_button, wb_plan_modal



# STOCKS_DATE_PICKER_ID = "daily-sales-stocks-date-picker"
# STOCKS_EXPORT_BTN_ID = "daily-sales-stocks-export-btn"
# STOCKS_EXPORT_DOWNLOAD_ID = "daily-sales-stocks-export-download"
# STOCKS_EXPORT_LOADING_ID = "daily-sales-stocks-export-loading"



# def export_button(label, icon, button_id, color):
#     return dmc.Button(
#         label,
#         id=button_id,
#         leftSection=DashIconify(icon=icon, width=15, height=15),
#         variant="outline",
#         color=color,
#         radius="sm",
#         size="xs",
#         h=30,
#         px=10,
#         fw=700,
#         styles={
#             "label": {
#                 "fontSize": "12px",
#             },
#         },
#     )


# def export_section_title(icon, title, color):
#     return dmc.Group(
#         gap=6,
#         align="center",
#         children=[
#             DashIconify(
#                 icon=icon,
#                 width=16,
#                 height=16,
#                 color=color,
#             ),
#             dmc.Text(
#                 title,
#                 fw=700,
#                 size="xs",
#                 c="#212529",
#             ),
#         ],
#     )


# def export_panel_main():
#     yesterday = date.today() - timedelta(days=1)

#     return dmc.Paper(
#         withBorder=True,
#         radius="sm",
#         px="sm",
#         py=8,
#         mb="sm",
#         style={
#             "backgroundColor": "#ffffff",
#             "borderColor": "#e9ecef",
#         },
#         children=[
#             dmc.Group(
#                 justify="space-between",
#                 align="center",
#                 wrap="wrap",
#                 gap="sm",
#                 children=[
#                     dmc.Group(
#                         gap="md",
#                         align="center",
#                         wrap="wrap",
#                         children=[
#                             export_section_title(
#                                 "solar:box-linear",
#                                 "Остатки товаров",
#                                 "#40c057",
#                             ),
#                             dmc.DatePickerInput(
#                                 id=STOCKS_DATE_PICKER_ID,
#                                 value=yesterday,
#                                 valueFormat="DD.MM.YYYY",
#                                 clearable=False,
#                                 radius="sm",
#                                 size="xs",
#                                 w=135,
#                                 h=30,
#                                 styles={
#                                     "input": {
#                                         "height": "30px",
#                                         "minHeight": "30px",
#                                         "fontSize": "12px",
#                                     },
#                                 },
#                             ),
                      
                            
#                             dmc.Group(
#                                 gap=6,
#                                 align="center",
#                                 wrap="nowrap",
#                                 children=[
#                                     export_button(
#                                         "Скачать остатки",
#                                         "solar:download-outline",
#                                         STOCKS_EXPORT_BTN_ID,
#                                         "green",
#                                     ),
#                                     dcc.Loading(
#                                         type="cube",
#                                         children=html.Div(
#                                             id=STOCKS_EXPORT_LOADING_ID,
#                                             style={
#                                                 "width": "58px",
#                                                 "height": "58px",
#                                             },
#                                         ),
#                                     ),
#                                 ],
#                             ),
#                         ],
#                     ),

#                     dmc.Group(
#                         gap="xs",
#                         align="center",
#                         wrap="nowrap",
#                         children=[
#                             export_section_title(
#                                 "solar:table-2-linear",
#                                 "Таблица на экране",
#                                 "#228be6",
#                             ),
                            
#                             wb_plan_button(),
                            
#                             export_button(
#                                 "Excel",
#                                 "catppuccin:ms-excel",
#                                 {"type": "main-dnl", "index": "xls"},
#                                 "green",
#                             ),
#                             export_button(
#                                 "CSV",
#                                 "catppuccin:csv",
#                                 {"type": "main-dnl", "index": "csv"},
#                                 "blue",
#                             ),
#                         ],
#                     ),
#                 ],
#             ),

#             dcc.Download(id="daily-sales-main-excel-download"),
#             dcc.Download(id=STOCKS_EXPORT_DOWNLOAD_ID),
#             wb_plan_modal(),
#         ],
#     )


# def export_panel_details(date_value):
#     return dmc.Paper(
#         withBorder=True,
#         radius="sm",
#         px="sm",
#         py=8,
#         mb="sm",
#         style={
#             "backgroundColor": "#ffffff",
#             "borderColor": "#e9ecef",
#         },
#         children=[
#             dmc.Group(
#                 justify="space-between",
#                 align="center",
#                 wrap="wrap",
#                 gap="sm",
#                 children=[
#                     export_section_title(
#                         "solar:table-2-linear",
#                         "Детализация по выбранной дате",
#                         "#228be6",
#                     ),
#                     dmc.Group(
#                         gap="xs",
#                         children=[
#                             export_button(
#                                 "Excel",
#                                 "catppuccin:ms-excel",
#                                 {"type": "xls-dnl", "index": date_value},
#                                 "green",
#                             ),
#                             export_button(
#                                 "CSV",
#                                 "catppuccin:csv",
#                                 {"type": "csv-dnl", "index": date_value},
#                                 "blue",
#                             ),
#                         ],
#                     ),
#                 ],
#             ),
#             dcc.Download(id="daily-sales-details-excel-download"),
#         ],
#     )



# gear/app/daily_sales/ui.py

from datetime import date, timedelta

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from .wb_plan_monitor import wb_plan_button, wb_plan_modal
from .ai_analysis import ai_analysis_button, ai_analysis_modal


STOCKS_DATE_PICKER_ID = "daily-sales-stocks-date-picker"
STOCKS_EXPORT_BTN_ID = "daily-sales-stocks-export-btn"
STOCKS_EXPORT_DOWNLOAD_ID = "daily-sales-stocks-export-download"
STOCKS_EXPORT_LOADING_ID = "daily-sales-stocks-export-loading"


def export_button(label, icon, button_id, color):
    return dmc.Button(
        label,
        id=button_id,
        leftSection=DashIconify(
            icon=icon,
            width=15,
            height=15,
        ),
        variant="outline",
        color=color,
        radius="sm",
        size="xs",
        h=32,
        px=11,
        fw=700,
        styles={
            "label": {
                "fontSize": "12px",
            },
        },
    )


def export_section_title(icon, title, color):
    return dmc.Group(
        gap=7,
        align="center",
        wrap="nowrap",
        children=[
            DashIconify(
                icon=icon,
                width=17,
                height=17,
                color=color,
            ),
            dmc.Text(
                title,
                fw=700,
                size="sm",
                c="#212529",
                style={
                    "whiteSpace": "nowrap",
                },
            ),
        ],
    )


def vertical_divider():
    return dmc.Divider(
        orientation="vertical",
        size="xs",
        color="#dee2e6",
        style={
            "height": "34px",
            "alignSelf": "center",
        },
    )


def export_panel_main():
    yesterday = date.today() - timedelta(days=1)

    return dmc.Paper(
        withBorder=True,
        radius="sm",
        px="md",
        py=10,
        mb="sm",
        style={
            "backgroundColor": "#ffffff",
            "borderColor": "#dee2e6",
        },
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                wrap="wrap",
                gap="md",
                children=[
                    # -------------------------------------------------
                    # Левая часть:
                    # остатки + мониторинг плана WB
                    # -------------------------------------------------
                    dmc.Group(
                        gap="lg",
                        align="center",
                        wrap="wrap",
                        children=[
                            # Остатки товаров
                            dmc.Group(
                                gap="md",
                                align="center",
                                wrap="wrap",
                                children=[
                                    export_section_title(
                                        "solar:box-linear",
                                        "Остатки товаров",
                                        "#40c057",
                                    ),

                                    dmc.DatePickerInput(
                                        id=STOCKS_DATE_PICKER_ID,
                                        value=yesterday,
                                        valueFormat="DD.MM.YYYY",
                                        clearable=False,
                                        radius="sm",
                                        size="xs",
                                        w=140,
                                        h=32,
                                        styles={
                                            "input": {
                                                "height": "32px",
                                                "minHeight": "32px",
                                                "fontSize": "12px",
                                            },
                                        },
                                    ),

                                    dmc.Group(
                                        gap=6,
                                        align="center",
                                        wrap="nowrap",
                                        children=[
                                            export_button(
                                                "Скачать остатки",
                                                "solar:download-outline",
                                                STOCKS_EXPORT_BTN_ID,
                                                "green",
                                            ),

                                            dcc.Loading(
                                                type="cube",
                                                children=html.Div(
                                                    id=STOCKS_EXPORT_LOADING_ID,
                                                    style={
                                                        "width": "1px",
                                                        "height": "32px",
                                                    },
                                                ),
                                            ),
                                        ],
                                    ),
                                ],
                            ),

                            vertical_divider(),

                            # Мониторинг выполнения плана WB
                            dmc.Group(
                                gap="sm",
                                align="center",
                                wrap="nowrap",
                                children=[
                                    export_section_title(
                                        "solar:chart-2-linear",
                                        "Мониторинг плана WB",
                                        "#7950f2",
                                    ),
                                    wb_plan_button(),
                                ],
                            ),
                            
                            vertical_divider(),

                                dmc.Group(
                                    gap="sm",
                                    align="center",
                                    wrap="nowrap",
                                    children=[
                                        export_section_title(
                                            "solar:magic-stick-3-linear",
                                            "Умный анализ",
                                            "#7950f2",
                                        ),
                                        ai_analysis_button(),
                                    ],
                                ),
                        ],
                    ),

                    # -------------------------------------------------
                    # Правая часть:
                    # скачивание таблицы на экране
                    # -------------------------------------------------
                    dmc.Group(
                        gap="md",
                        align="center",
                        wrap="nowrap",
                        children=[
                            vertical_divider(),

                            export_section_title(
                                    "solar:download-minimalistic-linear",
                                    "Экспорт таблицы",
                                    "#228be6",
                                ),

                            dmc.Group(
                                gap="xs",
                                align="center",
                                wrap="nowrap",
                                children=[
                                    export_button(
                                        "Excel",
                                        "catppuccin:ms-excel",
                                        {
                                            "type": "main-dnl",
                                            "index": "xls",
                                        },
                                        "green",
                                    ),
                                    export_button(
                                        "CSV",
                                        "catppuccin:csv",
                                        {
                                            "type": "main-dnl",
                                            "index": "csv",
                                        },
                                        "blue",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),

            dcc.Download(id="daily-sales-main-excel-download"),
            dcc.Download(id=STOCKS_EXPORT_DOWNLOAD_ID),
            wb_plan_modal(),
            ai_analysis_modal(),
        ],
    )


def export_panel_details(date_value):
    return dmc.Paper(
        withBorder=True,
        radius="sm",
        px="sm",
        py=8,
        mb="sm",
        style={
            "backgroundColor": "#ffffff",
            "borderColor": "#e9ecef",
        },
        children=[
            dmc.Group(
                justify="space-between",
                align="center",
                wrap="wrap",
                gap="sm",
                children=[
                    export_section_title(
                        "solar:table-2-linear",
                        "Детализация по выбранной дате",
                        "#228be6",
                    ),

                    dmc.Group(
                        gap="xs",
                        align="center",
                        wrap="nowrap",
                        children=[
                            export_button(
                                "Excel",
                                "catppuccin:ms-excel",
                                {
                                    "type": "xls-dnl",
                                    "index": date_value,
                                },
                                "green",
                            ),
                            export_button(
                                "CSV",
                                "catppuccin:csv",
                                {
                                    "type": "csv-dnl",
                                    "index": date_value,
                                },
                                "blue",
                            ),
                        ],
                    ),
                ],
            ),

            dcc.Download(id="daily-sales-details-excel-download"),
        ],
    )