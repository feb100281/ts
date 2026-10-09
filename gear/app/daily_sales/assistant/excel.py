# gear/app/daily_sales/assistant/excel.py
"""Выгрузка ответа помощника в Excel в стиле мэн пака."""
from __future__ import annotations

import re
import tempfile
import threading
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font
from openpyxl.utils import get_column_letter

from conns import get_duckdb_conn_with_opt

EXPORT_MAX_ROWS = 100_000
EXPORT_TIMEOUT_SEC = 90
FILES_DIR = Path(tempfile.gettempdir()) / "ts_assistant"
FILE_TTL = 24 * 60 * 60
_FID = re.compile(r"^[0-9a-f]{32}$")


def file_path(fid: str) -> Path | None:
    if not _FID.match(fid or ""):
        return None
    hits = list(FILES_DIR.glob(fid + "__*.xlsx"))
    return hits[0] if hits else None


def _cleanup():
    if not FILES_DIR.exists():
        return
    now = time.time()
    for p in FILES_DIR.glob("*.xlsx"):
        if now - p.stat().st_mtime > FILE_TTL:
            p.unlink(missing_ok=True)


def _safe_name(title: str) -> str:
    s = re.sub(r"[^\w\s\-.,()«»]", "", title or "", flags=re.U).strip()
    return (re.sub(r"\s+", "_", s) or "export")[:80]


# ------------------------------------------------------------ форматы
_PCT = re.compile(r"(%|pct|percent|доля|процент|кмд|рентаб|маржинальн)", re.I)
_QTY = re.compile(r"(qty|шт|кол-?во|количеств|count|cnt|штук|заказ)", re.I)
_PRICE = re.compile(r"(price|цена|средн|avg)", re.I)
_ID = re.compile(r"(^id$|_id$|артикул|nm_?id|barcode|штрихкод|gtin|code|код|инн|sku)", re.I)


def _is_num(v):
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def _col_format(name, values, mp):
    sample = [v for v in values[:500] if v is not None]
    if not sample:
        return None, "left"
    if all(isinstance(v, (date, datetime)) for v in sample):
        return "DD.MM.YYYY", "center"
    if not all(_is_num(v) for v in sample):
        return None, "left"
    if _ID.search(name):
        return "0", "left"
    if _PCT.search(name):
        return mp.FMT_PCT, "right"
    if _QTY.search(name):
        return mp.FMT_QTY, "right"
    if _PRICE.search(name):
        return mp.FMT_PRICE, "right"
    return mp.FMT_MONEY, "right"


def _cell_value(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (list, dict, tuple)):
        return str(v)
    return v


# ------------------------------------------------------------ листы
def _write_table(ws, mp, title, subtitle, extra, columns, rows,
                 row_formats=None, totals=True):
    """Таблица: шапка листа, тёмно-зелёная строка заголовков, зебра, итог."""
    first_col = mp.COL_CODE
    ncols = first_col + len(columns) - 1
    mp.sheet_setup(ws)
    mp.title_band(ws, title, subtitle, max(ncols, first_col + 3),
                  extra=extra, show_back=False)
    ws.column_dimensions["A"].width = 2

    hdr = 7
    f_hdr = Font(name=mp.FONT, size=9, bold=True, color="FFFFFF")
    f_cell = Font(name=mp.FONT, size=9, color=mp.TEXT)
    f_bold = Font(name=mp.FONT, size=9, bold=True, color=mp.TEXT)

    cols_vals = [[r[i] for r in rows] for i in range(len(columns))]
    fmts = [_col_format(str(c), cols_vals[i], mp) for i, c in enumerate(columns)]

    for i, name in enumerate(columns):
        mp.write(ws, hdr, first_col + i, str(name).upper(), font=f_hdr,
                 fillc=mp.NAVY, align="left" if fmts[i][1] == "left" else "center",
                 wrap=True)
    ws.row_dimensions[hdr].height = 28

    r = hdr
    for ri, row in enumerate(rows):
        r = hdr + 1 + ri
        rf = (row_formats or {}).get(ri)
        for i, v in enumerate(row):
            fmt, al = fmts[i]
            if rf and i > 0 and _is_num(v):
                fmt = rf
            c = ws.cell(row=r, column=first_col + i, value=_cell_value(v))
            c.font = f_cell
            c.border = mp.B_BOTTOM
            if fmt:
                c.number_format = fmt
            c.alignment = Alignment(horizontal=al, vertical="center",
                                    indent=1 if al == "left" else 0)
    last = r

    if rows:
        mp.apply_zebra(ws, hdr + 1, last, first_col, ncols)
        mp.apply_column_dividers(ws, hdr, last, first_col, ncols)

    sum_cols = [i for i, (fmt, _) in enumerate(fmts)
                if fmt in (mp.FMT_MONEY, mp.FMT_QTY)]
    if totals and rows and len(rows) > 1 and sum_cols and not row_formats:
        tr = last + 1
        lbl_col = 0 if 0 not in sum_cols else None
        if lbl_col is not None:
            mp.write(ws, tr, first_col, "ИТОГО", font=f_bold,
                     border=mp.B_TOTAL, align="left", indent=1)
        for i in range(len(columns)):
            c = ws.cell(row=tr, column=first_col + i)
            c.border = mp.B_TOTAL
            if i in sum_cols:
                L = get_column_letter(first_col + i)
                c.value = f"=SUBTOTAL(9,{L}{hdr + 1}:{L}{last})"
                c.number_format = fmts[i][0]
                c.font = f_bold
                c.alignment = Alignment(horizontal="right", vertical="center")
        ws.row_dimensions[tr].height = 18

    for i, name in enumerate(columns):
        sample = [len(str(name))] + [
            len(f"{v:,.0f}") if _is_num(v) else len(str(v or ""))
            for v in cols_vals[i][:300]]
        ws.column_dimensions[get_column_letter(first_col + i)].width = \
            max(10, min(50, max(sample) + 3))

    if rows:
        ws.freeze_panes = ws.cell(row=hdr + 1, column=first_col + 1)
        ws.auto_filter.ref = (f"{get_column_letter(first_col)}{hdr}:"
                              f"{get_column_letter(ncols)}{last}")


def _write_about(ws, mp, title, question, description, source, sql, nrows):
    mp.sheet_setup(ws, landscape=False)
    mp.title_band(ws, "Описание выгрузки", title, 4, show_back=False)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 90
    f_lbl = Font(name=mp.FONT, size=9, bold=True, color=mp.NAVY_3)
    f_txt = Font(name=mp.FONT, size=9, color=mp.TEXT)
    items = [
        ("Вопрос", question or "—"),
        ("Что выгружено", description or title),
        ("Источник", source),
        ("Строк", nrows),
        ("Сформировано", datetime.now().strftime("%d.%m.%Y %H:%M")),
        ("Кем", "ИИ-помощник дашборда «Продажи»"),
    ]
    r = 7
    for lbl, val in items:
        mp.write(ws, r, 2, lbl, font=f_lbl, align="left", border=mp.B_BOTTOM)
        c = mp.write(ws, r, 3, val, font=f_txt, align="left", wrap=True,
                     border=mp.B_BOTTOM)
        if lbl == "SQL":
            c.font = Font(name="Menlo", size=8, color=mp.TEXT_2)
            ws.row_dimensions[r].height = min(400, 12 * (str(val).count("\n") + 2))
        r += 1


# ------------------------------------------------------------ источники
def _run_sql(sql):
    from .tools import check_sql
    clean = check_sql(sql)
    with get_duckdb_conn_with_opt(with_pg=False) as con:
        timer = threading.Timer(EXPORT_TIMEOUT_SEC, con.interrupt)
        timer.start()
        try:
            cur = con.execute(clean)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(EXPORT_MAX_ROWS + 1)
        finally:
            timer.cancel()
    cut = len(rows) > EXPORT_MAX_ROWS
    return clean, cols, rows[:EXPORT_MAX_ROWS], cut


def _pl_table(a):
    from .pl import METRICS, get_pl, _pick_months
    data = get_pl()
    months = _pick_months(data["months"], a.get("date_from"), a.get("date_to"))
    rd = data["report_date"]
    cols = ["Показатель"] + [m.strftime("%m.%Y") + (" (неполн.)" if m > rd else "")
                             for m in months]
    rows, row_fmts = [], {}
    pct_keys = {"kmd", "zfp_pct", "zfp_ex_pct"}
    for key, label in METRICS:
        vals = [data["derived"][m].get(key) for m in months]
        if key == "conv" and not any(vals):
            continue
        if key in pct_keys:
            row_fmts[len(rows)] = "pct"
        rows.append([label.replace(", ₽", "").replace(", %", "")] + vals)
    if a.get("detail") == "full":
        rows.append(["ДЕТАЛИЗАЦИЯ СТАТЕЙ"] + [None] * len(months))
        items = sorted({(s, i) for (m, s, i) in data["pl"] if m in months})
        for s, i in items:
            vals = [data["pl"].get((m, s, i)) for m in months]
            if any(vals):
                rows.append([f"{s.strip()} · {i}"] + vals)
    return cols, rows, row_fmts, rd


# ------------------------------------------------------------ точка входа
def _num(v: str):
    """«68 410», «15,4», «−3.5» → число; иначе исходная строка."""
    t = v.replace("\u00a0", "").replace(" ", "").replace("−", "-").replace(",", ".")
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        return float(t) if "." in t else int(t)
    return v


def _report_table(tool: str, tool_args: dict):
    """Текстовый отчёт инструмента → самая большая таблица в нём + примечания."""
    from .tools import call_tool
    if tool in ("export_excel", "run_sql", "list_tables", "describe_table"):
        raise ValueError("Для этого инструмента используй sql")
    text, is_err = call_tool(tool, tool_args)
    if is_err:
        raise ValueError(text)
    blocks, cur, notes = [], [], []
    for ln in str(text).split("\n"):
        if "\t" in ln:
            cur.append(ln.split("\t"))
            continue
        if cur:
            blocks.append(cur)
            cur = []
        if ln.strip():
            notes.append(ln.strip())
    if cur:
        blocks.append(cur)
    if not blocks:
        raise ValueError("В отчёте нет таблицы для выгрузки")
    best = max(blocks, key=len)
    cols = [c.strip() or f"Колонка {i + 1}" for i, c in enumerate(best[0])]
    rows = [[_num(c.strip()) if c.strip() else None for c in r]
            + [None] * (len(cols) - len(r)) for r in best[1:]]
    rows = [r[:len(cols)] for r in rows]
    return cols, rows, notes


def _margin_off() -> bool:
    from .tools import MARGIN_OFF
    return MARGIN_OFF


def _margin_msg() -> str:
    from .tools import MARGIN_HOLD_MSG
    return MARGIN_HOLD_MSG


def export(args: dict, question: str = "") -> tuple[str, dict]:
    from gear.management.commands import mp

    title = (args.get("title") or "Выгрузка").strip()[:120]
    desc = args.get("description") or ""
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup()

    wb = Workbook()
    ws = wb.active
    ws.title = "Данные"
    stamp = datetime.now().strftime("%d.%m.%Y %H:%M")

    if args.get("cards_check") is not None and args.get("cards_check") is not False:
        from datetime import date as _d, timedelta as _td
        from ..cards_compliance import make_cards_check_excel
        from .cards import get_df
        c = args["cards_check"] if isinstance(args["cards_check"], dict) else {}
        rd = (_d.fromisoformat(str(c["report_date"])[:10]) if c.get("report_date")
              else _d.today() - _td(days=1))
        df = get_df(rd)
        data = make_cards_check_excel(df, rd)
        fid = uuid.uuid4().hex
        name = f"{_safe_name(title)}_{datetime.now():%Y%m%d_%H%M}.xlsx"
        FILES_DIR.mkdir(parents=True, exist_ok=True)
        (FILES_DIR / f"{fid}__{name}").write_bytes(data)
        info = {"id": fid, "name": name, "rows": len(df), "cut": False}
        return (f"Файл «{name}» готов (тот же отчёт, что у кнопки проверки карточек). "
                "Кнопка скачивания появится под ответом автоматически.", info)

    if args.get("wb_sales"):
        from datetime import date as _d
        from ..wb_sales_export import fetch, to_excel, LEVELS
        w = args["wb_sales"] if isinstance(args["wb_sales"], dict) else {}
        lvl = w.get("level") if w.get("level") in LEVELS else "nm"
        st = _d.fromisoformat(str(w.get("date_from"))[:10])
        en = _d.fromisoformat(str(w.get("date_to"))[:10])
        brands = [b.upper() for b in w.get("brands") or []]
        df = fetch(st, en, lvl, brands)
        data, _ = to_excel(df, "wb_sales", st, en, lvl, brands)
        fid = uuid.uuid4().hex
        name = f"{_safe_name(title)}_{datetime.now():%Y%m%d_%H%M}.xlsx"
        FILES_DIR.mkdir(parents=True, exist_ok=True)
        (FILES_DIR / f"{fid}__{name}").write_bytes(data)
        info = {"id": fid, "name": name, "rows": len(df), "cut": False}
        return (f"Файл «{name}» готов, строк: {len(df)}. Кнопка скачивания "
                "появится под ответом автоматически.", info)

    if args.get("pl"):
        pl_args = args.get("pl") if isinstance(args.get("pl"), dict) else {}
        cols, rows, row_fmts, rd = _pl_table(pl_args)
        row_fmts = {k: mp.FMT_PCT for k in row_fmts}
        ws.title = "P&L"
        _write_table(ws, mp, title, f"Управленческий P&L по методике мэн пака · "
                     f"данные на {rd:%d.%m.%Y}",
                     "₽; расходы в скобках; ТБУ = постоянные затраты / КМД",
                     cols, rows, row_formats=row_fmts, totals=False)
        sql, cut, source = None, False, "Мэн пак (pl_report)"
    elif args.get("margin") and _margin_off():
        raise ValueError(_margin_msg())
    elif args.get("margin"):
        from .margin import margin_table
        m = args["margin"] if isinstance(args["margin"], dict) else {}
        out, start, end, meta = margin_table(m.get("date_from"), m.get("date_to"),
                                             m.get("group_by", "brand"), m.get("search"),
                                             bool(m.get("only_loss")))
        cols, rows = list(out.columns), out.astype(object).where(out.notna(), None).values.tolist()
        ws.title = "Маржинальность"
        _write_table(ws, mp, title,
                     f"Маржинальность по методике мэн пака · {start:%d.%m.%Y}–{end:%d.%m.%Y}",
                     "Без НДС; расходы в скобках; МД2 < 0 — продажи в убыток; "
                     f"продвижение распределено {meta.get('promo_basis', '')}",
                     cols, rows)
        sql, cut, source = None, False, "Мэн пак: продажи, себестоимость FIFO, расходы WB"
    elif args.get("report"):
        r = args["report"] if isinstance(args["report"], dict) else {}
        if _margin_off() and r.get("tool") == "margin_report":
            raise ValueError(_margin_msg())
        cols, rows, notes = _report_table(r.get("tool", ""), r.get("args") or {})
        _write_table(ws, mp, title, desc or "Выгрузка ИИ-помощника",
                     f"Сформировано {stamp} · строк: {len(rows)}", cols, rows, totals=False)
        desc = (desc + "\n" if desc else "") + "\n".join(notes)
        sql, cut, source = None, False, f"Отчёт помощника: {r.get('tool', '')}"
    elif args.get("sql"):
        sql, cols, rows, cut = _run_sql(args["sql"])
        _write_table(ws, mp, title, desc or "Выгрузка ИИ-помощника",
                     f"Сформировано {stamp} · строк: {len(rows):,}".replace(",", " ")
                     + (" · обрезано до 100 000" if cut else ""),
                     cols, rows)
        source = "Аналитическая база дашборда «Продажи»"
    else:
        raise ValueError("Нужен sql или pl")

    _write_about(wb.create_sheet("Описание"), mp, title, question, desc,
                 source, sql, len(rows))

    fid = uuid.uuid4().hex
    name = f"{_safe_name(title)}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    wb.save(FILES_DIR / f"{fid}__{name}")

    preview = "\t".join(map(str, cols)) + "\n" + "\n".join(
        "\t".join("" if v is None else str(v) for v in r) for r in rows[:10])
    info = {"id": fid, "name": name, "rows": len(rows), "cut": cut}
    text = (f"Файл «{name}» готов, строк: {len(rows)}"
            + (" (обрезано до 100 000)" if cut else "")
            + ". Кнопка скачивания появится под ответом автоматически — "
              "не вставляй ссылку в текст.\nПервые строки:\n" + preview)
    return text, info
