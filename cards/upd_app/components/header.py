# cards/upd_app/components/header.py

import dash_mantine_components as dmc
from dash import dcc


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
                                upd.date.strftime("%d.%m.%Y"),
                                color="gray",
                                variant="outline",
                                size="md",
                                radius="sm",
                            ),
                        ],
                        gap="sm",
                        align="center",
                    ),

                    dmc.Group(
                        [
                            dmc.Badge(
                                str(upd.counterparty),
                                color="blue",
                                variant="outline",
                                size="lg",
                                radius="sm",
                            ),

                            dcc.Upload(
                                id="upd-upload",
                                multiple=False,
                                accept=".parquet",
                                children=dmc.Button(
                                    "📦 parquet",
                                    variant="light",
                                    color="green",
                                ),
                            ),

                            dmc.Text(
                                "Файл не выбран",
                                id="upload-filename",
                                size="sm",
                                c="dimmed",
                                maw=220,
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
        ],
        p="md",
        radius="md",
        withBorder=True,
        mb="lg",
    )
