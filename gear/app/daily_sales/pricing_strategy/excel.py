
from __future__ import annotations

from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(color="FFFFFF", bold=True)
THIN = Side(style="thin", color="D1D5DB")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


RECOMMENDATION_COLUMNS = [
    ("priority", "Приоритет"),
    ("status", "Решение"),
    ("confidence_score", "Confidence, %"),
    ("nm_id", "NM ID"),
    ("sa_name", "Артикул"),
    ("brand", "Бренд"),
    ("category", "Категория"),
    ("gender", "Пол"),
    ("title", "Наименование"),
    ("current_seller_list_price", "Цена в карточке"),
    ("seller_price_30d", "Наша факт. цена 30д"),
    ("buyer_price_30d", "Цена покупателя 30д"),
    ("wb_price_delta_pct_30d", "Разница WB, %"),
    ("latest_seller_realized_price", "Последняя наша факт. цена"),
    ("latest_buyer_price", "Последняя цена покупателя"),
    ("recommended_change_pct", "Изменение нашей цены, %"),
    ("recommended_seller_price", "Рекомендованная наша цена"),
    ("recommended_buyer_price", "Прогноз цены покупателя"),
    ("amount_vatless_30d", "Выручка без НДС 30д"),
    ("cogs_man_30d", "FIFO с/с 30д"),
    ("net_comission_30d", "Комиссия WB 30д"),
    ("margin_man_30d", "Маржа 30д"),
    ("margin_pct_30d", "Маржа 30д, %"),
    ("recommended_margin_30d", "Маржа сценарий 30д"),
    ("recommended_margin_pct", "Маржа сценарий, %"),
    ("margin_upside_30d", "Потенциал маржи 30д"),
    ("margin_upside_day", "Потенциал маржи / день"),
    ("stock_on_hand", "Остаток"),
    ("stock_in_transit", "В пути"),
    ("stock_total", "Итого запас"),
    ("days_of_stock", "Запас, дней"),
    ("recommended_stock_days", "Запас после решения, дней"),
    ("stock_age_days", "Возраст товара, дней"),
    ("last_income_date", "Последний приход"),
    ("sales_qty_7d", "Продажи 7д"),
    ("sales_qty_30d", "Продажи 30д"),
    ("sales_qty_90d", "Продажи 90д"),
    ("daily_sales_qty_30d", "Продаж / день 30д"),
    ("sales_speed_trend_pct", "Тренд скорости 7д к 30д, %"),
    ("elasticity", "Эластичность"),
    ("elasticity_r2", "R²"),
    ("elasticity_observations", "Наблюдений"),
    ("price_cv_pct", "CV цены покупателя, %"),
    ("elasticity_confidence", "Надёжность"),
    ("reason", "Почему"),
]


SCENARIO_COLUMNS = [
    ("nm_id", "NM ID"),
    ("brand", "Бренд"),
    ("title", "Наименование"),
    ("price_change_pct", "Δ нашей цены, %"),
    ("seller_price", "Наша цена"),
    ("buyer_price", "Цена покупателя"),
    ("wb_factor", "Коэффициент WB"),
    ("projected_qty", "Прогноз продаж 30д"),
    ("qty_change_pct", "Изменение количества, %"),
    ("projected_daily_qty", "Продаж / день"),
    ("projected_revenue_net", "Выручка без НДС"),
    ("projected_margin", "Маржа"),
    ("projected_margin_pct", "Маржа, %"),
    ("margin_change_pct", "Изменение маржи, %"),
    ("projected_stock_days", "Запас, дней"),
    ("is_margin_safe", "Маржа выше минимума"),
]


HISTORY_COLUMNS = [
    ("date_from", "Дата"),
    ("nm_id", "NM ID"),
    ("brand", "Бренд"),
    ("category", "Категория"),
    ("title", "Наименование"),
    ("sales_qty", "Продажи"),
    ("returns_qty", "Возвраты"),
    ("net_qty", "Чистое количество"),
    ("seller_sales_amount", "Наша выручка продаж"),
    ("wb_sales_amount", "Реализация WB продаж"),
    ("amount", "Наша чистая выручка с НДС"),
    ("retail_amount", "WB чистая реализация с НДС"),
    ("seller_price", "Наша факт. цена"),
    ("buyer_price", "Цена покупателя"),
    ("wb_price_delta_pct", "Разница WB, %"),
    ("amount_vatless", "Наша выручка без НДС"),
    ("cogs_man", "FIFO с/с"),
    ("net_comission", "Комиссия WB"),
    ("margin_man", "Маржа"),
    ("margin_pct", "Маржа, %"),
]


def _excel_value(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if (
        hasattr(value, "isoformat")
        and not isinstance(value, str)
    ):
        try:
            return value.isoformat()
        except Exception:
            pass

    return value


def write_frame(ws, frame, columns):
    for column_index, (_, title) in enumerate(columns, 1):
        cell = ws.cell(1, column_index, title)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    for row_index, (_, row) in enumerate(frame.iterrows(), 2):
        for column_index, (field, _) in enumerate(columns, 1):
            cell = ws.cell(
                row_index,
                column_index,
                _excel_value(row.get(field)),
            )
            cell.border = BORDER
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=field in ("title", "reason"),
            )

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.row_dimensions[1].height = 32

    for index, (field, title) in enumerate(columns, 1):
        if field == "reason":
            width = 72
        elif field == "title":
            width = 38
        elif field in ("brand", "category"):
            width = 20
        else:
            width = max(12, min(len(title) + 2, 24))

        ws.column_dimensions[get_column_letter(index)].width = width


def build_pricing_excel(payload: dict) -> bytes:
    recommendations = pd.DataFrame(
        payload.get("recommendations") or []
    )
    scenarios = pd.DataFrame(
        payload.get("scenarios") or []
    )
    history = pd.DataFrame(
        payload.get("history") or []
    )

    workbook = Workbook()

    ws = workbook.active
    ws.title = "Рекомендации"
    write_frame(
        ws,
        recommendations,
        RECOMMENDATION_COLUMNS,
    )

    ws2 = workbook.create_sheet("Сценарии")
    write_frame(
        ws2,
        scenarios,
        SCENARIO_COLUMNS,
    )

    ws3 = workbook.create_sheet("История")
    write_frame(
        ws3,
        history,
        HISTORY_COLUMNS,
    )

    ws4 = workbook.create_sheet("Методология")

    rows = [
        ("Дата анализа", payload.get("report_date")),
        ("Дата остатков", payload.get("stock_date")),
        ("Начало истории", payload.get("history_start")),
        (
            "Цена спроса",
            (
                "buyer_price = retail_amount / число положительных продаж. "
                "Это фактическая стоимость реализации WB покупателю."
            ),
        ),
        (
            "Наша цена",
            (
                "seller_price = положительный cr_rev / число продаж."
            ),
        ),
        (
            "Эластичность",
            (
                "ln(Q) = a + b * ln(buyer_price). "
                "Используется именно цена покупателя."
            ),
        ),
        (
            "Маржа",
            (
                "margin_man = amount_vatless - FIFO cogs_man + net_comission."
            ),
        ),
        (
            "Что не входит",
            (
                "Маркетинг, штрафы, хранение и прочие распределяемые "
                "недельные расходы WB."
            ),
        ),
        (
            "Сценарий WB",
            (
                "В сценариях текущий коэффициент buyer_price / seller_price "
                "условно сохраняется. Это рабочее допущение, а не гарантия СПП."
            ),
        ),
        (
            "Статус TEST",
            (
                "Данных или вариации цены недостаточно для уверенной "
                "оценки эластичности; рекомендуется ограниченный ценовой тест."
            ),
        ),
    ]

    ws4["A1"] = "Параметр"
    ws4["B1"] = "Описание"

    for cell in ws4[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER

    for index, (key, value) in enumerate(rows, 2):
        ws4.cell(index, 1, key).border = BORDER

        cell = ws4.cell(index, 2, value)
        cell.border = BORDER
        cell.alignment = Alignment(
            wrap_text=True,
            vertical="top",
        )

    ws4.column_dimensions["A"].width = 25
    ws4.column_dimensions["B"].width = 110
    ws4.freeze_panes = "A2"

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()
