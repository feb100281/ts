# gear/app/misc/baners.py

import dash_mantine_components as dmc
from dash_iconify import DashIconify


BANNER_STYLE = {
    "maxWidth": "540px",
    "margin": "40px auto",
    "textAlign": "center",
}


def _banner(
    *,
    icon: str,
    icon_color: str,
    title: str,
    description: str,
    accent_text: str,
    accent_color: str,
    footer_text: str,
    max_width: str = "540px",
):
    return dmc.Paper(
        withBorder=True,
        shadow="md",
        radius="md",
        p="xl",
        style={
            **BANNER_STYLE,
            "maxWidth": max_width,
        },
        children=dmc.Stack(
            align="center",
            gap="sm",
            children=[
                DashIconify(
                    icon=icon,
                    width=64,
                    height=64,
                    color=icon_color,
                ),
                dmc.Title(
                    title,
                    order=2,
                    ta="center",
                ),
                dmc.Text(
                    description,
                    ta="center",
                    c="dimmed",
                    style={"whiteSpace": "pre-line"},
                ),
                dmc.Divider(w="100%"),
                dmc.Text(
                    accent_text,
                    ta="center",
                    fw=700,
                    c=accent_color,
                ),
                dmc.Text(
                    footer_text,
                    ta="center",
                    size="sm",
                    c="gray",
                    style={"whiteSpace": "pre-line"},
                ),
            ],
        ),
    )


def empty_df_banner():
    return _banner(
        icon="mdi:database-off",
        icon_color="#ff6b6b",
        title="Данных нет",
        description=(
            "Запрос вернул пустой DataFrame.\n"
            "Возможно, фильтры слишком строгие или данных действительно нет."
        ),
        accent_text="Проверьте параметры отчёта",
        accent_color="red",
        footer_text="Попробуйте ослабить фильтры или проверить источник данных.",
        max_width="520px",
    )


def in_construction_banner():
    return _banner(
        icon="mdi:tools",
        icon_color="#ffa94d",
        title="Раздел в работе",
        description=(
            "Эта часть дашборда сейчас находится в разработке."
         
        ),
        accent_text="Скоро будет доступно",
        accent_color="orange",
        footer_text="Раздел будет обновлён после завершения настройки логики.",
        max_width="540px",
    )
    
def in_construction_widjet():
    return _banner(
        icon="streamline:widget",
        icon_color="#ff4df0",
        title="Виджет в работе",
        description=(
            "Этот виджет сейчас находится в разработке."
         
        ),
        accent_text="Скоро будет доступно",
        accent_color="orange",
        footer_text="Виджет будет обновлён после завершения настройки логики.",
        max_width="540px",
    )