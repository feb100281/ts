# gear/app/daily_sales/wb_expenses_excel.py
"""
Экспорт "Анализ расходов WB по неделям и статьям" в Excel.

Категоризация (account / cost_item) зеркалит
management/commands/sql/wb_costs.sql -- сам файл не трогаем (там
"не меняй запросы!!!"), здесь та же логика на sales.sales_long,
своим запросом, но с дополнительной детализацией, которой в
wb_costs.sql нет и которая нужна только здесь: nm_id, наименование
карточки, rrd_id, sop_name, btn -- на уровне отдельной строки.

Конвенция знака и НДС -- та же, что и в
commercial_review/data.py::_wb_expenses_sql и в
management/commands/sql/opex.sql:

    сумма_руб = (dt - cr) / (100 + COALESCE(vat_rate, 20)) * 100 / 100

где dt = SUM(val) по строкам с oper='dt', cr = SUM(val) по строкам
с oper='cr'. На уровне одной строки (у строки ровно один oper) это
арифметически то же самое, что:

    signed = val, если oper='dt', иначе -val
    сумма_руб = signed / (100 + COALESCE(vat_rate, 20)) * 100 / 100

-- этой построчной формулой и считаем, а суммы по любому срезу
(день, неделя, месяц, статья) получаются обычным SUM() по строкам,
без переагрегации.

Период -- обычный date-picker дашборда "Продажи" (FILTERS.date_picker_id),
тот же, что и у выгрузки "Контроль качества". Ничего своего для выбора
периода здесь нет и не нужно. Период не выбран -- значит весь период:
с начала истории (как и в остальных выгрузках дашборда) по сегодня.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, no_update

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from . import excel_report_style as style

#: Начало истории для выгрузок без выбранного периода -- то же,
#: что и в quality_control_export.py/register_quality_control_export_callbacks.
HISTORY_START = date(2024, 1, 1)


# ================================================================ ID's
WB_EXPENSES_EXPORT_ITEM_ID = "wb-expenses-export-item"
WB_EXPENSES_EXPORT_DOWNLOAD_ID = "wb-expenses-export-download"
WB_EXPENSES_EXPORT_STATUS_ID = "wb-expenses-export-status"
WB_EXPENSES_EXPORT_CLICKS_ID = "wb-expenses-export-clicks"

# Пункты меню "Экспорт" в дашборде "Продажи". Пока один пункт --
# задел под будущие отчёты того же меню (Дарья: "потом ещё будем
# добавлять что скачивать").
EXPORT_MENU_KINDS = (
    ("wb_expenses", WB_EXPENSES_EXPORT_ITEM_ID),
)


# ================================================================ категории (= wb_costs.sql)
#: (account, sql-условие WHERE, SQL-выражение для cost_item).
#: Точь-в-точь account/cost_item из management/commands/sql/wb_costs.sql
#: -- чтобы итоги этой выгрузки сходились со сквозным управленческим
#: учётом (opex.sql), который читает ту же категоризацию.
WB_EXPENSE_ACCOUNTS = (
    (
        "3.1 Логистика",
        "field = 'delivery_rub'",
        """
        CASE
            WHEN COALESCE(btn, sop_name) ILIKE '%при продаже%'
                THEN 'Логистика продажи'
            WHEN COALESCE(btn, sop_name) ILIKE '%отмен%'
                THEN 'Логистика отмен'
            WHEN COALESCE(btn, sop_name) ILIKE '%брак%'
                THEN 'Возврат брака'
            WHEN COALESCE(btn, sop_name) ILIKE '%возврат%'
                THEN 'Возвраты'
            WHEN COALESCE(btn, sop_name) ILIKE '%коррекц%'
              OR COALESCE(btn, sop_name) ILIKE '%коэффициент%'
                THEN 'Коррекции логистики'
            ELSE 'Прочие'
        END
        """,
    ),
    (
        "3.2. Хранение",
        "field = 'storage_fee'",
        "sop_name",
    ),
    (
        "3.3. Приемка",
        "field = 'acceptance'",
        "sop_name",
    ),
    (
        "3.4. Штрафы",
        "field = 'penalty'",
        """
        CASE
            WHEN btn ILIKE '%габарит%'
              OR btn ILIKE '%обмер%'
                THEN 'Габариты товара'
            WHEN btn ILIKE '%расхождени%карточк%'
                THEN 'Расхождения в карточке товара'
            WHEN btn ILIKE '%хранени%возврат%'
                THEN 'Хранение возвратов'
            WHEN btn ILIKE '%подмен%товар%'
                THEN 'Подмена товара'
            WHEN btn ILIKE '%недовоз%'
              OR btn ILIKE '%срок%передач%'
              OR btn ILIKE '%невыполненн%заказ%'
                THEN 'Нарушения поставки'
            ELSE 'Прочие штрафы'
        END
        """,
    ),
    (
        "WB Deduction",
        "field = 'deduction' "
        "AND btn IS NOT NULL "
        "AND NOT STARTS_WITH(btn, 'Платеж') "
        "AND NOT STARTS_WITH(btn, 'Перевод')",
        """
        CASE
            WHEN STARTS_WITH(btn, 'Списание за отзыв')
                THEN '4.2. Отзывы'
            WHEN STARTS_WITH(btn, 'Оказание услуг')
              OR STARTS_WITH(btn, 'Предоставление услуг')
              OR STARTS_WITH(btn, 'Витрина Магазина')
                THEN '4.1. Услуги WB'
            ELSE '4.3. Прочее'
        END
        """,
    ),
    (
        "3.6. Программа лояльности",
        "field IN ('cashback_commission_change', 'cashback_amount')",
        "btn",
    ),
)

# Понятные ярлыки для строгих кодов account -- используются в
# заголовках строк, сами коды остаются в данных для сверки с
# opex.sql/wb_costs.sql.
ACCOUNT_LABELS = {
    "3.1 Логистика": "3.1 Логистика",
    "3.2. Хранение": "3.2. Хранение",
    "3.3. Приемка": "3.3. Приёмка",
    "3.4. Штрафы": "3.4. Штрафы",
    "WB Deduction": "3.5. Продвижение и услуги WB (WB Deduction)",
    "3.6. Программа лояльности": "3.6. Программа лояльности",
}


def _detail_sql() -> str:
    branches = []
    for account, condition, cost_item_sql in WB_EXPENSE_ACCOUNTS:
        branches.append(
            f"""
            SELECT
                date_from,
                rrd_id,
                nm_id,
                sop_name,
                btn,
                oper,
                val,
                vat_rate,
                '{account}' AS account,
                ({cost_item_sql}) AS cost_item
            FROM sales.sales_long
            WHERE {condition}
              AND date_from::DATE BETWEEN $start_date AND $end_date
            """
        )

    union = "\n\nUNION ALL\n".join(branches)

    return f"""
        WITH detail AS ({union})

        SELECT
            d.date_from::DATE AS date_from,
            d.rrd_id,
            d.nm_id,
            COALESCE(NULLIF(TRIM(p.title), ''), 'Без наименования') AS title,
            COALESCE(NULLIF(TRIM(p.brand), ''), 'Не указан') AS brand,
            d.account,
            d.cost_item,
            d.sop_name,
            d.btn,
            d.oper,
            d.val,
            d.vat_rate,

            (CASE WHEN d.oper = 'dt' THEN d.val ELSE -d.val END)
                / (100 + COALESCE(d.vat_rate, 20)) * 100 / 100
                AS amount_rub

        FROM detail d
        LEFT JOIN inventories.wb_product p
            ON p.card_id = d.nm_id

        ORDER BY
            d.date_from,
            d.rrd_id
    """


def fetch_wb_expenses_detail(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Одна строка sales.sales_long = одна строка результата --
    максимальная детализация: rrd_id, nm_id, наименование карточки,
    account/cost_item, sop_name, btn, знак операции, сумма без НДС.
    """
    from conns import get_duckdb_conn_with_opt

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            _detail_sql(),
            {"start_date": start_date, "end_date": end_date},
        ).df()

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "date_from", "rrd_id", "nm_id", "title", "brand",
                "account", "cost_item", "sop_name", "btn", "oper",
                "val", "vat_rate", "amount_rub",
            ]
        )

    df["date_from"] = pd.to_datetime(df["date_from"]).dt.date
    df["account_label"] = df["account"].map(
        lambda a: ACCOUNT_LABELS.get(a, a)
    )

    # У "3.2. Хранение"/"3.3. Приемка" cost_item = sop_name, у
    # "3.6. Программа лояльности" -- btn: оба сырые колонки sales_long
    # и могут быть NULL. pandas groupby (используется и в
    # _hierarchy_order, и в _pivot_amounts) по умолчанию МОЛЧА
    # выбрасывает строки с NaN в ключе группировки -- то есть такие
    # строки исчезали бы из разделов/статей и из сумм всех
    # листов-пивотов, а карточка "Расходы WB за период" на Оглавлении
    # считает total = df["amount_rub"].sum() по сырому df и эти же
    # строки честно включает. Отсюда и расхождение итогов.
    #
    # Вместо общей заглушки вроде "Без уточнения" -- достаём статью
    # из второго поля: если пусто btn, берём sop_name (и наоборот,
    # если у какой-то строки cost_item пуст, а btn всё-таки есть --
    # он и останется). Если оба поля у строки совпадают, coalesce
    # просто берёт значение один раз -- задвоения строки не будет.
    # "Без уточнения" -- уже самый последний случай, когда пустуют
    # оба поля сразу.
    df["cost_item"] = (
        df["cost_item"]
        .fillna(df["btn"])
        .fillna(df["sop_name"])
        .fillna("Без уточнения")
    )

    df["day_key"] = df["date_from"]
    df["day_label"] = df["date_from"].apply(lambda d: d.strftime("%d.%m.%Y"))

    df["week_start"] = df["date_from"].apply(
        lambda d: d - timedelta(days=d.weekday())
    )
    df["week_key"] = df["week_start"]
    df["week_label"] = df["week_start"].apply(
        lambda ws: f"{ws.strftime('%d.%m')}–"
                   f"{(ws + timedelta(days=6)).strftime('%d.%m')}"
    )

    df["month_key"] = df["date_from"].apply(lambda d: date(d.year, d.month, 1))
    df["month_label"] = df["month_key"].apply(lambda m: m.strftime("%m.%Y"))
    df["year_label"] = df["date_from"].apply(lambda d: str(d.year))

    return df


# ================================================================ агрегаты для листов-пивотов
def _hierarchy_order(df: pd.DataFrame):
    """
    Порядок account -> [cost_item, ...] по убыванию модуля суммы --
    крупнейшие статьи расходов сверху, как и в разделе "Анализ
    расходов WB" самого отчёта.
    """
    if df.empty:
        return []

    by_account = (
        df.groupby("account_label")["amount_rub"].sum().abs()
        .sort_values(ascending=False)
    )

    order = []
    for account in by_account.index:
        sub = df.loc[df["account_label"] == account]
        by_item = (
            sub.groupby("cost_item")["amount_rub"].sum().abs()
            .sort_values(ascending=False)
        )
        order.append((account, list(by_item.index)))

    return order


def _period_columns(df: pd.DataFrame, key_col: str, label_col: str):
    if df.empty:
        return []
    pairs = df[[key_col, label_col]].drop_duplicates().sort_values(key_col)
    return list(pairs[label_col])


def _pivot_amounts(df: pd.DataFrame, label_col: str):
    """{(account_label, cost_item, period_label): сумма}."""
    if df.empty:
        return {}
    g = df.groupby(["account_label", "cost_item", label_col])["amount_rub"].sum()
    return {key: float(v) for key, v in g.items()}


# ================================================================ лист-пивот (год / неделя / день)
def _write_pivot_sheet(wb, sheet_name, title, subtitle, params,
                        hierarchy, period_labels, amounts):
    ws = wb.create_sheet(sheet_name)

    col_end = 2 + len(period_labels)  # A: статья, B: подстатья, далее периоды + Итого
    col_end += 1  # колонка "Итого"

    row = style.write_sheet_header(ws, title, subtitle, params, col_end)
    header_row = row

    headers = ["Раздел", "Статья"] + list(period_labels) + ["Итого, ₽"]
    style.write_table_header(ws, header_row, 1, headers)

    row = header_row + 1
    first_data_row = row
    period_cols = list(range(3, 3 + len(period_labels)))
    total_col = col_end
    numeric_cols = tuple(period_cols) + (total_col,)
    formats = {c: style.FMT_MONEY for c in numeric_cols}

    grand_by_period = {p: 0.0 for p in period_labels}
    grand_total = 0.0

    for account, cost_items in hierarchy:
        # Строка-раздел -- отдельная, зарезервированная ДО строк
        # статей, а не одна из них: если писать итог раздела поверх
        # первой строки статьи (как было раньше), числа этой самой
        # статьи затираются итогом по разделу -- статья остаётся
        # подписанной, но с чужими, более крупными суммами.
        account_row = row
        row += 1

        account_by_period = {p: 0.0 for p in period_labels}
        account_total = 0.0

        for cost_item in cost_items:
            ws.cell(row=row, column=1, value="")
            ws.cell(row=row, column=2, value=cost_item)

            item_total = 0.0
            for offset, period in enumerate(period_labels):
                value = amounts.get((account, cost_item, period), 0.0)
                ws.cell(row=row, column=3 + offset, value=round(value, 2))
                item_total += value
                account_by_period[period] += value
                grand_by_period[period] += value

            ws.cell(row=row, column=total_col, value=round(item_total, 2))
            account_total += item_total
            grand_total += item_total

            style.style_data_row(ws, row, 1, col_end,
                                  numeric_cols=numeric_cols, formats=formats)
            row += 1

        # теперь заполняем зарезервированную строку раздела --
        # ни одна строка статьи её больше не делит
        ws.cell(row=account_row, column=1, value=account)
        for offset, period in enumerate(period_labels):
            ws.cell(row=account_row, column=3 + offset,
                    value=round(account_by_period[period], 2))
            ws.cell(row=account_row, column=3 + offset).number_format = style.FMT_MONEY
        ws.cell(row=account_row, column=total_col, value=round(account_total, 2))
        ws.cell(row=account_row, column=total_col).number_format = style.FMT_MONEY

        style.style_level_row(ws, account_row, 1, col_end, level=0)

    # ИТОГО по всем разделам
    ws.cell(row=row, column=1, value="ИТОГО")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    for offset, period in enumerate(period_labels):
        ws.cell(row=row, column=3 + offset,
                value=round(grand_by_period[period], 2))
        ws.cell(row=row, column=3 + offset).number_format = style.FMT_MONEY
    ws.cell(row=row, column=total_col, value=round(grand_total, 2))
    ws.cell(row=row, column=total_col).number_format = style.FMT_MONEY
    style.style_total_row(ws, row, 1, col_end)
    last_row = row

    style.apply_zebra(ws, first_data_row, last_row - 1, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    style.apply_column_widths(
        ws,
        {"Раздел": 30, "Статья": 34, "Итого, ₽": 15},
        header_row,
        default_max=14,
    )
    style.freeze_table(ws, header_row, first_col=3)
    # Без автофильтра в шапке: это иерархия раздел/статья с
    # промежуточными итогами, а не плоская таблица -- фильтрация
    # по колонкам-периодам здесь только мешает.

    return ws


# ================================================================ лист "По дням" с раскрытием год/месяц/день
def _daily_drilldown_columns(df: pd.DataFrame):
    """
    Хронологический список колонок для листа "По дням": три уровня
    Excel column outline, как в её же PL -- год всегда виден (уровень
    0), месяц свёрнут под своим годом (уровень 1, разворачивается по
    "+"), день свёрнут под своим месяцем (уровень 2, отдельный "+"
    внутри уже развёрнутого месяца). По умолчанию видны только
    итоги года -- месяцы и дни скрыты, пока не раскрыть плюсиком.
    Поэтому отдельный лист "По месяцам" не нужен: месячные суммы
    всегда на расстоянии одного клика, дневные -- двух.

    Каждый элемент: {"label", "amounts" (словарь _pivot_amounts),
    "key" (значение периода в этом словаре), "outline" (0/1/2 --
    уровень вложенности для группировки колонок), "hidden" (свёрнута
    ли по умолчанию), "leaf" (True только у дневных колонок -- лишь
    они складываются в "Итого, ₽" строки, иначе сумма дня по разу
    зайдёт в неё дважды и трижды -- сам день, итог месяца, итог года)}.
    """
    if df.empty:
        return []

    day_amounts = _pivot_amounts(df, "day_label")
    month_amounts = _pivot_amounts(df, "month_label")
    year_amounts = _pivot_amounts(df, "year_label")

    meta = (
        df[["day_key", "day_label", "month_key", "month_label", "year_label"]]
        .drop_duplicates()
        .sort_values("day_key")
    )

    columns = []
    # sort=False у groupby по уже хронологически отсортированному
    # meta сохраняет порядок первого появления группы -- то есть
    # тоже хронологический, без ручного отслеживания смены месяца/года.
    for year_label, year_grp in meta.groupby("year_label", sort=False):
        for _month_key, month_grp in year_grp.groupby("month_key", sort=False):
            month_label = month_grp["month_label"].iloc[0]

            for day_label in month_grp["day_label"]:
                columns.append({
                    "label": day_label, "amounts": day_amounts,
                    "key": day_label, "outline": 2, "hidden": True,
                    "leaf": True,
                })

            columns.append({
                "label": f"Итого {month_label}", "amounts": month_amounts,
                "key": month_label, "outline": 1, "hidden": True,
                "leaf": False,
            })

        columns.append({
            "label": f"Итого {year_label}", "amounts": year_amounts,
            "key": year_label, "outline": 0, "hidden": False,
            "leaf": False,
        })

    return columns


def _write_daily_drilldown_sheet(wb, sheet_name, title, subtitle, params,
                                  hierarchy, df):
    ws = wb.create_sheet(sheet_name)
    columns = _daily_drilldown_columns(df)

    col_end = 2 + len(columns) + 1  # Раздел / Статья + периоды + Итого
    row = style.write_sheet_header(ws, title, subtitle, params, col_end)
    header_row = row

    headers = ["Раздел", "Статья"] + [c["label"] for c in columns] + ["Итого, ₽"]
    style.write_table_header(ws, header_row, 1, headers)

    row = header_row + 1
    first_data_row = row
    period_cols = list(range(3, 3 + len(columns)))
    total_col = col_end
    numeric_cols = tuple(period_cols) + (total_col,)
    formats = {c: style.FMT_MONEY for c in numeric_cols}

    grand_by_col = [0.0] * len(columns)
    grand_total = 0.0

    for account, cost_items in hierarchy:
        account_row = row
        row += 1

        account_by_col = [0.0] * len(columns)
        account_total = 0.0

        for cost_item in cost_items:
            ws.cell(row=row, column=1, value="")
            ws.cell(row=row, column=2, value=cost_item)

            item_total = 0.0
            for idx, col in enumerate(columns):
                value = col["amounts"].get((account, cost_item, col["key"]), 0.0)
                ws.cell(row=row, column=3 + idx, value=round(value, 2))
                account_by_col[idx] += value
                grand_by_col[idx] += value
                if col["leaf"]:
                    # В "Итого, ₽" суммируем только дни (leaf=True):
                    # колонки "Итого месяца"/"Итого года" в том же
                    # списке columns -- это уже производные от тех же
                    # дней суммы, а не отдельные периоды. Если считать
                    # их тоже, каждая сумма попадает в общий итог
                    # трижды: как день, как часть итога месяца и как
                    # часть итога года.
                    item_total += value

            ws.cell(row=row, column=total_col, value=round(item_total, 2))
            account_total += item_total
            grand_total += item_total

            style.style_data_row(ws, row, 1, col_end,
                                  numeric_cols=numeric_cols, formats=formats)
            row += 1

        ws.cell(row=account_row, column=1, value=account)
        for idx, col in enumerate(columns):
            ws.cell(row=account_row, column=3 + idx,
                    value=round(account_by_col[idx], 2))
            ws.cell(row=account_row, column=3 + idx).number_format = style.FMT_MONEY
        ws.cell(row=account_row, column=total_col, value=round(account_total, 2))
        ws.cell(row=account_row, column=total_col).number_format = style.FMT_MONEY

        style.style_level_row(ws, account_row, 1, col_end, level=0)

    ws.cell(row=row, column=1, value="ИТОГО")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
    for idx, col in enumerate(columns):
        ws.cell(row=row, column=3 + idx, value=round(grand_by_col[idx], 2))
        ws.cell(row=row, column=3 + idx).number_format = style.FMT_MONEY
    ws.cell(row=row, column=total_col, value=round(grand_total, 2))
    ws.cell(row=row, column=total_col).number_format = style.FMT_MONEY
    style.style_total_row(ws, row, 1, col_end)
    last_row = row

    style.apply_zebra(ws, first_data_row, last_row - 1, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    style.apply_column_widths(
        ws,
        {"Раздел": 30, "Статья": 34, "Итого, ₽": 15},
        header_row,
        default_max=11,
    )
    style.freeze_table(ws, header_row, first_col=3)

    # Раскрытие в три уровня, как в PL: год -- всегда виден (уровень 0),
    # месяц свёрнут под своим годом (уровень 1, по умолчанию скрыт),
    # день свёрнут под своим месяцем (уровень 2, по умолчанию скрыт).
    # "+" у итога года разворачивает месяцы, отдельный "+" внутри уже
    # развёрнутого месяца -- дни.
    ws.sheet_properties.outlinePr.summaryRight = True
    for idx, col in enumerate(columns):
        if not col["outline"]:
            continue
        col_letter = get_column_letter(3 + idx)
        ws.column_dimensions[col_letter].outlineLevel = col["outline"]
        ws.column_dimensions[col_letter].hidden = col["hidden"]

    return ws



# ================================================================ лист "Детализация" (rrd_id / nm_id)
DETAIL_HEADERS = [
    "Год", "Месяц", "Дата", "rrd_id", "nm_id", "Наименование карточки", "Бренд",
    "Раздел", "Статья", "Комментарий WB (sop_name)", "Под-операция (btn)",
    "Операция", "Ставка НДС, %", "Сумма без НДС, ₽",
]


def _write_detail_sheet(wb, df, title, subtitle, params):
    """
    Год -> месяц -> день -> сама операция (rrd_id/nm_id) -- в одну
    таблицу, отсортированную хронологически: год и месяц отдельными
    колонками, чтобы группировать/фильтровать в Excel, не разбирая
    дату из текста.
    """
    ws = wb.create_sheet("Детализация")

    col_end = len(DETAIL_HEADERS)
    row = style.write_sheet_header(ws, title, subtitle, params, col_end,
                                    landscape=True)
    header_row = row
    style.write_table_header(ws, header_row, 1, DETAIL_HEADERS)

    row = header_row + 1
    first_data_row = row
    numeric_cols = (13, 14)
    formats = {13: style.FMT_PCT, 14: style.FMT_MONEY_DEC}

    df_sorted = df.sort_values(["date_from", "rrd_id"]) if not df.empty else df

    for _, r in df_sorted.iterrows():
        ws.cell(row=row, column=1, value=r["date_from"].year)
        ws.cell(row=row, column=2, value=r["date_from"].month)
        ws.cell(row=row, column=3, value=r["date_from"])
        ws.cell(row=row, column=3).number_format = style.FMT_DATE
        ws.cell(row=row, column=4, value=str(r["rrd_id"]))
        ws.cell(row=row, column=5, value=int(r["nm_id"]) if pd.notna(r["nm_id"]) else None)
        ws.cell(row=row, column=6, value=r["title"])
        ws.cell(row=row, column=7, value=r["brand"])
        ws.cell(row=row, column=8, value=r["account_label"])
        ws.cell(row=row, column=9, value=r["cost_item"])
        ws.cell(row=row, column=10, value=r["sop_name"])
        ws.cell(row=row, column=11, value=r["btn"])
        ws.cell(row=row, column=12,
                value="Дебет" if r["oper"] == "dt" else "Кредит (возврат)")
        ws.cell(row=row, column=13,
                value=float(r["vat_rate"]) if pd.notna(r["vat_rate"]) else 20.0)
        ws.cell(row=row, column=14, value=round(float(r["amount_rub"]), 2))

        style.style_data_row(ws, row, 1, col_end,
                              numeric_cols=numeric_cols, formats=formats)
        row += 1

    last_row = max(row - 1, first_data_row)
    if df_sorted.empty:
        ws.cell(row=row, column=1, value="Нет операций за выбранный период")
        ws.merge_cells(start_row=row, start_column=1, end_row=row,
                        end_column=col_end)
        last_row = row

    style.apply_zebra(ws, first_data_row, last_row, 1, col_end)
    style.apply_column_dividers(ws, header_row, last_row, 1, col_end)
    style.apply_column_widths(
        ws,
        {
            "Год": 8, "Месяц": 8, "Дата": 12, "rrd_id": 14, "nm_id": 12,
            "Наименование карточки": 42, "Бренд": 16,
            "Раздел": 30, "Статья": 26,
            "Комментарий WB (sop_name)": 40, "Под-операция (btn)": 40,
            "Операция": 16, "Ставка НДС, %": 12, "Сумма без НДС, ₽": 16,
        },
        header_row,
    )
    style.freeze_table(ws, header_row, first_col=6)
    if not df_sorted.empty:
        style.enable_autofilter(ws, header_row, 1, col_end, last_row)

    return ws


# ================================================================ Оглавление
def _write_toc(wb, df, period_label, sheet_entries):
    ws = wb.create_sheet(style.TOC_SHEET_NAME)

    col_end = 6
    style.sheet_base_setup(ws, landscape=True)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_end)
    c = ws.cell(row=1, column=1,
                value="Анализ расходов WB по неделям и статьям")
    c.font = style.FONT_SHEET_TITLE
    c.alignment = style.ALIGN_LEFT
    ws.row_dimensions[1].height = 28

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_end)
    c = ws.cell(row=2, column=1, value=period_label)
    c.font = style.FONT_SHEET_SUBTITLE
    c.alignment = style.ALIGN_LEFT

    total = float(df["amount_rub"].sum()) if not df.empty else 0.0
    ops = int(df["rrd_id"].nunique()) if not df.empty else 0
    skus = int(df["nm_id"].nunique()) if not df.empty else 0
    days = int(df["day_key"].nunique()) if not df.empty else 0
    top_account = ""
    if not df.empty:
        by_account = df.groupby("account_label")["amount_rub"].sum().abs()
        if not by_account.empty:
            top_account = by_account.sort_values(ascending=False).index[0]

    def money(v):
        v = round(v)
        sign = "-" if v < 0 else ""
        return f"{sign}{abs(v):,.0f}".replace(",", " ") + " ₽"

    cards = [
        ("Расходы WB за период", money(total), "без НДС, все статьи"),
        ("Операций", f"{ops:,}".replace(",", " "), "уникальных rrd_id"),
        ("Артикулов", f"{skus:,}".replace(",", " "), "уникальных nm_id"),
        ("Дней в периоде", str(days), "с операциями"),
    ]
    row = 4
    style.write_kpi_cards(ws, row, cards, col_start=1, card_width=1, gap_after=0)
    row += 4

    if top_account:
        note_row = row
        ws.merge_cells(start_row=note_row, start_column=1,
                        end_row=note_row, end_column=col_end)
        ws.cell(
            row=note_row, column=1,
            value=f"Крупнейшая статья расходов за период: {top_account}",
        ).font = style.FONT_SHEET_SUBTITLE
        row += 2

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_end)
    ws.cell(row=row, column=1, value="Разделы отчёта").font = style.FONT_TABLE_HEADER
    row += 1

    row = style.write_toc_links(ws, row, sheet_entries, col_label=1,
                                 col_desc=2, desc_span=col_end - 1)
    row += 1

    style.write_footer_note(
        ws, row, col_end,
        f"Категоризация статей -- как в management/commands/sql/wb_costs.sql. "
        f"Сформировано {datetime.now():%d.%m.%Y %H:%M}.",
    )

    style.apply_column_widths(ws, {}, header_row=row, default_max=30)
    for letter in ("A", "B", "C", "D", "E", "F"):
        if ws.column_dimensions[letter].width is None or ws.column_dimensions[letter].width < 14:
            ws.column_dimensions[letter].width = 18

    return ws


# ================================================================ сборка книги
def build_wb_expenses_excel(start_date: str, end_date: str) -> bytes:
    df = fetch_wb_expenses_detail(start_date, end_date)
    return _assemble_workbook(df, start_date, end_date)


def _assemble_workbook(df: pd.DataFrame, start_date: str, end_date: str) -> bytes:
    start_label = pd.to_datetime(start_date).strftime("%d.%m.%Y")
    end_label = pd.to_datetime(end_date).strftime("%d.%m.%Y")
    period_label = (
        f"{start_label} – {end_label}" if start_date != end_date
        else start_label
    )
    params = f"Период: {period_label} · без НДС · сформировано {datetime.now():%d.%m.%Y %H:%M}"

    wb = Workbook()
    wb.remove(wb.active)

    # Раздел/статья -- уже строки каждого из трёх листов ниже,
    # отдельного листа "По статьям" не заводим: сырые sop_name/btn
    # смотрим в "Детализации", а свод раздел/статья -- прямо здесь.
    hierarchy = _hierarchy_order(df)

    # --- По дням ---
    day_labels = _period_columns(df, "day_key", "day_label")
    day_amounts = _pivot_amounts(df, "day_label")
    _write_pivot_sheet(
        wb, "По дням",
        "Расходы WB по дням",
        "Раздел и статья по строкам, дни по столбцам",
        params,
        hierarchy, day_labels, day_amounts,
    )

    # --- По неделям ---
    week_labels = _period_columns(df, "week_key", "week_label")
    week_amounts = _pivot_amounts(df, "week_label")
    _write_pivot_sheet(
        wb, "По неделям",
        "Расходы WB по неделям",
        "Понедельник -- начало недели, как и в остальном отчёте",
        params,
        hierarchy, week_labels, week_amounts,
    )

    # --- По месяцам ---
    month_labels = _period_columns(df, "month_key", "month_label")
    month_amounts = _pivot_amounts(df, "month_label")
    _write_pivot_sheet(
        wb, "По месяцам",
        "Расходы WB по месяцам",
        "Раздел и статья по строкам, месяцы по столбцам",
        params,
        hierarchy, month_labels, month_amounts,
    )

    # Лист "Детализация" (год/месяц/день/rrd_id/nm_id построчно)
    # временно убран -- на всей истории (период не выбран) это
    # тысячи строк, а openpyxl пишет их по одной ячейке за раз,
    # это и есть основная причина долгой сборки. Функция
    # _write_detail_sheet() осталась в файле нетронутой: можно
    # вернуть лист, когда решим, как ограничить его размер
    # (например, только за выбранный период, без выпадения в
    # "всю историю") или ускорить запись через ws.append().

    # --- Оглавление (последним, чтобы иметь итоги для KPI-карточек) ---
    sheet_entries = [
        ("По дням", "Ежедневные суммы по разделам и статьям"),
        ("По неделям", "Понедельные суммы по разделам и статьям"),
        ("По месяцам", "Помесячные суммы по разделам и статьям"),
    ]
    _write_toc(wb, df, params, sheet_entries)

    style.finalize_workbook(
        wb,
        order=[style.TOC_SHEET_NAME, "По дням", "По неделям", "По месяцам"],
    )

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()


# ================================================================ UI: пункт меню "Экспорт"
def export_menu_item(label, description, component_id):
    return dmc.MenuItem(
        dmc.Box(
            children=[
                dmc.Text(label, size="sm", fw=600),
                dmc.Text(description, size="xs", c="dimmed"),
            ]
        ),
        id=component_id,
        n_clicks=0,
    )


def export_menu_dropdown_items():
    """
    Пункты меню "Экспорт" -- вызывается из ui.py при сборке
    dmc.Menu рядом с иконкой "Скачать в Excel". Отдельная функция,
    чтобы дальше сюда просто добавлялись новые пункты (Дарья:
    "потом ещё будем добавлять что скачивать").
    """
    return [
        dmc.MenuLabel("Отчёты"),
        export_menu_item(
            "Анализ расходов WB, Excel",
            "День / неделя / месяц по разделам и статьям ",
            WB_EXPENSES_EXPORT_ITEM_ID,
        ),
    ]


# ================================================================ callback
def register_wb_expenses_excel_callbacks(app, filters):
    """
    Период -- обычный date-picker дашборда (filters.date_picker_id,
    тот же, что и у "Контроль качества"), а не выбор строк в
    таблице: своя дата не нужна, дашборд уже даёт период целиком.

    Разбор date_range -- тот же, что в main.py::render_tab:
        None / []               -- период не выбран;
        [start, None]           -- выбрана только первая дата
                                    (пользователь ещё в календаре);
        [start, end]            -- период выбран.
    Период не выбран -- значит весь период (с начала истории по
    сегодня), а не "сегодня" -- иначе выгрузка почти всегда пустая:
    расходы WB попадают в sales.sales_long с задержкой в несколько
    дней, и "сегодня" почти никогда не бывает закрытым днём.

    Паттерн callback'а -- тот же, что и в меню "Скачать" у
    pricing_strategy: один callback на все пункты меню "Экспорт",
    счётчик нажатий в Store вместо ctx.triggered_id (под
    django-plotly-dash он не работает) и вместо дублирующихся
    Output на общий dcc.Download (ненадёжно).
    """

    @app.callback(
        Output(WB_EXPENSES_EXPORT_DOWNLOAD_ID, "data"),
        Output(WB_EXPENSES_EXPORT_STATUS_ID, "children"),
        Output(WB_EXPENSES_EXPORT_CLICKS_ID, "data"),

        Input(WB_EXPENSES_EXPORT_ITEM_ID, "n_clicks"),

        State(filters.date_picker_id, "value"),
        State(WB_EXPENSES_EXPORT_CLICKS_ID, "data"),

        prevent_initial_call=True,
    )
    def export_wb_expenses(wb_expenses_clicks, date_range, seen_clicks):
        counts = {"wb_expenses": int(wb_expenses_clicks or 0)}
        seen = seen_clicks or {}

        changed = [
            kind for kind, _ in EXPORT_MENU_KINDS
            if counts.get(kind, 0) != int(seen.get(kind) or 0)
        ]
        if not changed:
            return no_update, no_update, counts

        if date_range and len(date_range) == 2:
            picked_start, picked_end = date_range

            if picked_start and picked_end:
                start_date, end_date = picked_start, picked_end
            elif picked_start or picked_end:
                # выбрана только одна из двух дат -- пользователь
                # ещё в календаре, ждём вторую, ничего не собираем
                return no_update, no_update, counts
            else:
                start_date = HISTORY_START.isoformat()
                end_date = date.today().isoformat()
        else:
            # период не выбран -- весь период, а не "сегодня"
            start_date = HISTORY_START.isoformat()
            end_date = date.today().isoformat()

        period_note = (
            f"{start_date} – {end_date}" if start_date != end_date
            else start_date
        )

        try:
            df = fetch_wb_expenses_detail(start_date, end_date)
            content = _assemble_workbook(df, start_date, end_date)
        except Exception as exc:
            return (
                no_update,
                dmc.Alert(
                    title="Не удалось собрать файл",
                    color="red",
                    withCloseButton=True,
                    children=dmc.Text(
                        f"{type(exc).__name__}: {exc} "
                        f"(период запроса: {period_note})",
                        size="sm",
                    ),
                ),
                counts,
            )

        filename = f"wb_expenses_{start_date}_{end_date}.xlsx"

        # Файл собирается даже с пустыми данными (иначе не с чем
        # сравнивать период), но об этом нужно сказать явно --
        # иначе выглядит как молча сломанная выгрузка, а не как
        # "за эти даты в sales.sales_long правда нет операций".
        if df.empty:
            status = dmc.Alert(
                title="Файл собран, но за этот период нет операций",
                color="yellow",
                withCloseButton=True,
                children=dmc.Text(
                    f"Период запроса: {period_note}. Если чипом был "
                    f"выбран конкретный день, а не «За весь период» -- "
                    f"попробуйте период: расходы WB часто попадают в "
                    f"выгрузку WB с задержкой в несколько дней.",
                    size="sm",
                ),
            )
        else:
            status = dmc.Alert(
                title="Файл готов",
                color="teal",
                withCloseButton=True,
                children=dmc.Text(
                    f"{filename} · {len(content) / 1_000_000:.1f} МБ · "
                    f"{len(df)} операций за {period_note}",
                    size="sm",
                ),
            )

        return (
            dcc.send_bytes(content, filename=filename),
            status,
            counts,
        )
