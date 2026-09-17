# gear/app/daily_sales/fbs_orders/export.py
"""
Скачивание анализа заказов FBS в Excel.
"""

from __future__ import annotations

from datetime import datetime

from dash import (
    MATCH,
    Input,
    Output,
    Patch,
    State,
    dcc,
    no_update,
)

from .config import (
    FBS_EXPORT_BTN_ID,
    FBS_EXPORT_DOWNLOAD_ID,
    FBS_EXPORT_LOADING_ID,
    FBS_RELOAD_BTN_ID,
)
from .data import FbsData, FbsSourceMissing, collect_fbs_analysis
from .excel import make_fbs_excel


def _fmt_date(value):
    if value in (None, ""):
        return None

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None

    if isinstance(value, datetime):
        return value.date()

    return value


def _selection_text(values, all_text):
    if not values:
        return all_text

    if not isinstance(values, (list, tuple, set)):
        values = [values]

    values = [str(v) for v in values if v not in (None, "")]

    if not values:
        return all_text

    if len(values) <= 4:
        return ", ".join(values)

    return f"выбрано: {len(values)}"


def build_fbs_excel(
    date_range=None,
    cat_list=None,
    brand_list=None,
    gender_list=None,
) -> tuple[bytes, str]:
    """
    Собирает книгу и возвращает содержимое и имя файла.

    Вынесено отдельно от callback, чтобы этим же кодом можно
    было пользоваться из management-команды или из админки.
    """
    start = end = None

    if date_range and len(date_range) == 2:
        start = _fmt_date(date_range[0])
        end = _fmt_date(date_range[1])

    if not (start and end):
        start = end = None
        period_text = "не выбран — вся история"
    else:
        period_text = (
            f"{start:%d.%m.%Y} – {end:%d.%m.%Y}"
        )

    filters = {
        "start": start,
        "end": end,
        "cat_list": cat_list,
        "brand_list": brand_list,
        "gender_list": gender_list,
    }

    payload = collect_fbs_analysis(**filters)

    # Построчную выгрузку берём отдельным заходом: она нужна
    # только в Excel и на дашборде не показывается.
    with FbsData() as fbs:
        raw_df = fbs.get_raw(**filters)

    meta = {
        "period": period_text,
        "brand": _selection_text(brand_list, "все"),
        "category": _selection_text(cat_list, "все"),
        "gender": _selection_text(gender_list, "любой"),
    }

    content = make_fbs_excel(payload, meta, raw_df=raw_df)

    file_name = (
        "fbs_orders_"
        f"{payload['as_of']:%Y-%m-%d}"
        ".xlsx"
    )

    return content, file_name


def register_fbs_search_callback(app):
    """
    Поиск по таблице.

    Один колбэк на все таблицы вкладки: id полей и таблиц
    согласованы по index, поэтому MATCH связывает каждое поле
    ровно со своей таблицей.

    Отдаём Patch, а не весь набор настроек: иначе обновление
    затёрло бы закреплённую строку итогов и постраничный вывод.
    """
    from .layout import GRID_TYPE, SEARCH_TYPE

    @app.callback(
        Output(
            {"type": GRID_TYPE, "index": MATCH},
            "dashGridOptions",
        ),
        Input(
            {"type": SEARCH_TYPE, "index": MATCH},
            "value",
        ),
        prevent_initial_call=True,
    )
    def apply_quick_filter(value):
        options = Patch()
        options["quickFilterText"] = value or ""
        return options


def register_fbs_reload_callback(app):
    """
    Кнопка «Обновить» перезагружает страницу.

    Намеренно не дёргает API Wildberries: полная выгрузка
    заказов идёт минутами, пишет в ту же базу, из которой
    читает сайт, и висящий колбэк упёрся бы в таймаут
    gunicorn — воркер убивают, страница остаётся в старом
    состоянии. Поэтому кнопка только перечитывает то, что
    уже загружено, а сама загрузка живёт в расписании.
    """
    app.clientside_callback(
        """
        function (n_clicks) {
            if (n_clicks) {
                window.location.reload();
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output(FBS_RELOAD_BTN_ID, "n_clicks"),
        Input(FBS_RELOAD_BTN_ID, "n_clicks"),
        prevent_initial_call=True,
    )


def register_fbs_export_callbacks(
    app,
    date_picker_id,
    cat_multy_id,
    brand_multy_id,
    gender_multy_id,
):
    @app.callback(
        Output(FBS_EXPORT_DOWNLOAD_ID, "data"),
        Output(FBS_EXPORT_LOADING_ID, "children"),
        Input(FBS_EXPORT_BTN_ID, "n_clicks"),
        State(date_picker_id, "value"),
        State(cat_multy_id, "value"),
        State(brand_multy_id, "value"),
        State(gender_multy_id, "value"),
        prevent_initial_call=True,
    )
    def export_fbs_orders(
        n_clicks,
        date_range,
        cat_list,
        brand_list,
        gender_list,
    ):
        if not n_clicks:
            return no_update, no_update

        try:
            content, file_name = build_fbs_excel(
                date_range=date_range,
                cat_list=cat_list,
                brand_list=brand_list,
                gender_list=gender_list,
            )
        except FbsSourceMissing:
            # Витрины нет — на вкладке уже висит объяснение,
            # молча ничего не отдаём.
            return no_update, ""

        return (
            dcc.send_bytes(content, filename=file_name),
            "",
        )
