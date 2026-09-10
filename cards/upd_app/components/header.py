# # cards/upd_app/components/header.py

# import dash_mantine_components as dmc
# from dash import dcc


# def build_upd_header(upd):

#     return dmc.Paper(
#         [
#             dmc.Group(
#                 [
#                     dmc.Group(
#                         [
#                             dmc.Text(
#                                 f"УПД №{upd.number}",
#                                 fw=700,
#                                 size="24px",
#                             ),

#                             dmc.Badge(
#                                 upd.date.strftime("%d.%m.%Y"),
#                                 color="gray",
#                                 variant="outline",
#                                 size="md",
#                                 radius="sm",
#                             ),
#                         ],
#                         gap="sm",
#                         align="center",
#                     ),

#                     dmc.Group(
#                         [
#                             dmc.Badge(
#                                 str(upd.counterparty),
#                                 color="blue",
#                                 variant="outline",
#                                 size="lg",
#                                 radius="sm",
#                             ),

#                             dcc.Upload(
#                                 id="upd-upload",
#                                 multiple=False,
#                                 accept=".parquet",
#                                 children=dmc.Button(
#                                     "📦 parquet",
#                                     variant="light",
#                                     color="green",
#                                 ),
#                             ),

#                             dmc.Text(
#                                 "Файл не выбран",
#                                 id="upload-filename",
#                                 size="sm",
#                                 c="dimmed",
#                                 maw=220,
#                                 truncate="end",
#                             ),

#                             dmc.Button(
#                                 "Импорт",
#                                 id="import-upd-btn",
#                                 color="blue",
#                             ),
#                         ],
#                         gap="sm",
#                         align="center",
#                     ),
#                 ],
#                 justify="space-between",
#                 align="center",
#             ),
#         ],
#         p="md",
#         radius="md",
#         withBorder=True,
#         mb="lg",
#     )



# cards/upd_app/components/header.py

import dash_mantine_components as dmc
from dash import dcc, html


def build_upd_header(upd):

    return dmc.Paper(
        [
            dmc.Group(
                [
                    dmc.Group(
                            [
                                dmc.Text(
                                    f"УПД №{upd.number}",
                                    fw=700,
                                    size="24px",
                                ),

                                dmc.Badge(
                                    upd.date.strftime(
                                        "%d.%m.%Y"
                                    ),
                                    color="gray",
                                    variant="outline",
                                    size="md",
                                    radius="sm",
                                ),

                                dmc.Badge(
                                    f"ID {upd.id}",
                                    color="blue",
                                    variant="light",
                                    size="md",
                                    radius="sm",
                                ),
                            ],
                            gap="sm",
                            align="center",
                        ),

                    # =================================================
                    # ЗАГРУЗКА ОСНОВНОГО PARQUET
                    # =================================================

                    dmc.Group(
                        [
                            dcc.Upload(
                                id="upd-upload",
                                multiple=False,
                                accept=".parquet",
                                children=dmc.Button(
                                    "📦 Parquet",
                                    variant="light",
                                    color="green",
                                ),
                            ),

                            dmc.Text(
                                "Файл не выбран",
                                id="upload-filename",
                                size="sm",
                                c="dimmed",
                                maw=190,
                                truncate="end",
                            ),

                            dmc.Button(
                                "Импорт",
                                id="import-upd-btn",
                                color="blue",
                            ),
                        ],
                        gap="sm",
                        align="center",
                    ),
                ],
                justify="space-between",
                align="center",
            ),

            # =========================================================
            # ОТДЕЛЬНЫЙ БЛОК УПРАВЛЕНЧЕСКОЙ СЕБЕСТОИМОСТИ
            # =========================================================

            dmc.Divider(
                my="md",
                color="gray.3",
            ),

            dmc.Group(
                [
                    dmc.Group(
                        [
                            dmc.ThemeIcon(
                                html.I(
                                    className=(
                                        "fa-solid "
                                        "fa-file-excel"
                                    )
                                ),
                                color="teal",
                                variant="light",
                                size=38,
                                radius="sm",
                            ),

                            dmc.Stack(
                                [
                                    dmc.Text(
                                        "Управленческая себестоимость",
                                        fw=700,
                                        size="sm",
                                    ),

                                    dmc.Text(
                                        (
                                            "Excel · лист УПД · "
                                            "ID в колонке A · "
                                            "себестоимость в колонке L"
                                        ),
                                        size="xs",
                                        c="dimmed",
                                    ),
                                ],
                                gap=1,
                            ),
                        ],
                        gap="sm",
                        align="center",
                    ),

                    dmc.Group(
                        [
                            dcc.Upload(
                                id="man-cost-upload",
                                multiple=False,
                                accept=".xlsx",
                                children=dmc.Button(
                                    "Выбрать Excel",
                                    leftSection=html.I(
                                        className=(
                                            "fa-solid "
                                            "fa-file-arrow-up"
                                        )
                                    ),
                                    variant="light",
                                    color="teal",
                                ),
                            ),

                            dmc.Text(
                                "Файл не выбран",
                                id="man-cost-filename",
                                size="sm",
                                c="dimmed",
                                maw=220,
                                truncate="end",
                            ),

                            dmc.Button(
                                "Обновить с/сть",
                                id="import-man-cost-btn",
                                leftSection=html.I(
                                    className=(
                                        "fa-solid "
                                        "fa-calculator"
                                    )
                                ),
                                color="teal",
                            ),
                        ],
                        gap="sm",
                        align="center",
                    ),
                ],
                justify="space-between",
                align="center",
            ),

            html.Div(
                id="man-cost-alert-slot",
                style={
                    "marginTop": "12px",
                },
            ),
        ],
        p="md",
        radius="md",
        withBorder=True,
        mb="lg",
    )
