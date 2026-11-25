# #  gear/app/daily_sales/stocks/dashboard_stock/callbacks.py
# """Небольшие callbacks верхнего уровня dashboard."""

# from dash import dcc, Input, Output, State, no_update

# from ..transfer_excel import build_warehouses_excel
# from .ids import (
#     STOCK_WAREHOUSES_GRID_ID,
#     STOCK_PRODUCTS_COUNT_ID,
#     STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
#     STOCK_WAREHOUSES_DOWNLOAD_ID,
#     STOCK_CONTEXT_ID,
# )


# def register_main_callbacks(app):
#     @app.callback(
#         Output(
#             STOCK_PRODUCTS_COUNT_ID,
#             "children",
#         ),
#         Input(
#             STOCK_WAREHOUSES_GRID_ID,
#             "virtualRowData",
#         ),
#     )
#     def update_warehouse_count(
#         rows,
#     ):
#         return (
#             f"Показано складов: "
#             f"{len(rows or [])}"
#         )

#     @app.callback(
#         Output(
#             STOCK_WAREHOUSES_DOWNLOAD_ID,
#             "data",
#         ),
#         Input(
#             STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
#             "n_clicks",
#         ),
#         State(
#             STOCK_WAREHOUSES_GRID_ID,
#             "virtualRowData",
#         ),
#         State(
#             STOCK_CONTEXT_ID,
#             "data",
#         ),
#         prevent_initial_call=True,
#     )
#     def download_warehouses(
#         n_clicks,
#         rows,
#         context,
#     ):
#         if not n_clicks:
#             return no_update

#         context = context or {}

#         try:
#             content, filename = (
#                 build_warehouses_excel(
#                     rows=rows,
#                     report_date=context.get(
#                         "report_date"
#                     ),
#                 )
#             )
#         except ValueError:
#             return no_update

#         return dcc.send_bytes(
#             content,
#             filename,
#         )



#  gear/app/daily_sales/stocks/dashboard_stock/callbacks.py
"""Небольшие callbacks верхнего уровня dashboard."""

from dash import dcc, Input, Output, State, no_update

from ..transfer_excel import build_warehouses_excel
from ..incident_loss_export import (
    build_incident_loss_excel,
    build_incident_cover_letter_pdf,
    build_incident_compensation_excel,
)
from ..incident_compensation import lookup_subject_reference
from ..data import get_incident_potential_prices
from .incidents_panel import get_incident_events
from .ids import (
    STOCK_WAREHOUSES_GRID_ID,
    STOCK_PRODUCTS_COUNT_ID,
    STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
    STOCK_WAREHOUSES_DOWNLOAD_ID,
    STOCK_CONTEXT_ID,
    STOCK_INCIDENT_EXCEL_BTN_ID,
    STOCK_INCIDENT_EXCEL_DOWNLOAD_ID,
    STOCK_INCIDENT_PDF_BTN_ID,
    STOCK_INCIDENT_PDF_DOWNLOAD_ID,
    STOCK_INCIDENT_COMPENSATION_BTN_ID,
    STOCK_INCIDENT_COMPENSATION_DOWNLOAD_ID,
)


# Плательщик НДС по умолчанию для калькулятора ущерба (Оферта WB
# п. 11.3.5). Продавец подтвердил ставки 20/10% до 01.01.2026 и
# 22% начиная с этой даты — то есть компания является плательщиком
# НДС. Ставка по каждой позиции берётся отдельно (из карточки/
# истории продаж — stocks/data.py::get_incident_potential_prices),
# этот флаг влияет только на редактируемую колонку "Плательщик
# НДС?" по умолчанию в выгруженном Excel — при необходимости
# продавец меняет её построчно прямо в файле.
DEFAULT_IS_VAT_PAYER = True

# Действующая стандартная ставка НДС (с 01.01.2026). В истории
# продаж по некоторым позициям сохранена более старая ставка 20%
# (до повышения) либо ставка вовсе не записана (нет ни одной
# продажи в истории) — в обоих случаях для текущего расчёта
# компенсации берём актуальную стандартную ставку. Единственная
# ставка, которую НЕ подменяем, — льготная 10% (для товаров
# соответствующих категорий она фиксируется отдельно и не зависит
# от повышения общей ставки).
CURRENT_STANDARD_VAT_RATE_PCT = 22.0
PREFERENTIAL_VAT_RATE_PCT = 10.0


def _normalize_vat_rate(vat_rate_pct):
    """
    Приводит ставку НДС к актуальной: 10% (льготная) остаётся как
    есть, всё остальное (в т.ч. устаревшая историческая 20% и
    отсутствие данных, None) заменяется на текущую стандартную
    ставку 22%.
    """

    if vat_rate_pct is not None and abs(
        float(vat_rate_pct) - PREFERENTIAL_VAT_RATE_PCT
    ) < 0.01:
        return PREFERENTIAL_VAT_RATE_PCT

    return CURRENT_STANDARD_VAT_RATE_PCT


def _enrich_items_with_compensation_inputs(events, is_vat_payer):
    """
    Дополняет events[i]["items"][j] входными данными для формулы
    компенсации Оферты (Ц, К%, Нац%, ставка НДС) — см. docstring
    build_incident_compensation_excel в incident_loss_export.py.

    Мутирует переданные items на месте и возвращает events для
    удобства вызова в одну строку.
    """

    for event in events:
        items = event.get("items") or []

        if not items:
            continue

        snapshot = event.get("snapshot") or {}
        report_date = snapshot.get("effective_date")

        nm_ids = [
            item.get("nm_id")
            for item in items
            if item.get("nm_id") is not None
        ]

        price_map = {}

        if nm_ids and report_date:
            price_map = get_incident_potential_prices(
                nm_ids,
                report_date,
            )

        for item in items:
            nm_id = item.get("nm_id")

            price_info = None

            if nm_id is not None:
                try:
                    price_info = price_map.get(int(nm_id))
                except (TypeError, ValueError):
                    price_info = None

            price_info = price_info or {}

            subject_name = (
                price_info.get("subject_name")
                or item.get("subject_name")
            )

            reference = lookup_subject_reference(subject_name)

            item["subject_name"] = subject_name
            item["potential_price"] = price_info.get(
                "potential_price"
            )
            item["price_source"] = price_info.get("price_source")
            item["own_sales_count_365d"] = price_info.get(
                "own_sales_count_365d"
            )
            item["commission_pct"] = reference.get("commission_pct")
            item["markup_pct"] = reference.get("markup_pct")
            item["vat_rate_pct"] = _normalize_vat_rate(
                price_info.get("vat_rate_pct")
            )

    return events


def register_main_callbacks(app):
    @app.callback(
        Output(
            STOCK_PRODUCTS_COUNT_ID,
            "children",
        ),
        Input(
            STOCK_WAREHOUSES_GRID_ID,
            "virtualRowData",
        ),
    )
    def update_warehouse_count(
        rows,
    ):
        return (
            f"Показано складов: "
            f"{len(rows or [])}"
        )

    @app.callback(
        Output(
            STOCK_WAREHOUSES_DOWNLOAD_ID,
            "data",
        ),
        Input(
            STOCK_WAREHOUSES_DOWNLOAD_BTN_ID,
            "n_clicks",
        ),
        State(
            STOCK_WAREHOUSES_GRID_ID,
            "virtualRowData",
        ),
        State(
            STOCK_CONTEXT_ID,
            "data",
        ),
        prevent_initial_call=True,
    )
    def download_warehouses(
        n_clicks,
        rows,
        context,
    ):
        if not n_clicks:
            return no_update

        context = context or {}

        try:
            content, filename = (
                build_warehouses_excel(
                    rows=rows,
                    report_date=context.get(
                        "report_date"
                    ),
                )
            )
        except ValueError:
            return no_update

        return dcc.send_bytes(
            content,
            filename,
        )

    @app.callback(
        Output(
            STOCK_INCIDENT_EXCEL_DOWNLOAD_ID,
            "data",
        ),
        Input(
            STOCK_INCIDENT_EXCEL_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def download_incident_loss_excel(
        n_clicks,
    ):
        if not n_clicks:
            return no_update

        events = get_incident_events()

        if not events:
            return no_update

        content, filename = build_incident_loss_excel(events)

        return dcc.send_bytes(
            content,
            filename,
        )

    @app.callback(
        Output(
            STOCK_INCIDENT_PDF_DOWNLOAD_ID,
            "data",
        ),
        Input(
            STOCK_INCIDENT_PDF_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def download_incident_cover_letter(
        n_clicks,
    ):
        if not n_clicks:
            return no_update

        events = get_incident_events()

        if not events:
            return no_update

        content, filename = build_incident_cover_letter_pdf(events)

        return dcc.send_bytes(
            content,
            filename,
        )

    @app.callback(
        Output(
            STOCK_INCIDENT_COMPENSATION_DOWNLOAD_ID,
            "data",
        ),
        Input(
            STOCK_INCIDENT_COMPENSATION_BTN_ID,
            "n_clicks",
        ),
        prevent_initial_call=True,
    )
    def download_incident_compensation_excel(
        n_clicks,
    ):
        if not n_clicks:
            return no_update

        events = get_incident_events()

        if not events:
            return no_update

        events = _enrich_items_with_compensation_inputs(
            events,
            is_vat_payer=DEFAULT_IS_VAT_PAYER,
        )

        content, filename = build_incident_compensation_excel(
            events,
            is_vat_payer=DEFAULT_IS_VAT_PAYER,
        )

        return dcc.send_bytes(
            content,
            filename,
        )
