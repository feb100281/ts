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


CARDS_CHECK_SQL = r"""
WITH wb AS (
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
),

skus AS (
    SELECT DISTINCT
        c.nm_id::BIGINT AS nm_id,
        c.chrt_id::BIGINT AS chrt_id,
        c.vendor_code, c.brand, c.subject_name, c.title, c.tech_size,
        COALESCE(c.kiz_marked, FALSE) AS kiz_marked,
        TRIM(c.sku) AS barcode,
        TRIM(COALESCE(c.tnved, '')) AS tnved_raw,
        try_strptime(c.cert_end_date, '%d.%m.%Y')::DATE AS doc_end_date
    FROM cards.unpacked_cards c
),

-- контрольная цифра GS1: цифры справа налево (без последней) с весами 3,1,3,1…
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

-- одна строка на размер: остаток размера не дублируется по штрихкодам
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
        max(doc_end_date) AS doc_end_date
    FROM sku_check
    GROUP BY nm_id, chrt_id
),

-- номера документов: все характеристики со словами «декларац» / «сертификат»,
-- кроме дат
docs AS (
    SELECT
        r.nm_id::BIGINT AS nm_id,
        string_agg(DISTINCT TRIM(COALESCE(
            json_extract_string(ch.value, '$.value[0]'),
            json_extract_string(ch.value, '$.value'))), '; ') AS doc_number,
        string_agg(DISTINCT json_extract_string(ch.value, '$.name'), '; ') AS doc_fields
    FROM cards.cards_raw r,
         json_each(json_extract(r.payload, '$.characteristics')) AS ch
    WHERE (json_extract_string(ch.value, '$.name') ILIKE '%декларац%'
           OR json_extract_string(ch.value, '$.name') ILIKE '%сертификат%')
      AND json_extract_string(ch.value, '$.name') NOT ILIKE '%дата%'
      AND NULLIF(TRIM(COALESCE(
            json_extract_string(ch.value, '$.value[0]'),
            json_extract_string(ch.value, '$.value'))), '') IS NOT NULL
    GROUP BY 1
)

SELECT
    s.*,
    z.* EXCLUDE (nm_id, chrt_id),
    regexp_replace(COALESCE(z.tnved_raw, ''), '[^0-9]', '', 'g') AS tnved,
    d.doc_number,
    d.doc_fields
FROM stock_pos s
LEFT JOIN sizes z ON z.nm_id = s.nm_id AND z.chrt_id = s.chrt_id
LEFT JOIN docs d ON d.nm_id = s.nm_id
ORDER BY s.nm_id, z.tech_size
"""


def _classify(r, report_date):
    """Возвращает (gtin, tnved, doc) — каждая пара (уровень, текст) или (OK, None)."""
    if pd.isna(r.get("vendor_code")):
        miss = (CRIT, "карточка не найдена в выгрузке карточек")
        return miss, miss, miss

    kiz = bool(r.get("kiz_marked"))
    if r.get("valid_gtins"):
        gtin = (OK, None)
    elif not r.get("barcodes"):
        gtin = ((CRIT, "нет штрихкода, в карточке WB отмечена маркировка") if kiz
                else (CHECK, "нет штрихкода"))
    else:
        gtin = ((CRIT, "нет ни одного действительного GTIN, в карточке WB отмечена маркировка")
                if kiz else
                (CHECK, "нет ни одного действительного GTIN "
                        "(маркировка в карточке WB не отмечена — проверить, "
                        "подлежит ли товар маркировке)"))

    t = r.get("tnved") or ""
    if not t:
        tnved = (CRIT, "не заполнен")
    elif len(t) != 10:
        tnved = (CRIT, "%d цифр вместо 10" % len(t))
    else:
        tnved = (OK, None)

    num = r.get("doc_number")
    end = r.get("doc_end_date")
    end = None if end is None or pd.isna(end) else pd.to_datetime(end).date()
    if not num:
        doc = (CHECK, "в карточке нет номера декларации/сертификата "
                      "(нужен, если товар подлежит ТР ТС)")
    elif end is not None and end < report_date:
        doc = (CRIT, "срок истёк %s" % end.strftime("%d.%m.%Y"))
    elif end is None:
        doc = (CHECK, "не указан срок действия")
    else:
        doc = (OK, None)
    return gtin, tnved, doc


def get_cards_check_data(report_date) -> pd.DataFrame:
    """Размеры с остатком на дату и результаты проверок."""
    report_date = pd.to_datetime(report_date).date()
    with get_duckdb_conn_with_opt() as con:
        df = con.execute(CARDS_CHECK_SQL, {"report_date": report_date}).df()

    res = [_classify(r, report_date) for r in df.to_dict("records")]
    for i, key in enumerate(("gtin", "tnved", "doc")):
        df[key + "_level"] = [x[i][0] for x in res]
        df[key + "_issue"] = [x[i][1] for x in res]
    levels = df[["gtin_level", "tnved_level", "doc_level"]]
    df["status"] = np.where((levels == CRIT).any(axis=1), CRIT,
                            np.where((levels == CHECK).any(axis=1), CHECK, OK))
    df["brand"] = df["brand"].fillna("Без бренда").astype(str).str.upper()
    df["valid_gtins"] = df["valid_gtins"].where(
        df["valid_gtins"].notna() & (df["valid_gtins"] != ""), "нет")
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
]
LEVEL_OF = {"gtin_issue": "gtin_level", "tnved_issue": "tnved_level",
            "doc_issue": "doc_level", "status": "status"}
WIDTHS = {"Наименование": 40, "Декларация / сертификат": 32,
          "GTIN: проблема": 36, "ТН ВЭД: проблема": 18, "Документ: проблема": 36,
          "Действительные штрихкоды (GTIN)": 26, "Недействительные штрихкоды (справочно)": 40,
          "Статус": 12}

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


def _detail_sheet(wb, name, df, title, subtitle, params):
    ws = wb.create_sheet(name)
    hdr = write_sheet_header(ws, title, subtitle, params, len(COLUMNS))
    _write_rows(ws, hdr, COLUMNS, df.to_dict("records"), LEVEL_OF, WIDTHS)


def _card_flags(df):
    """Статусы на уровне карточки: худший статус среди её размеров."""
    g = df.groupby("nm_id")
    out = pd.DataFrame({
        "brand": g["brand"].first(),
        "qty": g["total_qty"].sum(),
    })
    for key in ("gtin", "tnved", "doc"):
        lv = df[key + "_level"]
        out[key + "_crit"] = (lv == CRIT).groupby(df["nm_id"]).any()
        out[key + "_check"] = (lv == CHECK).groupby(df["nm_id"]).any()
    out["crit"] = out[["gtin_crit", "tnved_crit", "doc_crit"]].any(axis=1)
    out["check"] = ~out["crit"] & out[["gtin_check", "tnved_check", "doc_check"]].any(axis=1)
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
        "GTIN, ТН ВЭД, декларации и сертификаты · только товары с остатком",
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
    rows = []
    for key, label in (("gtin", "GTIN (штрихкод)"), ("tnved", "ТН ВЭД"),
                       ("doc", "Декларация / сертификат")):
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

    row = write_toc_links(ws, last + 2, [
        (SHEET_CRIT, "Размеры, где WB может заблокировать карточку — исправлять в первую очередь"),
        (SHEET_CHECK, "Нужна ручная проверка: ошибки может и не быть"),
        (SHEET_BRANDS, "Сколько проблем по каждому бренду, в штуках и процентах"),
        (SHEET_ALL, "Все размеры с остатком — для сверки"),
    ], col_label=1, col_desc=2, desc_span=8)

    notes = [
        "КАК ПРОВЕРЯЕТСЯ GTIN. Штрихкоды карточки — это и есть GTIN (EAN-13 и т. п.). "
        "Последняя цифра — контрольная, она вычисляется из остальных по стандарту GS1: "
        "цифры справа налево (без последней) умножаются поочерёдно на 3 и 1, суммируются, "
        "контрольная = (10 − сумма mod 10) mod 10. Если она не совпала — код недействителен "
        "(выдуман или с опечаткой). Пример: 4610503150759 — сумма 61, контрольная 9, совпало.",
        "У размера бывает несколько штрихкодов. Размер в порядке, если среди них есть хотя бы "
        "один действительный GTIN; лишние недействительные коды показаны справочно.",
        "МАРКИРОВКА: берётся отметка «маркируется» (kizMarked) из карточки WB — её ставит "
        "продавец или WB по категории. Обязательность маркировки в Честном знаке отчёт сам "
        "не проверяет: если отметки нет, а товар подлежит маркировке, это тоже нужно исправить.",
        "КРИТИЧНО: нет действительного GTIN у товара с отметкой маркировки; ТН ВЭД не из 10 цифр; "
        "срок декларации/сертификата истёк; карточка не найдена.",
        "ПРОВЕРИТЬ: нет действительного GTIN у товара без отметки маркировки; в карточке нет номера документа (не нужен, если товар не подлежит "
        "ТР ТС); не указан срок действия документа.",
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
                  "WB может заблокировать карточку · сначала больший остаток", params)
    _detail_sheet(wb, SHEET_CHECK, df[df["status"] == CHECK], "ПРОВЕРИТЬ",
                  "Нужна ручная проверка · критичных проблем нет", params)
    _detail_sheet(wb, SHEET_ALL, df.sort_values(["brand", "nm_id", "tech_size"]),
                  "ВСЕ КАРТОЧКИ С ОСТАТКОМ", "Для сверки", params)

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
