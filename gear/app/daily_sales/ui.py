# gear/app/daily_sales/ui.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html
from datetime import date, timedelta



STOCKS_DATE_PICKER_ID = "daily-sales-stocks-date-picker"
STOCKS_EXPORT_BTN_ID = "daily-sales-stocks-export-btn"
STOCKS_EXPORT_DOWNLOAD_ID = "daily-sales-stocks-export-download"
STOCKS_EXPORT_LOADING_ID = "daily-sales-stocks-export-loading"



def export_button(label, icon, button_id, color):
    return dmc.Button(
        label,
        id=button_id,
        leftSection=DashIconify(icon=icon, width=15, height=15),
        variant="outline",
        color=color,
        radius="sm",
        size="xs",
        h=30,
        px=10,
        fw=700,
        styles={
            "label": {
                "fontSize": "12px",
            },
        },
    )


def export_section_title(icon, title, color):
    return dmc.Group(
        gap=6,
        align="center",
        children=[
            DashIconify(
                icon=icon,
                width=16,
                height=16,
                color=color,
            ),
            dmc.Text(
                title,
                fw=700,
                size="xs",
                c="#212529",
            ),
        ],
    )


def export_panel_main():
    yesterday = date.today() - timedelta(days=1)

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
                                w=135,
                                h=30,
                                styles={
                                    "input": {
                                        "height": "30px",
                                        "minHeight": "30px",
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
                                                "width": "58px",
                                                "height": "58px",
                                            },
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),

                    dmc.Group(
                        gap="xs",
                        align="center",
                        wrap="nowrap",
                        children=[
                            export_section_title(
                                "solar:table-2-linear",
                                "Таблица на экране",
                                "#228be6",
                            ),
                            export_button(
                                "Excel",
                                "catppuccin:ms-excel",
                                {"type": "main-dnl", "index": "xls"},
                                "green",
                            ),
                            export_button(
                                "CSV",
                                "catppuccin:csv",
                                {"type": "main-dnl", "index": "csv"},
                                "blue",
                            ),
                        ],
                    ),
                ],
            ),

            dcc.Download(id="daily-sales-main-excel-download"),
            dcc.Download(id=STOCKS_EXPORT_DOWNLOAD_ID),
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
                        children=[
                            export_button(
                                "Excel",
                                "catppuccin:ms-excel",
                                {"type": "xls-dnl", "index": date_value},
                                "green",
                            ),
                            export_button(
                                "CSV",
                                "catppuccin:csv",
                                {"type": "csv-dnl", "index": date_value},
                                "blue",
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Download(id="daily-sales-details-excel-download"),
        ],
    )