# gear/app/daily_sales/reprice_export.py
"""Выгрузка «Разбор переоценок»: какие артикулы подешевели в выбранные дни,
как быстро после этого уходит остаток и сколько недополучили к старой цене.

Расчёт — assistant/reprice.py, здесь меню, окно выбора дат и Excel.
"""
from __future__ import annotations

import io
from datetime import date, datetime, timedelta

import dash_mantine_components as dmc
import pandas as pd
from dash import Input, Output, State, dcc, html, no_update
from dash_iconify import DashIconify

OPEN_ID = "reprice-export-open"
MODAL_ID = "reprice-export-modal"
PERIOD_ID = "reprice-export-period"
BRANDS_ID = "reprice-export-brands"
CUT_ID = "reprice-export-cut"
RUN_ID = "reprice-export-run"
DOWNLOAD_ID = "reprice-export-download"
STATUS_ID = "reprice-export-status"

FAST = 3          # «распродали за 1–3 дня»
OVERSTOCK = 90    # остатка при старой цене на 3 месяца и больше — залежавшийся товар
NEW_DAYS = 30     # в продаже меньше 30 дней — новинка
WEEK = 7

COLUMNS = [
    ("brand", "Бренд", "text"), ("sa", "Артикул продавца", "text"), ("nm", "Артикул WB", "id"),
    ("title", "Наименование", "text"),
    ("groups", "Группа вывода", "wrap"),
    ("verdict", "Вывод", "wrap"),
    ("p0", "Цена до СПП ДО, ₽", "price"), ("pc", "Цена до СПП в дни переоценки, ₽", "price"),
    ("cut", "Изменение цены, %", "pct"),
    ("first_in", "Первое поступление", "date"), ("age", "Дней в продаже на дату переоценки", "qty"),
    ("last_upd", "Последняя поставка (УПД)", "date"),
    ("bp0", "Цена покупателя ДО, ₽", "price"), ("bp1", "Цена покупателя ПОСЛЕ, ₽", "price"),
    ("u0", "Продажи ДО, шт/день", "dec"), ("u1", "Продажи ПОСЛЕ, шт/день", "dec"),
    ("stock0", "Остаток перед переоценкой (на день до неё), шт", "qty"),
    ("stock", "Остаток на последнюю дату остатков, шт", "qty"),
    ("to0", "В пути к покупателю перед переоценкой (справочно), шт", "qty"),
    ("frm0", "В пути от покупателя перед переоценкой (справочно), шт", "qty"),
    ("to_n", "В пути к покупателю сейчас (справочно), шт", "qty"),
    ("frm_n", "В пути от покупателя сейчас (справочно), шт", "qty"),
    ("days_old", "Хватило бы при старой цене, дней", "dec"),
    ("days_new", "Уходит при новой цене, дней", "dec"),
    ("q1", "Продано после переоценки, шт", "qty"),
    ("lost", "Недополучено к старой цене, ₽", "money"),
    ("cogs_u_0", "Себестоимость, ₽/шт", "price"),
    ("m_0", "Фин. результат ДО, %", "pct"), ("m_1", "Фин. результат ПОСЛЕ, %", "pct"),
]

NOTES = [
    ("Что это", "Артикулы, у которых в выбранные дни наша цена до СПП снизилась на заданный "
                "процент и больше, и что было после: как быстро уходит остаток и сколько "
                "денег недополучили по сравнению со старой ценой."),
    ("ДО и ПОСЛЕ", "ДО — 14 дней перед первым днём переоценки. ПОСЛЕ — с первого дня "
                   "переоценки по последний загруженный день."),
    ("Цена до СПП", "Наша цена с НДС по продажам WB: продажи до СПП, ₽ / штуки. Цена "
                    "покупателя — после СПП."),
    ("Хватило бы / уходит", "Остаток перед переоценкой (склады WB + FBS; если снимок неполный — "
                            "не меньше чем «продано после + остаток сейчас»), делённый на продажи "
                            "в день ДО и ПОСЛЕ. Красным — остаток уходит за 3 дня и быстрее, "
                            "оранжевым — за неделю."),
    ("Недополучено", "(Цена ДО − цена ПОСЛЕ) × штуки, проданные после переоценки — сколько "
                     "отдали скидкой на фактически проданный объём. Оценка: предполагаем, что "
                     "по старой цене этот объём продали бы, только дольше. Для залежавшегося "
                     "остатка (по старой цене хватало на 90 дней и больше) сумма условная: "
                     "по старой цене товар почти не продавался."),
    ("Фин. результат", "Выручка без НДС − себестоимость − комиссия − расходы WB, % к выручке, "
                       "по методике дашборда продаж. Отрицательный — продаём в убыток."),
    ("В пути", "Справочно, в остаток не входит. «К покупателю» — уже заказано: склад "
               "уменьшается при заказе, а продажа появляется при выкупе, поэтому сразу после "
               "скидки часть товара видна здесь, а не в продажах. «От покупателя» — возвраты, "
               "в продажу вернётся только часть."),
    ("Новинка", "Первое поступление — самая ранняя дата из первого дня с остатком на складах "
                "WB/FBS и первой УПД поставщика. Новинка — товар в продаже меньше 30 дней на "
                "первый день переоценки."),
    ("Важно", "Снижение цены может быть и из-за акции WB, а не нашей переоценки — сверяйте "
              "с историей цен в личном кабинете."),
]


def _rub(v):
    return f"{v:,.0f}".replace(",", " ")


def verdict(r, b0: date | None = None) -> str:
    """Короткий вывод по артикулу для разговора."""
    parts = [f"Цена {r.p0:,.0f} → {r.pc:,.0f} ₽ ({r.cut:+.0f}%).".replace(",", " ")]
    if pd.notna(r.days_new) and r.stock0 > 0:
        old = (f"при старой цене хватило бы на {r.days_old:.0f} дн."
               if pd.notna(r.days_old) else "при старой цене почти не продавался.")
        on = f" на {b0:%d.%m}" if b0 else ""
        parts.append(f"Остаток{on} {_rub(r.stock0)} шт при новой цене уходит за "
                     f"{r.days_new:.0f} дн., {old}".replace("..", "."))
    to_n = getattr(r, "to_n", 0) or 0
    if to_n > 0:
        parts.append(f"Сейчас на складах {_rub(r.stock)} шт, в пути к покупателям ещё "
                     f"{_rub(to_n)} шт.")
    if r.u0 > 0 and r.u1 > 0:
        k = r.u1 / r.u0
        if k >= 1.2:
            parts.append(f"Продажи выросли в {k:.1f} раза.".replace(".", ",", 1))
        elif k <= 0.8 and round(r.u0, 1) != round(r.u1, 1):
            parts.append(f"Продажи даже снизились: {r.u0:.1f} → {r.u1:.1f} шт/день — "
                         "скидка не дала эффекта.".replace(".", ",", 2))
        else:
            parts.append("Продажи почти не изменились — скидка не дала эффекта.")
    elif r.u0 == 0 and r.u1 > 0:
        parts.append("До скидки не продавался.")
    new = pd.notna(r.age) and r.age < NEW_DAYS
    over = pd.notna(r.days_old) and r.days_old >= OVERSTOCK and not new
    if new:
        parts.append(f"Новинка: в продаже {r.age:.0f} дн. (с {pd.Timestamp(r.first_in):%d.%m}).")
    if r.lost > 0:
        parts.append(f"Недополучено ≈ {_rub(r.lost)} ₽"
                     + (" (условно: по старой цене товар почти не уходил)." if over else "."))
    if pd.notna(r.m_1):
        if pd.notna(r.m_0) and r.m_0 >= 0 > r.m_1:
            parts.append(f"Ушли в убыток: фин. результат {r.m_0:.0f}% → {r.m_1:.0f}%.")
        elif r.m_1 < 0:
            parts.append(f"Продаём в убыток: фин. результат {r.m_1:.0f}%.")
        elif pd.notna(r.m_0):
            parts.append(f"Фин. результат {r.m_0:.0f}% → {r.m_1:.0f}%.")
        if over and r.m_1 >= 0 and r.u0 > 0 and r.u1 / r.u0 >= 1.2:
            parts.append("Распродажа залежавшегося остатка в плюс — снижение оправдано.")
    return " ".join(parts)


def build(d1: date, d2: date, brands=None, min_cut: float = 10.0):
    from .assistant import reprice
    hit, meta = reprice.analyze(d1, d2, min_cut=min_cut)
    if brands:
        hit = hit[hit["brand"].astype(str).str.upper().isin([b.upper() for b in brands])]
    hit = hit.copy()
    if not hit.empty:
        hit["verdict"] = [verdict(r, meta["b0"]) for r in hit.itertuples(index=False)]
        hit["groups"] = tag_groups(hit)
    else:
        hit["groups"] = pd.Series(dtype=str)
    return hit, meta


# группы выводов: (короткое имя для колонки, заголовок, пояснение, условие)
def _k(h):
    return h["u1"] / h["u0"].where(h["u0"] > 0)


def _new(h):
    return h["age"] < NEW_DAYS


GROUPS = [
    ("Скидка на новинку", "Скидка на новый товар (в продаже меньше 30 дней)",
     lambda g: "Товар только поступил, а цену уже снизили — новинки обычно продают по полной "
               f"цене. Недополучено ≈ {_rub(g['lost'].clip(lower=0).sum())} ₽.",
     lambda h: _new(h).fillna(False)),
    ("Скидка без роста продаж", "Снижение цены не увеличило продажи",
     lambda g: f"Продажи выросли меньше чем на 20% или снизились. Недополучено ≈ "
               f"{_rub(g['lost'].clip(lower=0).sum())} ₽ без прироста объёма.",
     lambda h: (h["u0"] > 0) & (_k(h) < 1.2)),
    ("Ускоренная распродажа", "Ускоренная распродажа ходового остатка",
     lambda g: "При прежней цене остаток ушёл бы за 1–3 месяца, после снижения он уходит "
               f"минимум втрое быстрее. Недополучено ≈ {_rub(g['lost'].clip(lower=0).sum())} ₽; "
               "снижение можно было растянуть.",
     lambda h: (h["days_old"] >= 30) & (h["days_old"] < OVERSTOCK)
               & (h["days_new"] <= h["days_old"] / 3)),
    ("Переход в убыток", "Переход в убыток после переоценки",
     lambda g: "До снижения цены финансовый результат был положительным, после — отрицательный.",
     lambda h: (h["m_0"] >= 0) & (h["m_1"] < 0)),
    ("Скидка 40%+ на ходовом", "Глубокие скидки (40% и больше) на ходовом товаре",
     lambda g: "Остатка при прежней цене хватало меньше чем на 3 месяца — такую скидку можно "
               f"было не давать. Недополучено ≈ {_rub(g['lost'].clip(lower=0).sum())} ₽.",
     lambda h: (h["cut"] <= -40) & ((h["days_old"] < OVERSTOCK) | h["days_old"].isna())),
    ("Оправданная распродажа", "Оправданная распродажа залежавшегося остатка",
     lambda g: "При прежней цене остатка хватало на 3 месяца и больше, после снижения товар "
               "пошёл, а финансовый результат остался положительным. Это высвобождает деньги "
               "и снижает платное хранение — снижение цены оправдано.",
     lambda h: (h["days_old"] >= OVERSTOCK) & (h["m_1"] >= 0) & (_k(h) >= 1.2)
               & ~_new(h).fillna(False)),
]


def tag_groups(hit: pd.DataFrame) -> pd.Series:
    """Колонка «Группа вывода»: все группы артикула через «; »."""
    marks = [(name, cond(hit).fillna(False)) for name, _t, _n, cond in GROUPS]
    return pd.Series(["; ".join(n for n, m in marks if m.iloc[i]) for i in range(len(hit))],
                     index=hit.index)


def findings(hit: pd.DataFrame) -> list[tuple[str, str, str, pd.DataFrame]]:
    """Группы выводов: (короткое имя, заголовок, пояснение, артикулы)."""
    if hit.empty:
        return []
    out = []
    for name, title, note, cond in GROUPS:
        g = hit[cond(hit).fillna(False)].sort_values("lost", ascending=False)
        if len(g):
            out.append((name, f"{title} — {len(g)} арт.", note(g), g))
    return out


RECOMMENDATIONS = [
    "Снижать цену поэтапно (шаг 5–10%) с оценкой реакции продаж через 2–3 дня, а не "
    "единовременно на 20–40%.",
    "Для артикулов с запасом на месяц и больше ориентироваться на плановую "
    "оборачиваемость, а не на максимальную скорость распродажи.",
    "Переоценки, после которых финансовый результат становится отрицательным, "
    "согласовывать заранее.",
    "Перед снижением цены проверять, участвует ли артикул в акции WB, чтобы скидки "
    "не суммировались.",
]


def table_head(ws, fmt, r):
    """Шапка коротких таблиц артикулов на листах «Итог» и «Ключевые выводы»."""
    for c, name in ((1, "БРЕНД · АРТИКУЛ ПРОДАВЦА · АРТИКУЛ WB"), (2, "НАИМЕНОВАНИЕ"),
                    (3, "НЕДОПОЛУЧЕНО, ₽"), (4, "ВЫВОД")):
        ws.write(r, c, name, fmt["hdr"])
    ws.set_row(r, 30)


def table_widths(ws):
    ws.set_column(1, 1, 40)
    ws.set_column(2, 2, 34)
    ws.set_column(3, 3, 21)
    ws.set_column(4, 4, 100)


def table_row(ws, fmt, r, row):
    ws.write(r, 1, f"{row.brand} · {row.sa} · {int(row.nm)}", fmt["text"])
    ws.write(r, 2, str(row.title or ""), fmt["wrap"])
    ws.write_number(r, 3, max(row.lost, 0), fmt["money"])
    ws.write(r, 4, row.verdict, fmt["wrap"])
    ws.set_row(r, 30)


JUSTIFIED = "Оправданная распродажа"


def structure_block(ws, fmt, r, hit) -> int:
    """Из чего складывается недополученная сумма: проблемные (без двойного
    счёта), оправданная распродажа, без замечаний."""
    if hit.empty:
        return r
    lost = hit["lost"].clip(lower=0)
    g = hit["groups"].fillna("")
    ok = g.str.contains(JUSTIFIED, regex=False)
    bad = (g != "") & ~ok
    rows = [("Проблемные — хотя бы одна группа замечаний (без двойного счёта)", bad, "kpi")]
    for name, title, _n, _c in GROUPS:
        if name == JUSTIFIED:
            continue
        m = g.str.contains(name, regex=False)
        if m.any():
            rows.append((f"   в т. ч. {title.lower()}", m, "sub"))
    rows += [("Оправданная распродажа залежавшегося остатка", ok, "kpi"),
             ("Без замечаний: продажи выросли, остались в плюсе", g == "", "kpi")]
    ws.write(r, 1, "Из чего складывается недополученная сумма", fmt["title"])
    r += 1
    for c, name in ((1, "КАТЕГОРИЯ"), (2, "АРТИКУЛОВ"), (3, "НЕДОПОЛУЧЕНО, ₽")):
        ws.write(r, c, name, fmt["hdr"])
    ws.set_row(r, 22)
    r += 1
    for label, m, kind in rows:
        lf, vf = (fmt["kpi_l"], fmt["kpi_v"]) if kind == "kpi" else (fmt["muted"], fmt["money"])
        ws.write(r, 1, label, lf)
        ws.write_number(r, 2, int(m.sum()), fmt["qty"] if kind == "sub" else fmt["kpi_v"])
        ws.write_number(r, 3, float(lost[m].sum()), vf)
        r += 1
    ws.write(r, 1, "Итого", fmt["tot_l"])
    ws.write_number(r, 2, len(hit), fmt["tot"])
    ws.write_number(r, 3, float(lost.sum()), fmt["tot"])
    r += 1
    ws.write(r, 1, "Группы «в т. ч.» пересекаются: один артикул может попасть в несколько, "
                   "поэтому их сумма больше строки «Проблемные».", fmt["muted"])
    return r + 2


def findings_sheet(wb, fmt, head, hit, meta):
    ws = wb.add_worksheet("Ключевые выводы")
    head(ws, "Ключевые выводы", 4)
    table_widths(ws)
    r = 6
    if hit.empty:
        ws.write(r, 1, "Снижений цены за выбранные дни нет.", fmt["text"])
        return
    q = hit["q1"].sum()
    avg_cut = float((hit["cut"] * hit["q1"]).sum() / q) if q else float(hit["cut"].mean())
    bins = [(-100, -40, "40% и больше"), (-40, -30, "30–40%"), (-30, -20, "20–30%"),
            (-20, -abs(0.01), "до 20%")]
    ws.write(r, 1, "Масштаб переоценки", fmt["lbl"])
    ws.merge_range(r, 2, r, 4, "", fmt["wrap"])
    ws.write(r, 2, f"{len(hit)} арт. ({', '.join(f'{b} — {n}' for b, n in hit['brand'].value_counts().head(4).items())}); "
                   f"средняя скидка по проданным штукам {avg_cut:.0f}%. Недополучено за "
                   f"{meta['n1']} дн. ≈ {_rub(hit['lost'].clip(lower=0).sum())} ₽.", fmt["wrap"])
    ws.set_row(r, 30)
    r += 1
    ws.write(r, 1, "Глубина снижения", fmt["lbl"])
    ws.merge_range(r, 2, r, 4, "", fmt["wrap"])
    ws.write(r, 2, "; ".join(f"{name} — {int(((hit['cut'] > lo) & (hit['cut'] <= hi)).sum())} арт."
                             for lo, hi, name in bins), fmt["wrap"])
    r += 2
    for name, title, note, rows in findings(hit):
        ws.write(r, 1, title, fmt["title"])
        r += 1
        ws.write(r, 1, note, fmt["sub"])
        r += 1
        table_head(ws, fmt, r)
        r += 1
        for row in rows.head(5).itertuples(index=False):
            table_row(ws, fmt, r, row)
            r += 1
        if len(rows) > 5:
            ws.write(r, 1, f"…и ещё {len(rows) - 5} — на листе «Артикулы»: фильтр по колонке "
                           f"«Группа вывода», текст содержит «{name}»", fmt["muted"])
            r += 1
        r += 1
    ws.write(r, 1, "Рекомендации", fmt["title"])
    r += 1
    for i, t in enumerate(RECOMMENDATIONS, 1):
        ws.write(r, 1, f"{i}.", fmt["lbl"])
        ws.merge_range(r, 2, r, 4, t, fmt["wrap"])
        ws.set_row(r, 22)
        r += 1


def to_excel(hit: pd.DataFrame, meta: dict, min_cut: float, brands) -> tuple[bytes, str]:
    from gear.management.commands import mp
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"nan_inf_to_errors": True})
    base = {"font_name": mp.FONT, "font_size": 9, "font_color": "#" + mp.TEXT,
            "valign": "vcenter"}
    line = {"bottom": 1, "bottom_color": "#" + mp.LINE}
    F = lambda **k: wb.add_format({**base, **k})
    fmt = {
        "title": F(font_size=14, bold=True),
        "sub": F(font_color="#" + mp.TEXT_2),
        "muted": F(font_color="#" + mp.MUTED),
        "rule": wb.add_format({"bottom": 1, "bottom_color": "#" + mp.NAVY}),
        "hdr": F(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY, text_wrap=True,
                 align="center", border=1, border_color="#" + mp.NAVY_2),
        "text": F(**line, indent=1), "wrap": F(**line, text_wrap=True, valign="top"),
        "id": F(**line, num_format="0", align="left"),
        "qty": F(**line, num_format=mp.FMT_QTY),
        "date": F(**line, num_format="dd.mm.yyyy", align="center"), "money": F(**line, num_format=mp.FMT_MONEY),
        "price": F(**line, num_format=mp.FMT_MONEY), "dec": F(**line, num_format="0.0"),
        "pct": F(**line, num_format='0.0;[Red]-0.0'),
        "kpi_l": F(bold=True, font_color="#" + mp.NAVY_3, **line),
        "kpi_v": F(bold=True, font_size=11, **line, num_format=mp.FMT_MONEY),
        "lbl": F(bold=True, font_color="#" + mp.NAVY_3, valign="top", **line),
        "red": F(**line, num_format="0.0", bg_color="#F8D7D3", bold=True),
        "amber": F(**line, num_format="0.0", bg_color="#FCEBCF"),
        "tot": F(bold=True, top=1, bottom=1, num_format=mp.FMT_MONEY),
        "tot_l": F(bold=True, top=1, bottom=1, indent=1),
    }
    period = f"{meta['d1']:%d.%m}–{meta['d2']:%d.%m.%Y}"
    sub = (f"Снижение цены от {min_cut:.0f}% · ДО: {meta['a0']:%d.%m}–{meta['b0']:%d.%m} · "
           f"ПОСЛЕ: {meta['d1']:%d.%m}–{meta['last']:%d.%m} ({meta['n1']} дн.)"
           + f" · остаток перед переоценкой — на {meta['b0']:%d.%m}"
           + (f", сейчас — на {pd.Timestamp(meta['stock_date']):%d.%m}"
              if meta.get("stock_date") is not None else "")
           + (" · бренды: " + ", ".join(brands) if brands else ""))

    def head(ws, title, ncol):
        ws.hide_gridlines(2)
        ws.set_column(0, 0, 2)
        ws.write(1, 1, title, fmt["title"])
        ws.write(2, 1, sub, fmt["sub"])
        ws.write(3, 1, f"Сформировано {datetime.now():%d.%m.%Y %H:%M}", fmt["muted"])
        for c in range(1, ncol + 1):
            ws.write_blank(4, c, None, fmt["rule"])
        ws.set_row(1, 24)

    # ---- Итог
    ws = wb.add_worksheet("Итог")
    head(ws, f"Разбор переоценок {period}", 6)
    table_widths(ws)
    fast = hit[hit["days_new"].round() <= FAST] if not hit.empty else hit
    week = hit[hit["days_new"].round() <= WEEK] if not hit.empty else hit
    loss = hit[hit["m_1"] < 0] if not hit.empty else hit
    kpis = [("Подешевело артикулов", len(hit)),
            (f"Остаток уходит за {FAST} дня и быстрее", len(fast)),
            ("Остаток уходит за неделю и быстрее", len(week)),
            ("Продаются в убыток после переоценки", len(loss)),
            ("Недополучено к старой цене, ₽ (оценка)", float(hit["lost"].clip(lower=0).sum())
             if not hit.empty else 0),
            ("   в т. ч. по залежавшемуся остатку (условно), ₽",
             float(hit.loc[hit["days_old"] >= OVERSTOCK, "lost"].clip(lower=0).sum())
             if not hit.empty else 0)]
    r = 6
    for name, v in kpis:
        ws.write(r, 1, name, fmt["kpi_l"])
        ws.write_number(r, 2, v, fmt["kpi_v"])
        r += 1
    r += 1
    r = structure_block(ws, fmt, r, hit)
    ws.write(r, 1, "Главное по артикулам (по недополученной сумме)", fmt["title"])
    r += 1
    table_head(ws, fmt, r)
    r += 1
    for row in hit.head(15).itertuples(index=False):
        table_row(ws, fmt, r, row)
        r += 1

    # ---- Ключевые выводы
    findings_sheet(wb, fmt, head, hit, meta)

    # ---- Артикулы
    ws = wb.add_worksheet("Артикулы")
    head(ws, f"Переоценки {period} по артикулам", len(COLUMNS))
    hdr = 6
    ws.set_row(hdr, 42)
    widths = {"text": 14, "id": 13, "wrap": 70, "price": 12, "pct": 10, "dec": 11,
              "qty": 11, "money": 14, "date": 12}
    for i, (key, name, k) in enumerate(COLUMNS):
        ws.write(hdr, 1 + i, name.upper(), fmt["hdr"])
        ws.set_column(1 + i, 1 + i, 40 if key == "title" else 24 if key == "groups"
                      else widths[k])
    r = hdr + 1
    for row in hit.itertuples(index=False):
        for i, (key, _n, k) in enumerate(COLUMNS):
            v = getattr(row, key)
            f = fmt[k]
            if key == "days_new" and pd.notna(v):
                f = fmt["red"] if round(v) <= FAST else fmt["amber"] if round(v) <= WEEK else f
            if v is None or (not isinstance(v, str) and pd.isna(v)):
                ws.write_blank(r, 1 + i, None, f)
            elif k in ("text", "wrap"):
                ws.write_string(r, 1 + i, str(v), f)
            elif k == "date":
                ws.write_datetime(r, 1 + i, pd.Timestamp(v).to_pydatetime(), f)
            else:
                ws.write_number(r, 1 + i, float(v), f)
        ws.set_row(r, 42)
        r += 1
    if len(hit):
        li = [k for k, *_ in COLUMNS].index("lost")
        ws.write(r, 1, "ИТОГО", fmt["tot_l"])
        col = xlsxwriter.utility.xl_col_to_name(1 + li)
        ws.write_formula(r, 1 + li, f"=SUBTOTAL(9,{col}{hdr + 2}:{col}{r})", fmt["tot"],
                         float(hit["lost"].sum()))
        ws.autofilter(hdr, 1, r - 1, len(COLUMNS))
    ws.freeze_panes(hdr + 1, 5)

    # ---- Как читать
    ws = wb.add_worksheet("Как читать")
    head(ws, "Как читать разбор", 2)
    ws.set_column(1, 1, 24)
    ws.set_column(2, 2, 100)
    for i, (a, b) in enumerate(NOTES):
        ws.write(6 + i, 1, a, fmt["lbl"])
        ws.write(6 + i, 2, b, fmt["wrap"])
        ws.set_row(6 + i, 32)

    wb.close()
    name = f"Переоценки_{meta['d1']:%Y%m%d}-{meta['d2']:%Y%m%d}.xlsx"
    return buf.getvalue(), name


# ---------------------------------------------------------------- UI
def reprice_menu_item():
    return dmc.MenuItem(
        dmc.Box([
            dmc.Text("Разбор переоценок", size="sm", fw=600),
            dmc.Text("Что подешевело, как быстро ушло, сколько недополучили", size="xs",
                     c="dimmed"),
        ]),
        id=OPEN_ID, n_clicks=0,
        leftSection=DashIconify(icon="solar:tag-price-linear", width=18),
    )


def reprice_modal():
    from .wb_sales_export import brand_options, last_sales_date
    end = last_sales_date()
    start = end - timedelta(days=1)
    return dmc.Modal(
        id=MODAL_ID, opened=False, centered=True, size="lg", zIndex=10010,
        title=dmc.Group(gap=8, children=[
            DashIconify(icon="solar:tag-price-linear", width=22, color="#2F6656"),
            dmc.Text("Разбор переоценок", fw=700, size="lg"),
        ]),
        children=dmc.Stack(gap="md", children=[
            dmc.Text("Выберите дни, когда меняли цены. В Excel — по каждому артикулу: цена до "
                     "и после, как быстро уходит остаток, сколько недополучили к старой цене "
                     "и что стало с маржой. Для одного дня нажмите на дату дважды.",
                     size="sm", c="dimmed"),
            dmc.DatePickerInput(
                id=PERIOD_ID, type="range", label="Дни переоценки",
                value=[start.isoformat(), end.isoformat()],
                valueFormat="DD.MM.YYYY", maxDate=end.isoformat(),
                allowSingleDateInRange=True,
                leftSection=DashIconify(icon="solar:calendar-linear", width=16),
                popoverProps={"zIndex": 10020},
            ),
            dmc.NumberInput(id=CUT_ID, label="Снижение цены от, %", value=10, min=1, max=90,
                            step=5),
            dmc.MultiSelect(id=BRANDS_ID, label="Бренды", placeholder="Все бренды",
                            data=brand_options(), searchable=True, clearable=True,
                            comboboxProps={"zIndex": 10020}),
            dmc.Group(justify="flex-end", children=[
                dmc.Button("Скачать Excel", id=RUN_ID, color="teal",
                           leftSection=DashIconify(icon="solar:download-minimalistic-bold",
                                                   width=18)),
            ]),
            dcc.Loading(type="dot", color="#2F6656",
                        children=html.Div(id=STATUS_ID, style={"minHeight": 20})),
        ]),
    )


def reprice_download():
    return dcc.Download(id=DOWNLOAD_ID)


def register_reprice_export_callbacks(app):

    @app.callback(Output(MODAL_ID, "opened"), Input(OPEN_ID, "n_clicks"),
                  prevent_initial_call=True)
    def _open(n):
        return True if n else no_update

    @app.callback(
        Output(DOWNLOAD_ID, "data"), Output(STATUS_ID, "children"),
        Input(RUN_ID, "n_clicks"),
        State(PERIOD_ID, "value"), State(BRANDS_ID, "value"), State(CUT_ID, "value"),
        prevent_initial_call=True,
    )
    def _run(n, period, brands, cut):
        if not n:
            return no_update, no_update
        if not period or not period[0]:
            return no_update, dmc.Text("Выберите дни переоценки.", c="red", size="sm")
        d1 = date.fromisoformat(str(period[0])[:10])
        d2 = date.fromisoformat(str(period[1])[:10]) if len(period) > 1 and period[1] else d1
        cut = float(cut or 10)
        try:
            hit, meta = build(d1, d2, brands or [], cut)
            data, fname = to_excel(hit, meta, cut, brands or [])
        except Exception as e:
            return no_update, dmc.Text(f"Ошибка: {type(e).__name__}: {e}", c="red", size="sm")
        msg = dmc.Text(f"Готово: {fname} · артикулов: {len(hit)}", c="teal", size="sm")
        return dcc.send_bytes(data, filename=fname), msg
