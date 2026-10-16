# gear/app/daily_sales/assistant/menu.py
"""Меню бота продаж: готовые отчёты по кнопкам, без ИИ.

Кнопки внизу экрана → выбор периода (быстрые кнопки или календарь «начало — конец»)
→ карточка с цифрами, график и Excel. Все цифры — SQL по тем же витринам, что
дашборд продаж и утренняя рассылка; продажи — «как на сайте WB», с НДС.

callback_data: «mn:<операция>:<отчёт>:…», даты — ГГГГММДД.
    mn:o:<r>                 — выбор периода
    mn:p:<r>:<пресет>        — быстрый период
    mn:c:<r>:<ГГГГММ>:<нач>  — листание календаря (нач = 0, пока не выбрано)
    mn:d:<r>:<дата>          — выбрано начало
    mn:e:<r>:<нач>:<кон>     — выбран конец → отчёт
    mn:f:<r>:<файл>:<нач>:<кон> — дополнительный Excel
"""
from __future__ import annotations

import calendar
import html
import re
from datetime import date, timedelta

import pandas as pd

# ---------------------------------------------------------------- кнопки
REPORTS = {
    "s": "📊 Продажи",
    "k": "📦 Остатки",
    "b": "🏷 Бренды",
    "c": "🗂 Категории",
    "w": "💸 Расходы WB",
    "a": "📣 Реклама",
    "t": "🏆 Топ карточек",
}
BTN_AI = "🤖 Спросить ИИ"
BTN_HELP = "ℹ️ Как пользоваться"
BY_TEXT = {v: k for k, v in REPORTS.items()}

PRESETS = (("y", "Вчера"), ("7", "7 дней"), ("w", "Прошлая неделя"),
           ("m", "Этот месяц"), ("pm", "Прошлый месяц"), ("30", "30 дней"))
MONTHS = ("Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август",
          "Сентябрь", "Октябрь", "Ноябрь", "Декабрь")
WEEK = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
DATA_START = date(2024, 1, 29)
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF = "application/pdf"
CHART_MAX_DAYS = 62
TOP_N = 10
MOVERS_N = 6

QTY, RET, RP, RA, PAY = ("Итого, шт", "Возвраты, шт", "До СПП: итого, ₽",
                         "После СПП: итого, ₽", "К перечислению, ₽")
SOLD = "Продажи, шт"


def keyboard() -> dict:
    """Постоянное меню бота продаж."""
    r = REPORTS
    return {"keyboard": [[{"text": r["s"]}, {"text": r["k"]}],
                         [{"text": r["b"]}, {"text": r["c"]}],
                         [{"text": r["w"]}, {"text": r["a"]}],
                         [{"text": r["t"]}, {"text": BTN_AI}],
                         [{"text": BTN_HELP}]],
            "resize_keyboard": True, "is_persistent": True,
            "input_field_placeholder": "Кнопка или вопрос своими словами…"}


# ---------------------------------------------------------------- формат
def esc(t) -> str:
    return html.escape(str(t if t is not None else ""), quote=False)


def num(v, d=0) -> str:
    s = f"{float(v or 0):,.{d}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


def rub(v) -> str:
    v = float(v or 0)
    if abs(v) >= 1e6:
        return num(v / 1e6, 2) + " млн ₽"
    return num(v) + " ₽"


def chg(cur, prev, pp=False) -> str:
    """▲ 8,2% / ▼ 3,1% к прошлому периоду; pp — разница в процентных пунктах."""
    cur, prev = float(cur or 0), float(prev or 0)
    if pp:
        d = cur - prev
        if abs(d) < 0.05:
            return "≈"
        return ("▲ " if d > 0 else "▼ ") + num(abs(d), 1) + " п.п."
    if not prev:
        return ""
    d = (cur - prev) / abs(prev) * 100
    if abs(d) < 0.05:
        return "≈ 0%"
    return ("▲ " if d > 0 else "▼ ") + num(abs(d), 1) + "%"


def span(a: date, b: date) -> str:
    if a == b:
        return f"{a:%d.%m.%Y}"
    if a.year == b.year:
        return f"{a:%d.%m}–{b:%d.%m.%Y}"
    return f"{a:%d.%m.%Y}–{b:%d.%m.%Y}"


def ndays(a: date, b: date) -> int:
    return (b - a).days + 1


def ymd(d: date) -> str:
    return f"{d:%Y%m%d}"


def from_ymd(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


# ---------------------------------------------------------------- периоды
def loaded() -> date:
    from .digest import loaded_date
    return loaded_date() or date.today() - timedelta(days=1)


def month_end(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def preset(code: str, hi: date) -> tuple[date, date]:
    if code == "y":
        return hi, hi
    if code == "7":
        return hi - timedelta(days=6), hi
    if code == "30":
        return hi - timedelta(days=29), hi
    if code == "w":
        b = hi if hi.weekday() == 6 else hi - timedelta(days=hi.weekday() + 1)
        return b - timedelta(days=6), b
    if code == "m":
        return hi.replace(day=1), hi
    pb = hi.replace(day=1) - timedelta(days=1)          # прошлый месяц
    return pb.replace(day=1), pb


def prev_range(a: date, b: date) -> tuple[date, date]:
    """Прошлый период для сравнения: месяц — прошлый месяц (те же числа), иначе — столько же дней раньше."""
    if a.day == 1 and a.month == b.month and a.year == b.year:
        pa = (a - timedelta(days=1)).replace(day=1)
        if b == month_end(b):
            return pa, month_end(pa)
        return pa, min(pa.replace(day=1) + timedelta(days=b.day - 1), month_end(pa))
    n = ndays(a, b)
    return a - timedelta(days=n), a - timedelta(days=1)


def period_kb(rep: str) -> dict:
    rows, row = [], []
    for code, label in PRESETS:
        row.append({"text": label, "callback_data": f"mn:p:{rep}:{code}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "📅 Свой период", "callback_data": f"mn:c:{rep}::0"}])
    return {"inline_keyboard": rows}


def calendar_kb(rep: str, year: int, month: int, start: date | None, lo: date, hi: date) -> dict:
    """Месяц кнопками. Без start — выбираем начало, со start — конец (дни раньше начала серые)."""
    s = ymd(start) if start else "0"
    rows = [[{"text": f"{MONTHS[month - 1]} {year}", "callback_data": "mn:n"}],
            [{"text": w, "callback_data": "mn:n"} for w in WEEK]]
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        line = []
        for day in week:
            if not day:
                line.append({"text": " ", "callback_data": "mn:n"})
                continue
            d = date(year, month, day)
            if d < lo or d > hi or (start and d < start):
                line.append({"text": "·", "callback_data": "mn:n"})
            elif start:
                mark = f"[{day}]" if d == start else str(day)
                line.append({"text": mark, "callback_data": f"mn:e:{rep}:{s}:{ymd(d)}"})
            else:
                line.append({"text": str(day), "callback_data": f"mn:d:{rep}:{ymd(d)}"})
        rows.append(line)
    first = date(year, month, 1)
    prev_m = first - timedelta(days=1)
    next_m = month_end(first) + timedelta(days=1)
    nav = [{"text": "‹", "callback_data": f"mn:c:{rep}:{prev_m:%Y%m}:{s}"} if prev_m >= lo
           else {"text": " ", "callback_data": "mn:n"},
           {"text": "Закрыть", "callback_data": f"mn:o:{rep}"},
           {"text": "›", "callback_data": f"mn:c:{rep}:{next_m:%Y%m}:{s}"} if next_m <= hi
           else {"text": " ", "callback_data": "mn:n"}]
    rows.append(nav)
    if start:
        rows.append([{"text": f"Только {start:%d.%m}", "callback_data": f"mn:e:{rep}:{s}:{s}"}])
    return {"inline_keyboard": rows}


def ask_text(rep: str) -> str:
    return (f"<b>{REPORTS[rep]}</b>\nЗа какой период? Нажмите кнопку или напишите даты: "
            "<code>01.10–15.10</code>, <code>01.09.2026-30.09.2026</code>, <code>05.10</code>")


_D = r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?"
_RANGE = re.compile(rf"^\s*(?:с\s*)?{_D}\s*(?:[-–—]|по|до|\s)\s*{_D}\s*$", re.I)
_ONE = re.compile(rf"^\s*{_D}\s*$")


def _mkdate(d, m, y, hi: date) -> date | None:
    year = hi.year if not y else (int(y) + 2000 if len(y) == 2 else int(y))
    try:
        out = date(year, int(m), int(d))
    except ValueError:
        return None
    if not y and out > hi:                      # «20.12» в январе — прошлый год
        out = out.replace(year=out.year - 1)
    return out


def parse_range(text: str, hi: date) -> tuple[date, date] | None:
    """«01.10–15.10», «1.10 по 15.10.26», «с 01.09.2026 до 30.09.2026», «05.10» → (начало, конец)."""
    t = (text or "").strip()
    m = _RANGE.match(t)
    if m:
        a, b = _mkdate(*m.groups()[:3], hi), _mkdate(*m.groups()[3:], hi)
        if m.group(6) is None and m.group(3) and b and a and b.year != a.year and b < a:
            b = b.replace(year=a.year)          # год указан только у начала
        if a and b:
            a, b = sorted((a, b))
            return max(a, DATA_START), min(b, hi)
        return None
    m = _ONE.match(t)
    if m:
        d = _mkdate(*m.groups(), hi)
        return (d, d) if d and DATA_START <= d <= hi else None
    return None


# ---------------------------------------------------------------- данные
def sales(a: date, b: date, level: str) -> pd.DataFrame:
    from ..wb_sales_export import fetch
    return fetch(a, b, level, [])


def _photo(fn):
    try:
        return fn()
    except Exception as e:                       # без картинки отчёт всё равно уходит
        print(f"[menu] график: {type(e).__name__}: {e}", flush=True)
        return None


def _book(title: str, subtitle: str, sheets: list[tuple[str, list, list]], notes=None) -> bytes:
    """Excel в стиле мэн пака: листы (имя, колонки, строки) + описание."""
    import io
    from openpyxl import Workbook
    from gear.management.commands import mp
    from .excel import _write_table

    wb = Workbook()
    wb.remove(wb.active)
    for name, cols, rows in sheets:
        ws = wb.create_sheet(name[:31])
        _write_table(ws, mp, f"{title} — {name.lower()}", subtitle, None, cols, rows)
    if notes:
        from openpyxl.styles import Font
        ws = wb.create_sheet("Описание")
        mp.sheet_setup(ws, landscape=False)
        mp.title_band(ws, "Описание", subtitle, 4, show_back=False)
        ws.column_dimensions["A"].width = 2
        ws.column_dimensions["B"].width = 24
        ws.column_dimensions["C"].width = 90
        for i, (k, v) in enumerate(notes):
            mp.write(ws, 7 + i, 2, k, font=Font(name=mp.FONT, size=9, bold=True, color=mp.NAVY_3),
                     align="left", border=mp.B_BOTTOM)
            mp.write(ws, 7 + i, 3, v, font=Font(name=mp.FONT, size=9, color=mp.TEXT),
                     align="left", wrap=True, border=mp.B_BOTTOM)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# Результат отчёта: {"text", "photo", "files": [(имя, байты, mime)], "kb"}
def _files_kb(rep, a, b, items) -> dict:
    s, e = ymd(a), ymd(b)
    btn = [{"text": label, "callback_data": f"mn:f:{rep}:{code}:{s}:{e}"} for code, label in items]
    rows = [btn[i:i + 2] for i in range(0, len(btn), 2)]
    rows.append([{"text": "🔁 Другой период", "callback_data": f"mn:o:{rep}"}])
    return {"inline_keyboard": rows}


# ---------------------------------------------------------------- 📊 продажи
SALES_FILES = (("day", "Excel: по дням"), ("brand", "Excel: по брендам"),
               ("category", "Excel: по категориям"), ("nm", "Excel: по артикулам"))
LEVEL_NAMES = {"day": "по дням", "brand": "по брендам", "category": "по категориям",
               "nm": "по артикулам", "brand_day": "бренды по дням"}


def _tot(df, col):
    return float(df[col].sum()) if col in df.columns and not df.empty else 0.0


def report_sales(a: date, b: date) -> dict | None:
    from . import digest_charts as ch
    pa, pb = prev_range(a, b)
    df = sales(pa, b, "day")
    if df.empty:
        return None
    dcol = df.columns[0]
    df[dcol] = pd.to_datetime(df[dcol]).dt.date
    cur, old = df[df[dcol] >= a], df[df[dcol] <= pb]
    if cur.empty:
        return None
    rp, ra, pay, q, r, sold = (_tot(cur, c) for c in (RP, RA, PAY, QTY, RET, SOLD))
    o_rp, o_ra, o_pay, o_q, o_r, o_sold = (_tot(old, c) for c in (RP, RA, PAY, QTY, RET, SOLD))
    ret_pct = r / sold * 100 if sold else 0
    o_ret_pct = o_r / o_sold * 100 if o_sold else 0
    spp = (1 - ra / rp) * 100 if rp else 0
    o_spp = (1 - o_ra / o_rp) * 100 if o_rp else 0
    n = ndays(a, b)
    lines = [f"<b>📊 Продажи · {span(a, b)}</b>",
             f"<i>{n} дн. · сравнение с {span(pa, pb)}</i>", "",
             f"До СПП: <b>{rub(rp)}</b>  {chg(rp, o_rp)}",
             f"После СПП: <b>{rub(ra)}</b>  {chg(ra, o_ra)}",
             f"К перечислению: <b>{rub(pay)}</b>  {chg(pay, o_pay)}",
             f"Продано: <b>{num(q)} шт</b>  {chg(q, o_q)}",
             f"Возвраты: <b>{num(r)} шт</b> · {num(ret_pct, 1)}%  {chg(ret_pct, o_ret_pct, pp=True)}",
             f"Средняя цена до СПП: <b>{rub(rp / q if q else 0)}</b>  "
             f"{chg(rp / q if q else 0, o_rp / o_q if o_q else 0)}",
             f"СПП: <b>{num(spp, 1)}%</b>  {chg(spp, o_spp, pp=True)}"]
    if n > 1:
        best = cur.loc[cur[RP].idxmax()]
        lines += ["", f"Лучший день: <b>{best[dcol]:%d.%m}</b> — {rub(best[RP])}",
                  f"В среднем за день: {rub(rp / n)} и {num(q / n)} шт"]
    lines += ["", "<i>Как на сайте WB: с НДС, по дате операции в отчёте реализации.</i>"]

    photo = None
    if n > 1:
        show = df if ndays(pa, b) <= CHART_MAX_DAYS else cur
        days = list(show[dcol])
        vals = [float(v) / 1e6 for v in show[RP]]
        n_cur = len(cur) if show is df else len(show)
        photo = _photo(lambda: ch.sales_period(
            days, vals, n_cur, None, f"Продажи до СПП — {rub(rp)}",
            f"млн ₽ по дням · {span(a, b)}" + (" · бледные — прошлый период" if show is df else "")))
    return {"text": "\n".join(lines), "photo": photo, "auto": "day",
            "kb": _files_kb("s", a, b, SALES_FILES)}


def file_sales(level: str, a: date, b: date):
    from ..wb_sales_export import to_excel
    if level not in LEVEL_NAMES:
        return None
    df = sales(a, b, level)
    name = f"Продажи WB {LEVEL_NAMES[level]} {span(a, b)}".replace("/", ".")
    data, fname = to_excel(df, name, a, b, level, [])
    return fname, data, XLSX


# ---------------------------------------------------------------- 🏷 бренды / 🗂 категории
GROUP = {"b": ("brand", "Бренд", "брендов", "🏷 Бренды"),
         "c": ("category", "Категория", "категорий", "🗂 Категории")}


def _compare(level, a, b):
    pa, pb = prev_range(a, b)
    key = {"brand": "Бренд", "category": "Категория"}[level]
    cur, old = sales(a, b, level), sales(pa, pb, level)
    cols = [key, QTY, RET, SOLD, RP, RA]
    cur = cur[cols] if not cur.empty else pd.DataFrame(columns=cols)
    old = old[cols] if not old.empty else pd.DataFrame(columns=cols)
    m = cur.merge(old, on=key, how="outer", suffixes=("", "_old")).fillna(0)
    m["d_rp"] = m[RP] - m[RP + "_old"]
    total = m[RP].sum()
    m["share"] = m[RP] / total * 100 if total else 0
    return m.sort_values(RP, ascending=False), pa, pb, key


def report_group(rep: str, a: date, b: date) -> dict | None:
    from . import digest_charts as ch
    level, key, many, title = GROUP[rep]
    m, pa, pb, key = _compare(level, a, b)
    if m.empty or not m[RP].sum():
        return None
    lines = [f"<b>{title} · {span(a, b)}</b>",
             f"<i>сравнение с {span(pa, pb)} · продажи до СПП с НДС</i>", "",
             f"<b>Топ-{min(TOP_N, len(m))} по продажам</b>"]
    for i, r in enumerate(m.head(TOP_N).itertuples(index=False), 1):
        d = dict(zip(m.columns, r))
        lines.append(f"{i}. {esc(d[key])} — <b>{rub(d[RP])}</b> · {num(d['share'], 1)}%  "
                     f"{chg(d[RP], d[RP + '_old'])}")
    up = m[m["d_rp"] > 0].sort_values("d_rp", ascending=False).head(MOVERS_N)
    down = m[m["d_rp"] < 0].sort_values("d_rp").head(MOVERS_N)
    if not up.empty:
        lines += ["", "<b>▲ Растут сильнее всех</b>"] + [
            f"• {esc(x)} — +{rub(v)}" for x, v in zip(up[key], up["d_rp"])]
    if not down.empty:
        lines += ["", "<b>▼ Падают сильнее всех</b>"] + [
            f"• {esc(x)} — −{rub(abs(v))}" for x, v in zip(down[key], down["d_rp"])]
    lines.append(f"\nВсего {many} с продажами: {len(m[m[RP] > 0])}. Полный список — в Excel.")
    movers = [(str(x), float(v)) for x, v in
              list(zip(up[key], up["d_rp"]))[:4] + list(zip(down[key], down["d_rp"]))[:4]]
    photo = _photo(lambda: ch.brands(
        movers, f"{title[2:]}: кто вырос и упал", f"{span(a, b)} к {span(pa, pb)}, до СПП")) \
        if movers else None
    return {"text": "\n".join(lines), "photo": photo, "auto": "cmp",
            "kb": _files_kb(rep, a, b, (("cmp", "Excel: сравнение"),
                                        ("days", "Excel: по дням")))}


def file_group(rep: str, code: str, a: date, b: date):
    level, key, many, title = GROUP[rep]
    if code == "days":
        if level == "brand":
            return file_sales("brand_day", a, b)
        df = sales(a, b, "nm_day")
        if df.empty:
            return None
        df["Дата"] = pd.to_datetime(df["Дата"]).dt.date
        g = df.groupby(["Дата", "Категория"], as_index=False)[[SOLD, RET, QTY, RP, RA]].sum()
        cols = ["Дата", "Категория", SOLD, RET, QTY, RP, RA]
        rows = g[cols].values.tolist()
        data = _book("Категории", f"{span(a, b)} · как на сайте WB, с НДС",
                     [("По дням", cols, rows)])
        return f"Категории по дням {span(a, b)}.xlsx", data, XLSX
    m, pa, pb, key = _compare(level, a, b)
    cols = [key, "Шт", "Шт прошлый", "Изменение шт", "До СПП, ₽", "До СПП прошлый, ₽",
            "Изменение, ₽", "Изменение, %", "Доля, %", "После СПП, ₽", "Возвраты, %"]
    rows = []
    for _, r in m.iterrows():
        rows.append([r[key], r[QTY], r[QTY + "_old"], r[QTY] - r[QTY + "_old"], r[RP],
                     r[RP + "_old"], r["d_rp"],
                     (r["d_rp"] / r[RP + "_old"] * 100) if r[RP + "_old"] else None,
                     r["share"], r[RA], (r[RET] / r[SOLD] * 100) if r[SOLD] else None])
    sub = f"{span(a, b)} к {span(pa, pb)} · как на сайте WB, с НДС"
    data = _book(f"{title[2:]}", sub, [("Сравнение", cols, rows)], notes=[
        ("Период", span(a, b)), ("Сравнение", span(pa, pb)),
        ("До СПП", "Наша цена до скидки постоянного покупателя, с НДС, продажи минус возвраты."),
        ("После СПП", "«Вайлдберриз реализовал Товар (Пр)» — цена покупателя."),
        ("Источник", "Отчёт реализации WB, дата операции.")])
    return f"{title[2:]} {span(a, b)}.xlsx", data, XLSX


# ---------------------------------------------------------------- 📦 остатки
STOCK_SQL = """
WITH wb AS (
    SELECT nm_id, SUM(COALESCE(quantity, 0)) AS wb_qty,
           SUM(COALESCE(in_way_to_client, 0)) + SUM(COALESCE(in_way_from_client, 0)) AS way
    FROM stocks.unpacked_stocks WHERE date_from::DATE = $d::DATE GROUP BY nm_id
),
fbs AS (
    SELECT nm_id, SUM(COALESCE(quantity, 0)) AS fbs_qty
    FROM stocks.unpacked_fbs_stocks WHERE date_from::DATE = $d::DATE GROUP BY nm_id
)
SELECT COALESCE(wb.nm_id, fbs.nm_id) AS nm_id,
       COALESCE(wb.wb_qty, 0) + COALESCE(wb.way, 0) + COALESCE(fbs.fbs_qty, 0) AS qty,
       COALESCE(NULLIF(TRIM(UPPER(p.brand)), ''), 'НЕ УКАЗАН') AS brand,
       COALESCE(NULLIF(TRIM(p.subject_name), ''), 'Не указана') AS category,
       COALESCE(p.sa_name, '') AS sa, COALESCE(NULLIF(TRIM(p.title), ''), '') AS title
FROM wb FULL OUTER JOIN fbs ON wb.nm_id = fbs.nm_id
LEFT JOIN inventories.wb_product p ON p.card_id = COALESCE(wb.nm_id, fbs.nm_id)
"""


def _stock_dates(a, b):
    from conns import get_duckdb_conn_with_opt
    from .stocks import _last_date
    with get_duckdb_conn_with_opt(ro=True) as con:
        db = _last_date(con, b)
        da = _last_date(con, a - timedelta(days=1)) or _last_date(con, a)
    return da, db


def _stock_nm(d):
    from conns import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        return con.execute(STOCK_SQL, {"d": d}).df()


def _stock_table(a, b, by):
    """Остатки на начало и конец по группе + продажи за период и дни запаса."""
    da, db = _stock_dates(a, b)
    s_end = _stock_nm(db)
    s_beg = _stock_nm(da) if da else s_end.iloc[0:0]
    sold = sales(a, b, "nm")
    sold = sold.rename(columns={"Артикул WB": "nm_id"})[["nm_id", QTY]] if not sold.empty \
        else pd.DataFrame(columns=["nm_id", QTY])
    attrs = pd.concat([s_end, s_beg])[["nm_id", "brand", "category", "sa", "title"]] \
        .drop_duplicates("nm_id")
    m = attrs.merge(s_beg[["nm_id", "qty"]].rename(columns={"qty": "beg"}), on="nm_id", how="left") \
        .merge(s_end[["nm_id", "qty"]].rename(columns={"qty": "end"}), on="nm_id", how="left") \
        .merge(sold, on="nm_id", how="left").fillna({"beg": 0, "end": 0, QTY: 0})
    keys = {"brand": ["brand"], "category": ["category"],
            "nm": ["brand", "category", "sa", "nm_id", "title"]}[by]
    g = m.groupby(keys, as_index=False)[["beg", "end", QTY]].sum()
    g = g[(g["beg"] != 0) | (g["end"] != 0) | (g[QTY] != 0)]
    days = ndays(a, b)
    g["chg"] = g["end"] - g["beg"]
    g["cover"] = g.apply(lambda r: r["end"] / (r[QTY] / days) if r[QTY] > 0 else None, axis=1)
    return g.sort_values("end", ascending=False), da, db


def report_stocks(a: date, b: date) -> dict | None:
    from . import digest_charts as ch
    from .stocks import series, totals
    end = totals(b)
    if not end:
        return None
    beg = totals(a - timedelta(days=1)) or totals(a)
    places = (("На складах WB", "wb"), ("Наш склад FBS", "fbs"),
              ("Едет к покупателям", "to_client"), ("Возвращается", "from_client"))
    d = end["total"] - (beg["total"] if beg else 0)
    lines = [f"<b>📦 Остатки на {end['date']:%d.%m.%Y}</b>",
             f"<i>изменение с {beg['date']:%d.%m.%Y}</i>" if beg else "", "",
             f"Всего: <b>{num(end['total'])} шт</b>"
             + (f"  {'▲' if d > 0 else '▼'} {num(abs(d))} шт ({chg(end['total'], beg['total'])[2:]})"
                if beg and d else "")]
    for name, k in places:
        dd = end[k] - beg[k] if beg else 0
        lines.append(f"{name}: <b>{num(end[k])}</b>" + (f"  ({'+' if dd > 0 else '−'}{num(abs(dd))})"
                                                       if dd else ""))
    q = _tot(sales(a, b, "day"), QTY)
    n = ndays(a, b)
    if q > 0:
        lines += ["", f"Продано за период: <b>{num(q)} шт</b> (≈{num(q / n)} в день)",
                  f"Хватит примерно на <b>{num(end['total'] / (q / n))} дн.</b>"]
    try:
        g, _, _ = _stock_table(a, b, "brand")
        up = g[g["chg"] > 0].sort_values("chg", ascending=False).head(5)
        down = g[g["chg"] < 0].sort_values("chg").head(5)
        if not up.empty:
            lines += ["", "<b>▲ Прибавилось больше всего</b>"] + [
                f"• {esc(x)} — +{num(v)} шт" for x, v in zip(up["brand"], up["chg"])]
        if not down.empty:
            lines += ["", "<b>▼ Убыло больше всего</b>"] + [
                f"• {esc(x)} — −{num(abs(v))} шт" for x, v in zip(down["brand"], down["chg"])]
        short = g[(g["cover"].notna()) & (g["cover"] < 14) & (g[QTY] > 0)].sort_values("cover").head(5)
        if not short.empty:
            lines += ["", "<b>⚠️ Кончается (запас меньше 2 недель)</b>"] + [
                f"• {esc(x)} — {num(e)} шт, ≈{num(c)} дн." for x, e, c in
                zip(short["brand"], short["end"], short["cover"])]
    except Exception as e:
        print(f"[menu] остатки по брендам: {type(e).__name__}: {e}", flush=True)
    lines += ["", "<i>Все места вместе: склады WB, в пути и наш склад FBS.</i>"]
    ser = series(b, min(max(n, 8), CHART_MAX_DAYS))
    photo = None
    if len(ser) > 1:
        parts = [(name, end[k], (end[k] - beg[k]) if beg else None) for name, k in places]
        ref = next((i for i, r in enumerate(ser) if beg and r["date"] == beg["date"]), None)
        photo = _photo(lambda: ch.stocks(
            [r["date"] for r in ser], [r["total"] for r in ser], parts,
            f"Остатки на {end['date']:%d.%m} — {num(end['total'])} шт",
            "склады WB, в пути, наш склад FBS", ref=ref or 0, note="за период"))
    return {"text": "\n".join(x for x in lines if x is not None), "photo": photo, "auto": "brand",
            "kb": _files_kb("k", a, b, (("brand", "Excel: по брендам"),
                                        ("category", "Excel: по категориям"),
                                        ("nm", "Excel: по артикулам")))}


def file_stocks(by: str, a: date, b: date):
    g, da, db = _stock_table(a, b, by)
    head = {"brand": ["Бренд"], "category": ["Категория"],
            "nm": ["Бренд", "Категория", "Артикул продавца", "Артикул WB", "Наименование"]}[by]
    src = {"brand": ["brand"], "category": ["category"],
           "nm": ["brand", "category", "sa", "nm_id", "title"]}[by]
    cols = head + [f"На {da:%d.%m}, шт" if da else "На начало, шт", f"На {db:%d.%m}, шт",
                   "Изменение, шт", "Продано за период, шт", "Запас, дней"]
    rows = [[r[c] for c in src] + [r["beg"], r["end"], r["chg"], r[QTY],
                                   round(r["cover"]) if r["cover"] is not None and r["cover"] == r["cover"] else None]
            for _, r in g.iterrows()]
    name = {"brand": "по брендам", "category": "по категориям", "nm": "по артикулам"}[by]
    data = _book("Остатки", f"{span(a, b)} · склады WB + в пути + FBS", [(f"Остатки {name}", cols, rows)],
                 notes=[("Остатки", "Склады WB + в пути к клиенту + в пути от клиента + наш склад FBS."),
                        ("Продано", "Продажи минус возвраты за период, как на сайте WB."),
                        ("Запас, дней", "Остаток на конец / средние продажи в день за период.")])
    return f"Остатки {name} {span(a, b)}.xlsx", data, XLSX


# ---------------------------------------------------------------- 💸 расходы WB
def _costs_chart(rows, title, sub) -> bytes:
    from . import digest_charts as ch
    plt = ch._plt()
    rows = sorted(rows, key=lambda r: -r[1])
    fig, ax = plt.subplots(figsize=(10.8, 1.8 + 0.9 * len(rows)), dpi=100)
    mx = max(v for _, v, _ in rows) or 1
    for i, (name, v, old) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh(y, v, height=0.58, color=ch.GREEN)
        ax.text(-mx * 0.02, y, name, va="center", ha="right", fontsize=15, color=ch.INK)
        lab = rub(v) + (f"   {chg(v, old)}" if old else "")
        ax.text(v + mx * 0.02, y, lab, va="center", ha="left", fontsize=14.5, fontweight="bold",
                color=ch.INK)
    ax.set_xlim(-mx * 0.45, mx * 1.7)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.axis("off")
    h = fig.get_figheight()
    ch._head(fig, title, sub, y=1 - 0.42 / h)
    fig.subplots_adjust(left=0.03, right=0.97, top=1 - 1.3 / h, bottom=0.03)
    return ch._png(plt, fig)


def report_costs(a: date, b: date) -> dict | None:
    from .digest_period import wb_costs_range
    pa, pb = prev_range(a, b)
    rows = [r for r in wb_costs_range(a, b, pa, pb) if r[1] or r[2]]
    if not rows:
        return None
    rp = _tot(sales(a, b, "day"), RP)
    o_rp = _tot(sales(pa, pb, "day"), RP)
    tot, o_tot = sum(r[1] for r in rows), sum(r[2] for r in rows)
    lines = [f"<b>💸 Расходы WB · {span(a, b)}</b>",
             f"<i>сравнение с {span(pa, pb)} · суммы с НДС, как в отчёте WB</i>", "",
             f"Всего: <b>{rub(tot)}</b>  {chg(tot, o_tot)}"]
    if rp:
        lines.append(f"Доля от продаж до СПП: <b>{num(tot / rp * 100, 1)}%</b>  "
                     f"{chg(tot / rp * 100, o_tot / o_rp * 100 if o_rp else 0, pp=True)}")
    lines.append("")
    for name, v, o in sorted(rows, key=lambda r: -r[1]):
        share = f" · {num(v / rp * 100, 1)}% от продаж" if rp else ""
        lines.append(f"{name}: <b>{rub(v)}</b>{share}  {chg(v, o)}")
    worst = max(rows, key=lambda r: r[1] - r[2])
    if worst[1] - worst[2] > 0 and worst[2]:
        lines += ["", f"Сильнее всего выросла статья «{worst[0]}»: +{rub(worst[1] - worst[2])}."]
    lines += ["", "<i>Комиссия WB сюда не входит. Подробно по дням и статьям — в Excel.</i>"]
    photo = _photo(lambda: _costs_chart(rows, f"Расходы WB — {rub(tot)}",
                                        f"{span(a, b)} · изменение к {span(pa, pb)}"))
    return {"text": "\n".join(lines), "photo": photo, "auto": "xl",
            "kb": _files_kb("w", a, b, (("xl", "Excel: расходы WB"),))}


def file_costs(a: date, b: date):
    from ..wb_expenses_excel import build_wb_expenses_excel
    return f"Расходы WB {span(a, b)}.xlsx", build_wb_expenses_excel(a.isoformat(), b.isoformat()), XLSX


# ---------------------------------------------------------------- 📣 реклама
def report_ads(a: date, b: date) -> dict | None:
    from .. import ad_campaigns_report as ad
    pa, pb = prev_range(a, b)
    st = ad._fetch_stats(a.isoformat(), b.isoformat())
    if st is None or st.empty:
        return None
    old = ad._fetch_stats(pa.isoformat(), pb.isoformat())
    t, o = ad._totals(st), ad._totals(old)
    lines = [f"<b>📣 Реклама WB · {span(a, b)}</b>",
             f"<i>сравнение с {span(pa, pb)}</i>", "",
             f"Расход: <b>{rub(t['spend_rub'])}</b>  {chg(t['spend_rub'], o['spend_rub'])}",
             f"Выручка с рекламы: <b>{rub(t['revenue_rub'])}</b>  {chg(t['revenue_rub'], o['revenue_rub'])}",
             f"ДРР: <b>{num(t['drr'] or 0, 1)}%</b>  {chg(t['drr'], o['drr'], pp=True)}"
             + (f" · {ad._drr_rating(t['drr']).lower()}" if ad._drr_rating(t["drr"]) else ""),
             f"Заказы: <b>{num(t['orders'])}</b>  {chg(t['orders'], o['orders'])}",
             f"Стоимость заказа: <b>{rub(t['cpo'] or 0)}</b>  {chg(t['cpo'], o['cpo'])}",
             f"Показы: {num(t['views'])} · клики: {num(t['clicks'])} · CTR {num(t['ctr'] or 0, 2)}%"]
    try:
        g = ad._sum_metrics(st, "advert_id")
        meta = ad._fetch_campaigns_meta()
        if meta is not None and not meta.empty:
            g = g.merge(meta[["advert_id", "name"]], on="advert_id", how="left")
        g["name"] = g.get("name", pd.Series(dtype=str)).fillna(g["advert_id"].astype(str))
        top = g.sort_values("spend_rub", ascending=False).head(5)
        lines += ["", "<b>Больше всего тратят</b>"] + [
            f"• {esc(str(n)[:40])} — {rub(s)} · ДРР {num(d or 0, 1)}%"
            for n, s, d in zip(top["name"], top["spend_rub"], top["drr"])]
        bad = g[(g["spend_rub"] >= ad.CAMPAIGN_MIN_SPEND_TO_JUDGE)
                & (g["drr"].fillna(1e9) > ad.DRR_HIGH_THRESHOLD)].sort_values("spend_rub", ascending=False).head(5)
        if not bad.empty:
            lines += ["", f"<b>⚠️ ДРР выше {num(ad.DRR_HIGH_THRESHOLD)}%</b>"] + [
                f"• {esc(str(n)[:40])} — {rub(s)}, ДРР "
                + (f"{num(d, 1)}%" if d == d and d is not None else "нет заказов")
                for n, s, d in zip(bad["name"], bad["spend_rub"], bad["drr"])]
        bal = ad._fetch_balance()
        if bal and bal.get("balance") is not None:
            lines += ["", f"Баланс рекламного кабинета: <b>{rub(bal['balance'])}</b>"]
    except Exception as e:
        print(f"[menu] реклама: {type(e).__name__}: {e}", flush=True)
    lines += ["", "<i>По статистике кампаний WB. Подробный разбор — в PDF-записке.</i>"]
    return {"text": "\n".join(lines), "photo": None, "auto": "xl",
            "kb": _files_kb("a", a, b, (("pdf", "PDF: записка"), ("xl", "Excel: кампании"),
                                        ("per", "Excel: по периодам")))}


def file_ads(code: str, a: date, b: date):
    from .. import ad_campaigns_report as ad
    s, e = a.isoformat(), b.isoformat()
    if code == "pdf":
        return f"Реклама WB — записка {span(a, b)}.pdf", ad.build_ad_campaigns_pdf_bytes(s, e), PDF
    if code == "per":
        return f"Реклама WB по периодам {span(a, b)}.xlsx", ad.build_ad_campaigns_periods_excel(s, e), XLSX
    return f"Реклама WB {span(a, b)}.xlsx", ad.build_ad_campaigns_excel(s, e), XLSX


# ---------------------------------------------------------------- 🏆 топ карточек
def report_top(a: date, b: date) -> dict | None:
    lines = [f"<b>🏆 Топ карточек · {span(a, b)}</b>", "",
             "Лучшие и худшие карточки товара за период: продажи, возвраты, остатки — "
             "тот же отчёт, что в дашборде.", "", "Excel пришлю сразу, PDF — по кнопке."]
    return {"text": "\n".join(lines), "photo": None, "auto": "xl",
            "kb": _files_kb("t", a, b, (("xl", "Excel"), ("pdf", "PDF")))}


def file_top(code: str, a: date, b: date):
    from .. import wb_top_cards_report as tc
    s, e = a.isoformat(), b.isoformat()
    if code == "pdf":
        return f"Топ карточек {span(a, b)}.pdf", tc.build_top_cards_pdf_bytes(s, e), PDF
    return f"Топ карточек {span(a, b)}.xlsx", tc.build_top_cards_excel(s, e), XLSX


# ---------------------------------------------------------------- диспетчер
def build(rep: str, a: date, b: date) -> dict | None:
    if rep == "s":
        return report_sales(a, b)
    if rep in GROUP:
        return report_group(rep, a, b)
    if rep == "k":
        return report_stocks(a, b)
    if rep == "w":
        return report_costs(a, b)
    if rep == "a":
        return report_ads(a, b)
    if rep == "t":
        return report_top(a, b)
    return None


def file(rep: str, code: str, a: date, b: date):
    """(имя, байты, mime) или None."""
    if rep == "s":
        return file_sales(code, a, b)
    if rep in GROUP:
        return file_group(rep, code, a, b)
    if rep == "k":
        return file_stocks(code, a, b)
    if rep == "w":
        return file_costs(a, b)
    if rep == "a":
        return file_ads(code, a, b)
    if rep == "t":
        return file_top(code, a, b)
    return None


HELP = ("<b>Как пользоваться</b>\n"
        "• Кнопки внизу — готовые отчёты: нажмите, выберите период — придут цифры, "
        "график и Excel. Дополнительные файлы — кнопками под отчётом.\n"
        "• Свой период — «📅 Свой период»: нажмите день начала, потом день конца. "
        "Или просто напишите даты после кнопки отчёта: 01.10–15.10.\n"
        "• Всё сравнивается с прошлым таким же периодом (месяц — с прошлым месяцем).\n"
        "• Продажи — как на сайте WB: с НДС, до СПП, после СПП и к перечислению.\n"
        "• Нестандартный вопрос — просто напишите его своими словами, ответит ИИ.\n\n"
        "Важные цифры сверяйте с дашбордом. Если что-то не так — напишите Дарье.")
