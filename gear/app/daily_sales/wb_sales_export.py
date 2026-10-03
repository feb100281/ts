# gear/app/daily_sales/wb_sales_export.py
"""Выгрузка продаж WB «как в личном кабинете» за любой период.

Источник — sales.sales_long (детализация отчёта реализации WB, дата операции
rr_dt): одна строка field='retail_price' = одна единица товара, oper='dt' —
продажа, 'cr' — возврат. Справочник товара — inventories.wb_product.
Excel оформлен в стиле мэн пака (xlsxwriter, потоковая запись), CSV — для
больших объёмов (; разделитель, запятая в дробях, UTF-8 с BOM).
"""
from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timedelta

import dash_mantine_components as dmc
import pandas as pd
from dash import Input, Output, State, dcc, html, no_update
from dash_iconify import DashIconify

from conns import get_duckdb_conn_with_opt

OPEN_ID = "wb-sales-export-open"
MODAL_ID = "wb-sales-export-modal"
PERIOD_ID = "wb-sales-export-period"
LEVEL_ID = "wb-sales-export-level"
BRANDS_ID = "wb-sales-export-brands"
FORMAT_ID = "wb-sales-export-format"
RUN_ID = "wb-sales-export-run"
DOWNLOAD_ID = "wb-sales-export-download"
STATUS_ID = "wb-sales-export-status"

EXCEL_MAX_ROWS = 1_000_000

# Подсветка ключевых колонок в Excel: светло-зелёная (фирменная) и светло-красная
HL_GREEN = "E7F1ED"
HL_RED = "F6E9E4"
HIGHLIGHT = {
    "Бренд": HL_GREEN,
    "Итого, шт": HL_GREEN,
    "Розничная цена: итого, ₽": HL_GREEN,
    "Возвраты, шт": HL_RED,
}
CSV_ZIP_FROM_MB = 25

# ---------------------------------------------------------------- уровни
DIMS = {
    "date": ("s.d", "Дата"),
    "brand": ("COALESCE(NULLIF(TRIM(UPPER(p.brand)), ''), 'НЕ УКАЗАН')", "Бренд"),
    "category": ("COALESCE(NULLIF(TRIM(p.subject_name), ''), 'Не указана')", "Категория"),
    "gender": ("COALESCE(NULLIF(TRIM(p.gender), ''), 'Не указан')", "Пол"),
    "sa": ("COALESCE(p.sa_name, '')", "Артикул продавца"),
    "nm": ("s.nm_id", "Артикул WB"),
    "title": ("COALESCE(NULLIF(TRIM(p.title), ''), 'Без наименования')", "Наименование"),
    "size": ("COALESCE(s.ts_name, '')", "Размер"),
    "barcode": ("COALESCE(s.barcode, '')", "Баркод"),
}
NM = ["brand", "category", "gender", "sa", "nm", "title"]
LEVELS = {
    "detail": ("Номенклатура × размер × день", ["date"] + NM + ["size", "barcode"]),
    "nm_day": ("Номенклатура × день", ["date"] + NM),
    "nm": ("Номенклатура за период", NM),
    "size": ("Номенклатура × размер за период", NM + ["size", "barcode"]),
    "brand_day": ("Бренд × день", ["date", "brand"]),
    "brand": ("Бренд за период", ["brand"]),
    "category": ("Категория за период", ["category"]),
    "day": ("По дням", ["date"]),
}
GRAIN_SIZE = {"detail", "size"}

METRICS = [
    ("sales_qty", "Продажи, шт"),
    ("ret_qty", "Возвраты, шт"),
    ("net_qty", "Итого, шт"),
    ("rp_sales", "Розничная цена: продажи, ₽"),
    ("rp_ret", "Розничная цена: возвраты, ₽"),
    ("rp_net", "Розничная цена: итого, ₽"),
    ("ra_sales", "До СПП: продажи, ₽"),
    ("ra_ret", "До СПП: возвраты, ₽"),
    ("ra_net", "До СПП: итого, ₽"),
    ("corr", "Коррекции и прочее WB (розничная), ₽"),
    ("avg_ra", "Средняя цена до СПП, ₽"),
    ("disc_pct", "Скидка к розничной, %"),
    ("pay_net", "К перечислению, ₽"),
    ("ret_pct", "Доля возвратов, %"),
]

NOTES = [
    ("Источник", "Детализация еженедельного отчёта реализации WB (как в ЛК → "
                 "Финансовые отчёты). Дата — дата операции в отчёте."),
    ("Продажи / возвраты, шт", "Строки отчёта с типом документа «Продажа» / «Возврат», "
                               "без коррекций WB (одна строка = одна единица)."),
    ("Коррекции и прочее", "Коррекции продаж/возвратов и прочие строки отчёта с "
                           "розничной ценой: не продажа и не возврат, показаны отдельно."),
    ("Розничная цена", "Поле отчёта WB «Цена розничная» (retail_price) — "
                       "наша цена до скидки."),
    ("До СПП", "Поле «Вайлдберриз реализовал Товар (Пр)» (retail_amount) — "
               "цена с нашей скидкой, до СПП."),
    ("Скидка к розничной, %", "1 − До СПП / Розничная цена, по чистым суммам."),
    ("К перечислению", "Поле «К перечислению продавцу за реализованный "
                       "товар» (ppvz_for_pay), продажи минус возвраты."),
    ("Отличие от P&L", "Это продажи «как на сайте WB» с НДС. В мэн паке "
                       "выручка — без НДС, с управленческими корректировками."),
]


# Продажа / возврат — как в ЛК WB: по типу документа, без коррекций WB.
# Коррекции и прочие строки отчёта — отдельной суммой, чтобы итог сходился.
NOT_CORR = "COALESCE(sop_name, '') NOT ILIKE '%оррекц%'"
SALE_COND = f"oper = 'dt' AND dtn = 'Продажа' AND {NOT_CORR}"
RET_COND = f"oper = 'cr' AND dtn = 'Возврат' AND {NOT_CORR}"


def _sql(level, brands):
    dims = LEVELS[level][1]
    grain = "d, nm_id, ts_name, barcode" if level in GRAIN_SIZE else "d, nm_id"
    sel = ",\n".join(f"{DIMS[k][0]} AS \"{DIMS[k][1]}\"" for k in dims)
    grp = ", ".join(str(i + 1) for i in range(len(dims)))
    brand_filter = ""
    if brands:
        ph = ", ".join("?" * len(brands))
        brand_filter = f"AND UPPER(TRIM(p.brand)) IN ({ph})"
    sql = """
        WITH s AS (
            SELECT
                date_from::DATE AS d, nm_id,
                {size_cols}
                COUNT(*) FILTER (WHERE field = 'retail_price' AND {SALE}) AS sales_qty,
                COUNT(*) FILTER (WHERE field = 'retail_price' AND {RET}) AS ret_qty,
                COALESCE(SUM(val) FILTER (WHERE field = 'retail_price' AND {SALE}), 0) / 100.0 AS rp_sales,
                COALESCE(SUM(val) FILTER (WHERE field = 'retail_price' AND {RET}), 0) / 100.0 AS rp_ret,
                COALESCE(SUM(val) FILTER (WHERE field = 'retail_amount' AND {SALE}), 0) / 100.0 AS ra_sales,
                COALESCE(SUM(val) FILTER (WHERE field = 'retail_amount' AND {RET}), 0) / 100.0 AS ra_ret,
                COALESCE(SUM(CASE WHEN oper = 'dt' THEN val ELSE -val END)
                         FILTER (WHERE field = 'retail_price' AND NOT ({SALE}) AND NOT ({RET})), 0) / 100.0 AS corr,
                COALESCE(SUM(CASE WHEN oper = 'dt' THEN val ELSE -val END)
                         FILTER (WHERE field = 'ppvz_for_pay'), 0) / 100.0 AS pay_net
            FROM sales.sales_long
            WHERE date_from::DATE BETWEEN ? AND ?
              AND field IN ('retail_price', 'retail_amount', 'ppvz_for_pay')
            GROUP BY {grain}
        )
        SELECT
            {sel},
            SUM(sales_qty) AS sales_qty,
            SUM(ret_qty) AS ret_qty,
            SUM(sales_qty) - SUM(ret_qty) AS net_qty,
            SUM(rp_sales) AS rp_sales,
            SUM(rp_ret) AS rp_ret,
            SUM(rp_sales) - SUM(rp_ret) AS rp_net,
            SUM(ra_sales) AS ra_sales,
            SUM(ra_ret) AS ra_ret,
            SUM(ra_sales) - SUM(ra_ret) AS ra_net,
            SUM(corr) AS corr,
            CASE WHEN SUM(sales_qty) - SUM(ret_qty) > 0
                 THEN (SUM(ra_sales) - SUM(ra_ret)) / (SUM(sales_qty) - SUM(ret_qty)) END AS avg_ra,
            CASE WHEN SUM(rp_sales) - SUM(rp_ret) > 0
                 THEN (1 - (SUM(ra_sales) - SUM(ra_ret)) / (SUM(rp_sales) - SUM(rp_ret))) * 100 END AS disc_pct,
            SUM(pay_net) AS pay_net,
            CASE WHEN SUM(sales_qty) > 0
                 THEN SUM(ret_qty) * 100.0 / SUM(sales_qty) END AS ret_pct
        FROM s
        LEFT JOIN inventories.wb_product p ON p.card_id = s.nm_id
        WHERE ((s.sales_qty + s.ret_qty) > 0 OR s.corr <> 0) {brand_filter}
        GROUP BY {grp}
        ORDER BY {grp}
    """
    return (sql.replace("{SALE}", SALE_COND).replace("{RET}", RET_COND)
               .replace("{sel}", sel).replace("{grp}", grp)
               .replace("{grain}", grain).replace("{brand_filter}", brand_filter)
               .replace("{size_cols}", "ts_name, barcode," if level in GRAIN_SIZE else ""))


def fetch(start, end, level, brands):
    params = [start, end] + list(brands or [])
    with get_duckdb_conn_with_opt(with_pg=False) as con:
        df = con.execute(_sql(level, brands), params).df()
    return df.rename(columns=dict(METRICS))


def last_sales_date():
    try:
        with get_duckdb_conn_with_opt(with_pg=False) as con:
            r = con.execute("SELECT MAX(date_from)::DATE FROM sales.sales_long "
                            "WHERE field = 'retail_price'").fetchone()
        return r[0] if r and r[0] else date.today() - timedelta(days=1)
    except Exception:
        return date.today() - timedelta(days=1)


def brand_options():
    try:
        with get_duckdb_conn_with_opt(with_pg=False) as con:
            rows = con.execute("""
                SELECT DISTINCT UPPER(TRIM(brand)) FROM inventories.wb_product
                WHERE brand IS NOT NULL AND TRIM(brand) <> '' ORDER BY 1
            """).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------- файлы
def to_csv(df, name):
    buf = io.StringIO()
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%d.%m.%Y")
    out.to_csv(buf, sep=";", decimal=",", index=False, float_format="%.2f")
    data = buf.getvalue().encode("utf-8-sig")
    if len(data) > CSV_ZIP_FROM_MB * 1024 * 1024:
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(name + ".csv", data)
        return zbuf.getvalue(), name + ".zip"
    return data, name + ".csv"


def to_excel(df, name, start, end, level, brands):
    from gear.management.commands import mp
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"constant_memory": True,
                                   "default_date_format": "dd.mm.yyyy",
                                   "nan_inf_to_errors": True})
    F = mp.FONT
    base = {"font_name": F, "font_size": 9, "font_color": "#" + mp.TEXT, "valign": "vcenter"}
    fmt = {
        "title": wb.add_format({**base, "font_size": 14, "bold": True}),
        "sub": wb.add_format({**base, "font_color": "#" + mp.TEXT_2}),
        "muted": wb.add_format({**base, "font_color": "#" + mp.MUTED}),
        "line": wb.add_format({"bottom": 1, "bottom_color": "#" + mp.NAVY}),
        "hdr": wb.add_format({**base, "bold": True, "font_color": "#FFFFFF",
                              "bg_color": "#" + mp.NAVY, "text_wrap": True,
                              "align": "center", "border": 1, "border_color": "#" + mp.NAVY_2}),
        "text": wb.add_format({**base, "bottom": 1, "bottom_color": "#" + mp.LINE, "indent": 1}),
        "date": wb.add_format({**base, "num_format": "dd.mm.yyyy", "align": "center",
                               "bottom": 1, "bottom_color": "#" + mp.LINE}),
        "id": wb.add_format({**base, "num_format": "0", "align": "left",
                             "bottom": 1, "bottom_color": "#" + mp.LINE}),
        "qty": wb.add_format({**base, "num_format": (mp.FMT_QTY),
                              "bottom": 1, "bottom_color": "#" + mp.LINE}),
        "money": wb.add_format({**base, "num_format": (mp.FMT_MONEY),
                                "bottom": 1, "bottom_color": "#" + mp.LINE}),
        "price": wb.add_format({**base, "num_format": (mp.FMT_PRICE),
                                "bottom": 1, "bottom_color": "#" + mp.LINE}),
        "pct": wb.add_format({**base, "num_format": (mp.FMT_PCT),
                              "bottom": 1, "bottom_color": "#" + mp.LINE}),
        "tot_lbl": wb.add_format({**base, "bold": True, "top": 1, "bottom": 1, "indent": 1}),
        "tot_qty": wb.add_format({**base, "bold": True, "top": 1, "bottom": 1,
                                  "num_format": (mp.FMT_QTY)}),
        "tot_money": wb.add_format({**base, "bold": True, "top": 1, "bottom": 1,
                                    "num_format": (mp.FMT_MONEY)}),
        "tot_blank": wb.add_format({**base, "top": 1, "bottom": 1}),
        "lbl": wb.add_format({**base, "bold": True, "font_color": "#" + mp.NAVY_3,
                              "bottom": 1, "bottom_color": "#" + mp.LINE, "valign": "top"}),
        "wrap": wb.add_format({**base, "text_wrap": True, "valign": "top",
                               "bottom": 1, "bottom_color": "#" + mp.LINE}),
    }

    line = {"bottom": 1, "bottom_color": "#" + mp.LINE}
    data_props = {
        "text": {**base, **line, "indent": 1},
        "date": {**base, **line, "num_format": "dd.mm.yyyy", "align": "center"},
        "id": {**base, **line, "num_format": "0", "align": "left"},
        "qty": {**base, **line, "num_format": mp.FMT_QTY},
        "money": {**base, **line, "num_format": mp.FMT_MONEY},
        "price": {**base, **line, "num_format": mp.FMT_PRICE},
        "pct": {**base, **line, "num_format": mp.FMT_PCT},
    }
    tot_props = {
        "lbl": {**base, "bold": True, "top": 1, "bottom": 1, "indent": 1},
        "qty": {**base, "bold": True, "top": 1, "bottom": 1, "num_format": mp.FMT_QTY},
        "money": {**base, "bold": True, "top": 1, "bottom": 1, "num_format": mp.FMT_MONEY},
        "blank": {**base, "top": 1, "bottom": 1},
    }
    _cache = {}

    def cf(group, k, bg=None):
        key = (group, k, bg)
        if key not in _cache:
            props = dict((data_props if group == "data" else tot_props)[k])
            if bg:
                props["bg_color"] = "#" + bg
            _cache[key] = wb.add_format(props)
        return _cache[key]

    def kind(col):
        if col == "Дата":
            return "date"
        if col in ("Артикул WB",):
            return "id"
        if col.endswith(", шт"):
            return "qty"
        if col.endswith(", %"):
            return "pct"
        if col.startswith("Средняя"):
            return "price"
        if col.endswith(", ₽"):
            return "money"
        return "text"

    def sheet(title, data, subtitle):
        ws = wb.add_worksheet(title)
        ws.hide_gridlines(2)
        ws.set_column(0, 0, 2)
        cols = list(data.columns)
        kinds = [kind(c) for c in cols]
        last_col = len(cols)
        ws.write(1, 1, f"Продажи WB · {LEVELS[level][0]}" if title == "Продажи" else title,
                 fmt["title"])
        ws.write(2, 1, subtitle, fmt["sub"])
        ws.write(3, 1, f"Сформировано {datetime.now():%d.%m.%Y %H:%M} · строк: "
                       f"{len(data):,}".replace(",", " ")
                       + (" · бренды: " + ", ".join(brands) if brands else ""), fmt["muted"])
        for c in range(1, last_col + 1):
            ws.write_blank(4, c, None, fmt["line"])
        ws.set_row(1, 24)
        ws.set_row(4, 6)

        hdr = 6
        ws.set_row(hdr, 30)
        for i, c in enumerate(cols):
            ws.write(hdr, 1 + i, c.upper(), fmt["hdr"])
            sample = data[c].head(300)
            if kinds[i] == "text":
                w = max([len(c)] + [len(str(v)) for v in sample]) + 3
                w = min(max(w, 10), 60)
            elif kinds[i] == "date":
                w = 12
            elif kinds[i] == "id":
                w = 13
            else:
                w = max(12, min(18, len(c) * 0.7 + 4))
            ws.set_column(1 + i, 1 + i, w)

        r = hdr + 1
        values = data.itertuples(index=False, name=None)
        cell_fmt = [cf("data", k, HIGHLIGHT.get(c)) for c, k in zip(cols, kinds)]
        for row in values:
            for i, v in enumerate(row):
                k, f = kinds[i], cell_fmt[i]
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    ws.write_blank(r, 1 + i, None, f)
                elif k == "date":
                    ws.write_datetime(r, 1 + i, pd.Timestamp(v).to_pydatetime(), f)
                elif k == "text":
                    ws.write_string(r, 1 + i, str(v), f)
                else:
                    ws.write_number(r, 1 + i, float(v), f)
            r += 1

        # итог — под таблицей, SUBTOTAL пересчитывается при фильтре
        first, last = hdr + 1, hdr + len(data)
        for i, k in enumerate(kinds):
            col = xlsxwriter.utility.xl_col_to_name(1 + i)
            bg = HIGHLIGHT.get(cols[i])
            if i == 0:
                ws.write(r, 1, "ИТОГО", cf("tot", "lbl", bg))
            elif k in ("qty", "money") and len(data):
                ws.write_formula(r, 1 + i, f"=SUBTOTAL(9,{col}{first + 1}:{col}{last + 1})",
                                 cf("tot", k, bg), float(data[cols[i]].fillna(0).sum()))
            else:
                ws.write_blank(r, 1 + i, None, cf("tot", "blank", bg))

        ws.freeze_panes(hdr + 1, 2)
        if len(data):
            ws.autofilter(hdr, 1, last, last_col)
        return ws

    period = f"{start:%d.%m.%Y} – {end:%d.%m.%Y}"
    sheet("Продажи", df, f"Период {period} · как в личном кабинете WB, суммы с НДС")

    ws = wb.add_worksheet("Описание")
    ws.hide_gridlines(2)
    ws.set_column(0, 0, 2)
    ws.set_column(1, 1, 26)
    ws.set_column(2, 2, 95)
    ws.write(1, 1, "Описание выгрузки", fmt["title"])
    ws.write(2, 1, f"Период {period} · {LEVELS[level][0]}", fmt["sub"])
    for c in (1, 2):
        ws.write_blank(4, c, None, fmt["line"])
    for i, (a, b) in enumerate(NOTES):
        ws.write(6 + i, 1, a, fmt["lbl"])
        ws.write(6 + i, 2, b, fmt["wrap"])
        ws.set_row(6 + i, 28)

    wb.close()
    return buf.getvalue(), name + ".xlsx"


# ---------------------------------------------------------------- UI
def wb_sales_menu_item():
    return dmc.MenuItem(
        dmc.Box([
            dmc.Text("Продажи WB (как в ЛК)", size="sm", fw=600),
            dmc.Text("За любой период: бренды, артикулы, размеры", size="xs", c="dimmed"),
        ]),
        id=OPEN_ID, n_clicks=0,
        leftSection=DashIconify(icon="solar:cart-large-2-linear", width=18),
    )


def wb_sales_modal():
    end = last_sales_date()
    start = end.replace(day=1)
    return dmc.Modal(
        id=MODAL_ID, opened=False, centered=True, size="lg", zIndex=10010,
        title=dmc.Group(gap=8, children=[
            DashIconify(icon="solar:cart-large-2-linear", width=22, color="#2F6656"),
            dmc.Text("Выгрузка продаж WB", fw=700, size="lg"),
        ]),
        children=dmc.Stack(gap="md", children=[
            dmc.Text("Продажи и возвраты как в личном кабинете WB: розничная цена, "
                     "цена до СПП, штуки, к перечислению. Суммы с НДС.",
                     size="sm", c="dimmed"),
            dmc.DatePickerInput(
                id=PERIOD_ID, type="range", label="Период",
                value=[start.isoformat(), end.isoformat()],
                valueFormat="DD.MM.YYYY", maxDate=end.isoformat(),
                leftSection=DashIconify(icon="solar:calendar-linear", width=16),
                popoverProps={"zIndex": 10020},
            ),
            dmc.Select(
                id=LEVEL_ID, label="Детализация", value="nm",
                data=[{"value": k, "label": v[0]} for k, v in LEVELS.items()],
                allowDeselect=False, comboboxProps={"zIndex": 10020},
            ),
            dmc.MultiSelect(
                id=BRANDS_ID, label="Бренды", placeholder="Все бренды",
                data=brand_options(), searchable=True, clearable=True,
                comboboxProps={"zIndex": 10020},
            ),
            dmc.Group(justify="space-between", align="flex-end", children=[
                dmc.SegmentedControl(
                    id=FORMAT_ID, value="xlsx", color="teal",
                    data=[{"value": "xlsx", "label": "Excel"},
                          {"value": "csv", "label": "CSV"}],
                ),
                dmc.Button("Скачать", id=RUN_ID, color="teal",
                           leftSection=DashIconify(icon="solar:download-minimalistic-bold",
                                                   width=18)),
            ]),
            dcc.Loading(type="dot", color="#2F6656",
                        children=html.Div(id=STATUS_ID, style={"minHeight": 20})),
            dmc.Text("Совет: детализация «× размер × день» за месяц — это сотни тысяч "
                     "строк. Для таких объёмов удобнее CSV; Excel ограничен 1 млн строк.",
                     size="xs", c="dimmed"),
        ]),
    )


def wb_sales_download():
    return dcc.Download(id=DOWNLOAD_ID)


def register_wb_sales_export_callbacks(app):

    @app.callback(
        Output(MODAL_ID, "opened"),
        Input(OPEN_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def _open(n):
        return True if n else no_update

    @app.callback(
        Output(DOWNLOAD_ID, "data"),
        Output(STATUS_ID, "children"),
        Input(RUN_ID, "n_clicks"),
        State(PERIOD_ID, "value"),
        State(LEVEL_ID, "value"),
        State(BRANDS_ID, "value"),
        State(FORMAT_ID, "value"),
        prevent_initial_call=True,
    )
    def _run(n, period, level, brands, fmt_):
        if not n:
            return no_update, no_update
        if not period or len(period) < 2 or not period[0] or not period[1]:
            return no_update, dmc.Text("Выберите период: дату начала и конца.",
                                       c="red", size="sm")
        start = date.fromisoformat(str(period[0])[:10])
        end = date.fromisoformat(str(period[1])[:10])
        level = level if level in LEVELS else "nm"
        try:
            df = fetch(start, end, level, brands or [])
        except Exception as e:
            return no_update, dmc.Text(f"Ошибка запроса: {e}", c="red", size="sm")
        if df.empty:
            return no_update, dmc.Text("За этот период продаж нет.", c="orange", size="sm")

        name = f"wb_sales_{level}_{start:%Y%m%d}-{end:%Y%m%d}"
        if fmt_ == "xlsx" and len(df) > EXCEL_MAX_ROWS:
            return no_update, dmc.Text(
                f"Строк {len(df):,} — больше лимита Excel. Выберите CSV "
                "или детализацию покрупнее.".replace(",", " "), c="orange", size="sm")
        if fmt_ == "csv":
            data, fname = to_csv(df, name)
        else:
            data, fname = to_excel(df, name, start, end, level, brands or [])
        msg = dmc.Text(f"Готово: {fname} · строк: {len(df):,}".replace(",", " "),
                       c="teal", size="sm")
        return dcc.send_bytes(data, filename=fname), msg
