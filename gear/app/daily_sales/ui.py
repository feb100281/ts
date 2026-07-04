import dash_mantine_components as dmc
from dash_iconify import DashIconify


def export_button(label, icon, button_id, color):
    return dmc.Button(
        label,
        id=button_id,
        leftSection=DashIconify(
            icon=icon,
            width=16,
            height=16,
        ),
        variant="outline",
        color=color,
        radius=0,
        size="sm",
        h=34,
        px=14,
        fw=600,
        styles={
            "root": {
                "borderWidth": "1px",
            },
            "label": {
                "fontSize": "13px",
            },
        },
    )


def export_buttons_main():
    return dmc.Group(
        justify="flex-end",
        gap="xs",
        mb="sm",
        children=[
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
    )


def export_buttons_details(date_value):
    return dmc.Group(
        justify="flex-end",
        gap="xs",
        mb="sm",
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
    )