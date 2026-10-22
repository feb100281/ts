# gear/app/costs_control/article_report/callbacks.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from .data import get_article_history
from .excel import (
    build_excel_report,
    build_report_filename,
)
from .ids import (
    ARTICLE_REPORT_BTN_ID,
    ARTICLE_REPORT_CLOSE_BTN_ID,
    ARTICLE_REPORT_DOWNLOAD_BTN_ID,
    ARTICLE_REPORT_DOWNLOAD_ID,
    ARTICLE_REPORT_MODAL_ID,
    ARTICLE_REPORT_STATUS_ID,
    ARTICLE_REPORT_STORE_ID,
    ARTICLE_REPORT_UPLOAD_ID,
)
from .utils import (
    decode_upload_contents,
    read_articles_from_excel,
)


def _error_message(
    message: str,
):
    return dmc.Alert(
        title="Файл не обработан",
        color="red",
        variant="light",
        radius=0,
        icon=DashIconify(
            icon=(
                "solar:"
                "danger-triangle-linear"
            ),
            width=18,
        ),
        children=message,
    )


def _file_ready_message(
    filename: str,
    article_count: int,
):
    """
    Сообщение об успешной
    загрузке файла.
    """

    formatted_count = (
        f"{article_count:,}"
        .replace(
            ",",
            " ",
        )
    )

    return dmc.Alert(
        title="Файл готов к анализу",
        color="teal",
        variant="light",
        radius=0,
        icon=DashIconify(
            icon=(
                "solar:"
                "check-circle-linear"
            ),
            width=18,
        ),
        children=html.Div(
            children=[
                html.Div(
                    f"Файл: {filename}"
                ),

                html.Div(
                    (
                        "Уникальных артикулов: "
                        f"{formatted_count}"
                    ),
                    style={
                        "marginTop": "3px",
                    },
                ),

                html.Div(
                    (
                        "Нажмите "
                        "«Скачать анализ», "
                        "чтобы сформировать "
                        "отчёт."
                    ),
                    style={
                        "marginTop": "3px",
                    },
                ),
            ],
        ),
    )


def register_article_report_callbacks(
    app,
):
    """
    Регистрирует callbacks
    анализа артикулов.
    """

    # -------------------------------------------------------------
    # Открытие модалки
    # -------------------------------------------------------------

    @app.callback(
        Output(ARTICLE_REPORT_MODAL_ID, "opened"),
        Input(ARTICLE_REPORT_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def open_article_report_modal(
        n_clicks,
    ):
        if not n_clicks:
            raise PreventUpdate

        return True

    # -------------------------------------------------------------
    # Закрытие модалки
    # -------------------------------------------------------------

    @app.callback(
        Output(ARTICLE_REPORT_MODAL_ID, "opened", allow_duplicate=True),
        Input(ARTICLE_REPORT_CLOSE_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def close_article_report_modal(
        n_clicks,
    ):
        if not n_clicks:
            raise PreventUpdate

        return False

    # -------------------------------------------------------------
    # Проверка загруженного файла
    # -------------------------------------------------------------

    @app.callback(
        Output(ARTICLE_REPORT_STORE_ID, "data"),
        Output(ARTICLE_REPORT_STATUS_ID, "children"),
        Output(ARTICLE_REPORT_DOWNLOAD_BTN_ID, "disabled"),
        Input(ARTICLE_REPORT_UPLOAD_ID, "contents"),
        State(ARTICLE_REPORT_UPLOAD_ID, "filename"),
        prevent_initial_call=True,
    )
    def validate_article_file(
        contents,
        filename,
    ):
        if not contents:
            raise PreventUpdate

        if (
            not filename
            or not filename.lower().endswith(
                ".xlsx"
            )
        ):
            return (
                None,
                _error_message(
                    (
                        "Загрузите файл "
                        "в формате .xlsx."
                    )
                ),
                True,
            )

        try:
            file_bytes = (
                decode_upload_contents(
                    contents
                )
            )

            articles = (
                read_articles_from_excel(
                    file_bytes
                )
            )

            return (
                {
                    "articles": articles,
                    "filename": filename,
                },
                _file_ready_message(
                    filename=filename,
                    article_count=len(
                        articles
                    ),
                ),
                False,
            )

        except ValueError as exc:
            return (
                None,
                _error_message(
                    str(
                        exc
                    )
                ),
                True,
            )

        except Exception as exc:
            return (
                None,
                _error_message(
                    (
                        "При обработке файла "
                        "произошла ошибка: "
                        f"{exc}"
                    )
                ),
                True,
            )

    # -------------------------------------------------------------
    # Скачать Excel
    # -------------------------------------------------------------

    @app.callback(
        Output(ARTICLE_REPORT_DOWNLOAD_ID, "data"),
        Input(ARTICLE_REPORT_DOWNLOAD_BTN_ID, "n_clicks"),
        State(ARTICLE_REPORT_STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def download_article_report(
        n_clicks,
        stored_data,
    ):
        if (
            not n_clicks
            or not stored_data
        ):
            raise PreventUpdate

        articles = (
            stored_data.get(
                "articles",
                [],
            )
        )

        if not articles:
            raise PreventUpdate

        history_df = (
            get_article_history(
                articles
            )
        )

        report_bytes = (
            build_excel_report(
                articles=articles,
                history_df=history_df,
            )
        )

        report_filename = (
            build_report_filename()
        )

        def write_report(
            bytes_io,
        ):
            bytes_io.write(
                report_bytes
            )

        return dcc.send_bytes(
            write_report,
            report_filename,
        )