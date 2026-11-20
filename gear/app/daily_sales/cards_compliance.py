# gear/app/daily_sales/cards_compliance.py
# =============================================================================
#  Проверка карточек WB: GTIN, ТН ВЭД, декларации/сертификаты.
#
#  В выгрузку попадают только размеры с остатком на выбранную дату
#  (склады WB + FBS + в пути), как в выгрузке остатков.
#  Уровень строки: артикул WB + размер (все штрихкоды размера — в одной строке).
#
#  Два уровня: «Критично» — WB заблокирует или не примет карточку;
#  «Проверить» — нужна ручная проверка, ошибки может и не быть.
# =============================================================================

from io import BytesIO
from datetime import date

import numpy as np
import pandas as pd
from dash import dcc, Input, Output, State, no_update
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.worksheet.properties import PageSetupProperties

from conns import get_duckdb_conn_with_opt
from .excel_report_style import (
    TOC_SHEET_NAME, FONT, EXPENSE, WARN, WARN_BG, OCCUPIED_BG, FMT_QTY, FMT_DATE,
    FMT_PCT, write_sheet_header, write_table_header, style_data_row,
    apply_zebra, apply_column_widths, freeze_table, enable_autofilter,
    write_toc_links, write_footer_note, finalize_workbook,
)
from .ui import (
    STOCKS_DATE_PICKER_ID,
    CARDS_CHECK_BTN_ID,
    CARDS_CHECK_DOWNLOAD_ID,
    CARDS_CHECK_LOADING_ID,
)

CRIT = "Критично"
CHECK = "Проверить"
OK = "OK"


NA = "Нет данных"

STOCK_SQL = """
wb AS (
    SELECT nm_id, chrt_id,
           SUM(COALESCE(quantity, 0)) AS wb_qty,
           SUM(COALESCE(in_way_to_client, 0)
               + COALESCE(in_way_from_client, 0)) AS transit_qty
    FROM stocks.unpacked_stocks
    WHERE date_from::DATE = $report_date::DATE
    GROUP BY 1, 2
),
fbs AS (
    SELECT nm_id, chrt_id, SUM(COALESCE(quantity, 0)) AS fbs_qty
    FROM stocks.unpacked_fbs_stocks
    WHERE date_from::DATE = $report_date::DATE
      AND nm_id IS NOT NULL
    GROUP BY 1, 2
),
stock_pos AS (
    SELECT
        COALESCE(wb.nm_id, fbs.nm_id)::BIGINT AS nm_id,
        COALESCE(wb.chrt_id, fbs.chrt_id)::BIGINT AS chrt_id,
        COALESCE(wb.wb_qty, 0) AS wb_qty,
        COALESCE(fbs.fbs_qty, 0) AS fbs_qty,
        COALESCE(wb.transit_qty, 0) AS transit_qty,
        COALESCE(wb.wb_qty, 0) + COALESCE(fbs.fbs_qty, 0)
            + COALESCE(wb.transit_qty, 0) AS total_qty
    FROM wb
    FULL OUTER JOIN fbs
        ON wb.nm_id = fbs.nm_id AND wb.chrt_id = fbs.chrt_id
    WHERE COALESCE(wb.wb_qty, 0) + COALESCE(fbs.fbs_qty, 0)
          + COALESCE(wb.transit_qty, 0) > 0
)"""

# контрольная цифра GS1: цифры справа налево (без последней) с весами 3,1,3,1…
GTIN_SQL = """
sku_cd AS (
    SELECT
        *,
        CASE WHEN regexp_matches(COALESCE(barcode, ''), '^[0-9]{8}$|^[0-9]{12,14}$')
             THEN (10 - list_sum(list_transform(
                    range(1, length(barcode)),
                    i -> CAST(substr(barcode, length(barcode) - i, 1) AS INT)
                         * CASE WHEN i % 2 = 1 THEN 3 ELSE 1 END)) % 10) % 10
        END AS cd_expected
    FROM skus
),
sku_check AS (
    SELECT
        *,
        CASE
            WHEN COALESCE(barcode, '') = '' THEN NULL
            WHEN NOT regexp_matches(barcode, '^[0-9]+$') THEN 'есть не только цифры'
            WHEN length(barcode) NOT IN (8, 12, 13, 14)
                THEN length(barcode) || ' знаков (нужно 8, 12, 13 или 14)'
            WHEN cd_expected <> CAST(right(barcode, 1) AS INT)
                THEN 'контрольная цифра ' || right(barcode, 1)
                     || ', по расчёту должна быть ' || cd_expected
            WHEN length(barcode) = 13 AND starts_with(barcode, '2')
                THEN 'внутренний код (начинается на 2), не GTIN'
        END AS bad_reason
    FROM sku_cd
),
sizes AS (
    SELECT
        nm_id, chrt_id,
        any_value(vendor_code) AS vendor_code,
        any_value(brand) AS brand,
        any_value(subject_name) AS subject_name,
        any_value(title) AS title,
        any_value(tech_size) AS tech_size,
        bool_or(kiz_marked) AS kiz_marked,
        string_agg(DISTINCT barcode, ', ') FILTER (WHERE barcode <> '') AS barcodes,
        string_agg(DISTINCT barcode, ', ')
            FILTER (WHERE barcode <> '' AND bad_reason IS NULL) AS valid_gtins,
        string_agg(DISTINCT barcode || ': ' || bad_reason, '; ')
            FILTER (WHERE bad_reason IS NOT NULL) AS bad_barcodes,
        any_value(tnved_raw) AS tnved_raw,
        max(doc_end_date) AS doc_end_date,
        string_agg(DISTINCT decl_number, '; ') AS decl_number
    FROM sku_check
    GROUP BY nm_id, chrt_id
)"""

# номера документов и ОКПД2 из характеристик сырой карточки
RAW_DOCS_SQL = """
raw_ch AS (
    SELECT
        r.nm_id::BIGINT AS nm_id,
        json_extract_string(ch.value, '$.name') AS name,
        TRIM(COALESCE(json_extract_string(ch.value, '$.value[0]'),
                      json_extract_string(ch.value, '$.value'))) AS val
    FROM cards.cards_raw r,
         json_each(json_extract(r.payload, '$.characteristics')) AS ch
),
docs AS (
    SELECT
        nm_id,
        string_agg(DISTINCT val, '; ') FILTER (
            WHERE (name ILIKE '%декларац%' OR name ILIKE '%сертификат%')
              AND name NOT ILIKE '%дата%' AND NULLIF(val, '') IS NOT NULL
        ) AS doc_number,
        string_agg(DISTINCT name, '; ') FILTER (
            WHERE (name ILIKE '%декларац%' OR name ILIKE '%сертификат%')
              AND name NOT ILIKE '%дата%' AND NULLIF(val, '') IS NOT NULL
        ) AS doc_fields,
        string_agg(DISTINCT val, '; ') FILTER (
            WHERE name ILIKE '%ОКПД%' AND NULLIF(val, '') IS NOT NULL
        ) AS okpd2
    FROM raw_ch
    GROUP BY nm_id
)"""

NO_DOCS_SQL = """
docs AS (
    SELECT NULL::BIGINT AS nm_id, NULL::VARCHAR AS doc_number,
           NULL::VARCHAR AS doc_fields, NULL::VARCHAR AS okpd2
    WHERE FALSE
)"""

# поля cards.unpacked_cards, которые использует отчёт
CARD_FIELDS = {
    "vendor_code": "c.vendor_code",
    "brand": "c.brand",
    "subject_name": "c.subject_name",
    "title": "c.title",
    "tech_size": "c.tech_size",
    "kiz_marked": "COALESCE(c.kiz_marked, FALSE)",
    "barcode": "TRIM(c.sku)",
    "tnved_raw": "TRIM(COALESCE(c.tnved, ''))",
    "doc_end_date": "try_strptime(c.cert_end_date, '%d.%m.%Y')::DATE",
    "decl_number": "NULLIF(TRIM(c.declaration_number), '')",
}
CARD_SOURCE_COL = {
    "vendor_code": "vendor_code", "brand": "brand", "subject_name": "subject_name",
    "title": "title", "tech_size": "tech_size", "kiz_marked": "kiz_marked",
    "barcode": "sku", "tnved_raw": "tnved", "doc_end_date": "cert_end_date",
    "decl_number": "declaration_number",
}
CARD_NULL_TYPE = {"kiz_marked": "BOOLEAN", "doc_end_date": "DATE"}


def _build_sql(card_cols, raw_ok):
    """Собирает запрос под колонки, которые реально есть в базе."""
    fields = []
    for alias, expr in CARD_FIELDS.items():
        if CARD_SOURCE_COL[alias] in card_cols:
            fields.append("%s AS %s" % (expr, alias))
        else:
            fields.append("NULL::%s AS %s" % (CARD_NULL_TYPE.get(alias, "VARCHAR"), alias))
    skus = ("skus AS (\n    SELECT DISTINCT\n        c.nm_id::BIGINT AS nm_id,\n"
            "        c.chrt_id::BIGINT AS chrt_id,\n        "
            + ",\n        ".join(fields)
            + "\n    FROM cards.unpacked_cards c\n)")
    docs = RAW_DOCS_SQL if raw_ok else NO_DOCS_SQL
    return ("WITH " + STOCK_SQL.strip() + ",\n" + skus + ",\n" + GTIN_SQL.strip()
            + ",\n" + docs.strip() + """
SELECT
    s.*,
    z.* EXCLUDE (nm_id, chrt_id),
    regexp_replace(COALESCE(z.tnved_raw, ''), '[^0-9]', '', 'g') AS tnved,
    COALESCE(d.doc_number, z.decl_number) AS doc_number,
    COALESCE(d.doc_fields,
             CASE WHEN z.decl_number IS NOT NULL
                  THEN 'Номер декларации соответствия' END) AS doc_fields,
    d.okpd2
FROM stock_pos s
LEFT JOIN sizes z ON z.nm_id = s.nm_id AND z.chrt_id = s.chrt_id
LEFT JOIN docs d ON d.nm_id = s.nm_id
ORDER BY s.nm_id, z.tech_size
""")


def _sources(con):
    """Какие данные доступны: колонки unpacked_cards и сырые карточки."""
    card_cols = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'cards' AND table_name = 'unpacked_cards'"
    ).fetchall()}
    try:
        con.execute("SELECT 1 FROM cards.cards_raw LIMIT 1").fetchall()
        raw_ok = True
    except Exception:
        raw_ok = False
    return card_cols, raw_ok


def _classify(r, report_date, avail):
    """(уровень, текст) по каждой проверке: gtin, tnved, doc, okpd."""
    if pd.isna(r.get("vendor_code")):
        miss = (CRIT, "карточка не найдена в выгрузке карточек")
        return miss, miss, miss, (OK, None)

    kiz = bool(r.get("kiz_marked")) if not pd.isna(r.get("kiz_marked")) else False
    if not avail["gtin"]:
        gtin = (NA, "нет данных о штрихкодах")
    elif r.get("valid_gtins"):
        gtin = (OK, None)
    elif not r.get("barcodes"):
        gtin = ((CRIT, "нет штрихкода, в карточке WB отмечена маркировка") if kiz
                else (CHECK, "нет штрихкода"))
    else:
        gtin = ((CRIT, "нет ни одного действительного GTIN, в карточке WB отмечена маркировка")
                if kiz else
                (CHECK, "нет ни одного действительного GTIN (маркировка в карточке WB "
                        "не отмечена — проверить, подлежит ли товар маркировке)"))

    # оферта WB п. 9.2.3: код должен быть достоверным и совпадать с документом
    t = r.get("tnved") or ""
    if not avail["tnved"]:
        tnved = (NA, "нет данных о ТН ВЭД")
    elif not t:
        tnved = (CRIT, "не заполнен")
    elif len(t) != 10:
        tnved = (CHECK, "%d цифр — сверьте с кодом в декларации/сертификате "
                        "(полный код — 10 цифр)" % len(t))
    else:
        tnved = (OK, None)

    num = r.get("doc_number")
    end = r.get("doc_end_date")
    end = None if end is None or pd.isna(end) else pd.to_datetime(end).date()
    if not avail["doc"]:
        doc = (NA, "нет данных о документах")
    elif end is not None and end < report_date:
        doc = (CRIT, "срок действия истёк %s" % end.strftime("%d.%m.%Y"))
    elif not num:
        doc = (CHECK, "в карточке нет номера декларации/сертификата "
                      "(обязателен, если товар подлежит ТР ТС)")
    elif end is None:
        doc = (CHECK, "не указан срок действия документа")
    else:
        doc = (OK, None)

    if not avail["okpd"]:
        okpd = (NA, None)
    elif r.get("okpd2"):
        okpd = (OK, None)
    else:
        okpd = (CHECK, "не заполнен (нужен, если указан в декларации/сертификате)")
    return gtin, tnved, doc, okpd


CHECKS = ("gtin", "tnved", "doc", "okpd")


def get_cards_check_data(report_date) -> pd.DataFrame:
    """Размеры с остатком на дату и результаты проверок."""
    report_date = pd.to_datetime(report_date).date()
    with get_duckdb_conn_with_opt() as con:
        card_cols, raw_ok = _sources(con)
        df = con.execute(_build_sql(card_cols, raw_ok),
                         {"report_date": report_date}).df()

    avail = {
        "gtin": "sku" in card_cols,
        "tnved": "tnved" in card_cols,
        "doc": raw_ok or "declaration_number" in card_cols or "cert_end_date" in card_cols,
        "okpd": raw_ok and df["okpd2"].notna().any(),
    }
    res = [_classify(r, report_date, avail) for r in df.to_dict("records")]
    for i, key in enumerate(CHECKS):
        df[key + "_level"] = [x[i][0] for x in res]
        df[key + "_issue"] = [x[i][1] for x in res]
    levels = df[[k + "_level" for k in CHECKS]]
    df["status"] = np.where((levels == CRIT).any(axis=1), CRIT,
                            np.where((levels == CHECK).any(axis=1), CHECK, OK))
    df["brand"] = df["brand"].fillna("Без бренда").astype(str).str.upper()
    df["valid_gtins"] = df["valid_gtins"].where(
        df["valid_gtins"].notna() & (df["valid_gtins"] != ""), "нет")
    df.attrs["avail"] = avail
    df.attrs["raw_ok"] = raw_ok
    return df


# ------------------------------------------------------------------ Excel

COLUMNS = [
    ("status", "Статус", None),
    ("nm_id", "Артикул WB", None),
    ("vendor_code", "Артикул продавца", None),
    ("brand", "Бренд", None),
    ("subject_name", "Предмет", None),
    ("title", "Наименование", None),
    ("tech_size", "Размер", None),
    ("total_qty", "Остаток, шт", FMT_QTY),
    ("wb_qty", "Склады WB", FMT_QTY),
    ("fbs_qty", "FBS", FMT_QTY),
    ("transit_qty", "В пути", FMT_QTY),
    ("kiz_marked", "Маркировка (отметка в карточке WB)", None),
    ("gtin_issue", "GTIN: проблема", None),
    ("valid_gtins", "Действительные штрихкоды (GTIN)", None),
    ("bad_barcodes", "Недействительные штрихкоды (справочно)", None),
    ("tnved_raw", "ТН ВЭД", None),
    ("tnved_issue", "ТН ВЭД: проблема", None),
    ("doc_number", "Декларация / сертификат", None),
    ("doc_end_date", "Действует до", FMT_DATE),
    ("doc_issue", "Документ: проблема", None),
    ("doc_fields", "Поле карточки с документом", None),
    ("okpd2", "ОКПД2", None),
    ("okpd_issue", "ОКПД2: проблема", None),
]
LEVEL_OF = {"gtin_issue": "gtin_level", "tnved_issue": "tnved_level",
            "doc_issue": "doc_level", "okpd_issue": "okpd_level", "status": "status"}
WIDTHS = {"Наименование": 40, "Декларация / сертификат": 32,
          "GTIN: проблема": 36, "ТН ВЭД: проблема": 18, "Документ: проблема": 36,
          "Действительные штрихкоды (GTIN)": 26, "Недействительные штрихкоды (справочно)": 40,
          "Статус": 12, "ОКПД2: проблема": 30, "Поле карточки с документом": 28}

SHEET_CRIT = "Критично"
SHEET_CHECK = "Проверить"
SHEET_BRANDS = "По брендам"
SHEET_ALL = "Все с остатком"

FILL = {CRIT: PatternFill("solid", fgColor=OCCUPIED_BG),
        CHECK: PatternFill("solid", fgColor=WARN_BG)}
FONT_LVL = {CRIT: Font(name=FONT, size=10, color=EXPENSE, bold=True),
            CHECK: Font(name=FONT, size=10, color=WARN)}


def _cell_value(value):
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, (bool, np.bool_)):
        return "да" if value else "нет"
    return value


def _fit_width(ws):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


def _write_rows(ws, hdr, columns, records, level_of=None, widths=None,
                freeze=True):
    ncols = len(columns)
    write_table_header(ws, hdr, 1, [c[1] for c in columns])
    numeric = {i + 1 for i, c in enumerate(columns) if c[2]}
    formats = {i + 1: c[2] for i, c in enumerate(columns) if c[2]}
    row = hdr + 1
    for rec in records:
        for j, (key, _l, _f) in enumerate(columns, start=1):
            ws.cell(row=row, column=j, value=_cell_value(rec.get(key)))
        style_data_row(ws, row, 1, ncols, numeric_cols=numeric, formats=formats)
        for j, (key, _l, _f) in enumerate(columns, start=1):
            lvl = rec.get(level_of[key]) if level_of and key in level_of else None
            if lvl in FILL:
                ws.cell(row=row, column=j).fill = FILL[lvl]
                ws.cell(row=row, column=j).font = FONT_LVL[lvl]
        row += 1
    last = max(row - 1, hdr + 1)
    apply_zebra(ws, hdr + 1, last, 1, ncols)
    apply_column_widths(ws, widths or {}, hdr)
    ws.row_dimensions[hdr].height = 36
    for j in range(1, ncols + 1):
        ws.cell(row=hdr, column=j).alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True)
    if freeze:
        freeze_table(ws, hdr, first_col=4)
        enable_autofilter(ws, hdr, 1, ncols, last)
    _fit_width(ws)
    return last


HIDE_IF_NA = {
    "gtin": ("gtin_issue", "valid_gtins", "bad_barcodes"),
    "tnved": ("tnved_raw", "tnved_issue"),
    "doc": ("doc_number", "doc_end_date", "doc_issue", "doc_fields"),
    "okpd": ("okpd2", "okpd_issue"),
}


def _detail_sheet(wb, name, df, title, subtitle, params, avail):
    hidden = {c for k, cols in HIDE_IF_NA.items() if not avail.get(k) for c in cols}
    columns = [c for c in COLUMNS if c[0] not in hidden]
    ws = wb.create_sheet(name)
    hdr = write_sheet_header(ws, title, subtitle, params, len(columns))
    _write_rows(ws, hdr, columns, df.to_dict("records"), LEVEL_OF, WIDTHS)


def _card_flags(df):
    """Статусы на уровне карточки: худший статус среди её размеров."""
    g = df.groupby("nm_id")
    out = pd.DataFrame({
        "brand": g["brand"].first(),
        "qty": g["total_qty"].sum(),
    })
    for key in CHECKS:
        lv = df[key + "_level"]
        out[key + "_crit"] = (lv == CRIT).groupby(df["nm_id"]).any()
        out[key + "_check"] = (lv == CHECK).groupby(df["nm_id"]).any()
    out["crit"] = out[[k + "_crit" for k in CHECKS]].any(axis=1)
    out["check"] = ~out["crit"] & out[[k + "_check" for k in CHECKS]].any(axis=1)
    return out


def _summary_row(label, cards, crit, check, n, total_q):
    cq, kq = cards.loc[crit, "qty"].sum(), cards.loc[check, "qty"].sum()
    return {"check": label,
            "crit_n": int(crit.sum()), "crit_p": _pct(crit.sum(), n),
            "crit_q": cq, "crit_qp": _pct(cq, total_q),
            "check_n": int(check.sum()), "check_p": _pct(check.sum(), n),
            "check_q": kq, "check_qp": _pct(kq, total_q)}


def _pct(part, total):
    return part / total * 100 if total else None


def make_cards_check_excel(df, report_date) -> bytes:
    report_date = pd.to_datetime(report_date).date()
    d = report_date.strftime("%d.%m.%Y")
    cards = _card_flags(df)
    n = len(cards)

    wb = Workbook()
    ws = wb.active
    ws.title = TOC_SHEET_NAME
    ncol = 9
    write_sheet_header(
        ws, "ПРОВЕРКА КАРТОЧЕК WB",
        "Требования оферты WB с 01.10.2026 (п. 9.2.3) · только товары с остатком",
        "Остатки на %s · склады WB + FBS + в пути · карточек с остатком: %d · "
        "остаток %s шт" % (d, n, f"{int(df['total_qty'].sum()):,}".replace(",", " ")),
        ncol, landscape=True)
    ws.unmerge_cells(start_row=1, start_column=1, end_row=1, end_column=2)
    for col in (1, 2):
        cell = ws.cell(row=1, column=col)
        cell.value, cell.hyperlink = None, None
        cell.fill, cell.border = PatternFill(fill_type=None), Border()

    # ---- сводка: карточек и % от карточек с остатком
    summary_cols = [
        ("check", "Проверка", None),
        ("crit_n", "Критично: карточек", FMT_QTY),
        ("crit_p", "Критично: % карточек", FMT_PCT),
        ("crit_q", "Критично: остаток, шт", FMT_QTY),
        ("crit_qp", "Критично: % остатка", FMT_PCT),
        ("check_n", "Проверить: карточек", FMT_QTY),
        ("check_p", "Проверить: % карточек", FMT_PCT),
        ("check_q", "Проверить: остаток, шт", FMT_QTY),
        ("check_qp", "Проверить: % остатка", FMT_PCT),
    ]
    total_q = cards["qty"].sum()
    avail = df.attrs.get("avail", {k: True for k in CHECKS})
    rows, skipped = [], []
    for key, label in (("gtin", "GTIN (штрихкод)"), ("tnved", "ТН ВЭД"),
                       ("doc", "Декларация / сертификат"), ("okpd", "ОКПД2")):
        if not avail.get(key):
            skipped.append(label)
            continue
        c, k = cards[key + "_crit"], cards[key + "_check"] & ~cards[key + "_crit"]
        rows.append(_summary_row(label, cards, c, k, n, total_q))
    rows.append(_summary_row("ИТОГО (карточка учтена один раз)", cards,
                             cards["crit"], cards["check"], n, total_q))
    ws.merge_cells(start_row=6, start_column=1, end_row=6, end_column=ncol)
    c = ws.cell(row=6, column=1, value="ВСЕГО С ОСТАТКОМ: %s карточек · %s шт"
                % (f"{n:,}".replace(",", " "), f"{int(total_q):,}".replace(",", " ")))
    c.font = Font(name=FONT, size=11, bold=True)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[6].height = 24
    last = _write_rows(ws, 7, summary_cols, rows,
                       widths={"Проверка": 32}, freeze=False)
    for j in range(1, len(summary_cols) + 1):
        ws.cell(row=last, column=j).font = Font(name=FONT, size=10, bold=True)

    for col, w in zip("ABCDEFGHI", (40, 13, 13, 14, 13, 13, 13, 14, 13)):
        ws.column_dimensions[col].width = w

    if skipped:
        ws.merge_cells(start_row=last + 1, start_column=1, end_row=last + 1, end_column=ncol)
        c = ws.cell(row=last + 1, column=1,
                    value="Не проверялось — нет данных в карточках: " + ", ".join(skipped))
        c.font = Font(name=FONT, size=9, italic=True, color=WARN)
        last += 1

    row = write_toc_links(ws, last + 2, [
        (SHEET_CRIT, "Размеры, где WB может заблокировать карточку — исправлять в первую очередь"),
        (SHEET_CHECK, "Нужна ручная проверка: ошибки может и не быть"),
        (SHEET_BRANDS, "Сколько проблем по каждому бренду, в штуках и процентах"),
        (SHEET_ALL, "Все размеры с остатком — для сверки"),
    ], col_label=1, col_desc=2, desc_span=8)

    notes = [
        "ЧТО ТРЕБУЕТ WB (оферта с 01.10.2026, п. 9.2.3 пп. 16 и п. 9.2.15): загрузить в карточку "
        "разрешительные документы; указать достоверные коды ТН ВЭД и ОКПД2, совпадающие с кодами "
        "в документах (если код в документе есть или товар подлежит маркировке); своевременно "
        "обновлять документы и иметь регистрацию в гос. системах (Честный знак). При "
        "несоответствии WB блокирует карточку, предупреждая за 3 дня.",
        "GTIN. Штрихкоды карточки — это GTIN. Последняя цифра контрольная: цифры справа налево "
        "(без последней) умножаются поочерёдно на 3 и 1 и суммируются, контрольная = "
        "(10 − сумма mod 10) mod 10. Не совпала — код недействителен. Размер в порядке, если "
        "есть хотя бы один действительный GTIN. Для маркированных товаров код также должен быть "
        "в Национальном каталоге — это отчёт не проверяет.",
        "МАРКИРОВКА — отметка «маркируется» из карточки WB; обязательность по закону отчёт не "
        "проверяет.",
        "КРИТИЧНО: нет действительного GTIN у товара с отметкой маркировки; ТН ВЭД не заполнен; "
        "срок документа истёк; карточка не найдена.",
        "ПРОВЕРИТЬ: ТН ВЭД не из 10 цифр (сверьте с документом); нет действительного GTIN у "
        "товара без отметки маркировки; нет номера документа в карточке или срока действия; "
        "не заполнен ОКПД2. Наличие загруженного файла документа и совпадение кодов с "
        "документом по этим данным не проверить — только вручную.",
    ]
    row += 1
    for text in notes:
        write_footer_note(ws, row, ncol, text)
        ws.cell(row=row, column=1).alignment = Alignment(
            horizontal="left", vertical="top", wrap_text=True)
        ws.row_dimensions[row].height = 44
        row += 1
    _fit_width(ws)

    # ---- по брендам
    b = cards.groupby("brand").agg(
        cards=("qty", "size"), qty=("qty", "sum"),
        crit=("crit", "sum"), check=("check", "sum"),
        gtin=("gtin_crit", "sum"), tnved=("tnved_crit", "sum"), doc=("doc_crit", "sum"),
    ).reset_index()
    b["crit_q"] = cards[cards["crit"]].groupby("brand")["qty"].sum().reindex(b["brand"]).fillna(0).values
    b["crit_p"] = b["crit"] / b["cards"] * 100
    b["check_p"] = b["check"] / b["cards"] * 100
    b = b.sort_values(["crit", "crit_q"], ascending=False)
    brand_cols = [
        ("brand", "Бренд", None), ("cards", "Карточек с остатком", FMT_QTY),
        ("qty", "Остаток, шт", FMT_QTY), ("crit", "Критично, карточек", FMT_QTY),
        ("crit_p", "Критично, %", FMT_PCT), ("crit_q", "Остаток в критичных, шт", FMT_QTY),
        ("gtin", "из них GTIN", FMT_QTY), ("tnved", "ТН ВЭД", FMT_QTY),
        ("doc", "Документы", FMT_QTY), ("check", "Проверить, карточек", FMT_QTY),
        ("check_p", "Проверить, %", FMT_PCT),
    ]
    wsb = wb.create_sheet(SHEET_BRANDS)
    hdr = write_sheet_header(wsb, "ПРОБЛЕМЫ ПО БРЕНДАМ",
                             "Карточки с остатком · статус карточки — худший из её размеров",
                             "Остатки на %s · сортировка: больше критичных выше" % d,
                             len(brand_cols))
    _write_rows(wsb, hdr, brand_cols, b.to_dict("records"), widths={"Бренд": 24})

    params = "Остатки на %s · уровень: артикул WB + размер" % d
    order = {CRIT: 0, CHECK: 1, OK: 2}
    df = df.assign(_o=df["status"].map(order)).sort_values(
        ["_o", "total_qty"], ascending=[True, False])
    _detail_sheet(wb, SHEET_CRIT, df[df["status"] == CRIT], "КРИТИЧНО",
                  "WB может заблокировать карточку · сначала больший остаток", params, avail)
    _detail_sheet(wb, SHEET_CHECK, df[df["status"] == CHECK], "ПРОВЕРИТЬ",
                  "Нужна ручная проверка · критичных проблем нет", params, avail)
    _detail_sheet(wb, SHEET_ALL, df.sort_values(["brand", "nm_id", "tech_size"]),
                  "ВСЕ КАРТОЧКИ С ОСТАТКОМ", "Для сверки", params, avail)

    finalize_workbook(wb, [TOC_SHEET_NAME, SHEET_CRIT, SHEET_CHECK, SHEET_BRANDS, SHEET_ALL])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------- callback

def register_cards_check_callbacks(app):
    @app.callback(
        Output(CARDS_CHECK_DOWNLOAD_ID, "data"),
        Output(CARDS_CHECK_LOADING_ID, "children"),
        Input(CARDS_CHECK_BTN_ID, "n_clicks"),
        State(STOCKS_DATE_PICKER_ID, "value"),
        prevent_initial_call=True,
    )
    def export_cards_check(n_clicks, report_date):
        if not n_clicks:
            return no_update, no_update
        report_date = (pd.to_datetime(report_date).date() if report_date
                       else date.today() - pd.Timedelta(days=1))
        df = get_cards_check_data(report_date)
        content = make_cards_check_excel(df, report_date)
        return (
            dcc.send_bytes(content, filename="cards_check_%s.xlsx"
                           % report_date.strftime("%Y-%m-%d")),
            "",
        )
