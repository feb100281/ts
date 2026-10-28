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
WEEK = 7

COLUMNS = [
    ("brand", "Бренд", "text"), ("sa", "Артикул продавца", "text"), ("nm", "Артикул WB", "id"),
    ("title", "Наименование", "text"),
    ("verdict", "Вывод", "wrap"),
    ("p0", "Цена до СПП ДО, ₽", "price"), ("pc", "Цена до СПП в дни переоценки, ₽", "price"),
    ("cut", "Изменение цены, %", "pct"),
    ("bp0", "Цена покупателя ДО, ₽", "price"), ("bp1", "Цена покупателя ПОСЛЕ, ₽", "price"),
    ("u0", "Продажи ДО, шт/день", "dec"), ("u1", "Продажи ПОСЛЕ, шт/день", "dec"),
    ("stock0", "Остаток перед переоценкой, шт", "qty"), ("stock", "Остаток сейчас, шт", "qty"),
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
    ("Хватило бы / уходит", "Остаток перед переоценкой (склады WB + FBS), делённый на продажи "
                            "в день ДО и ПОСЛЕ. Красным — остаток уходит за 3 дня и быстрее, "
                            "оранжевым — за неделю."),
    ("Недополучено", "(Цена ДО − цена ПОСЛЕ) × штуки, проданные после переоценки. Оценка: "
                     "предполагаем, что по старой цене этот объём продали бы, только дольше."),
    ("Фин. результат", "Выручка без НДС − себестоимость − комиссия − расходы WB, % к выручке, "
                       "по методике дашборда продаж. Отрицательный — продаём в убыток."),
    ("Важно", "Снижение цены может быть и из-за акции WB, а не нашей переоценки — сверяйте "
              "с историей цен в личном кабинете."),
]


def _rub(v):
    return f"{v:,.0f}".replace(",", " ")


def verdict(r) -> str:
    """Короткий вывод по артикулу для разговора."""
    parts = [f"Цена {r.p0:,.0f} → {r.pc:,.0f} ₽ ({r.cut:+.0f}%).".replace(",", " ")]
    if pd.notna(r.days_new):
        old = (f"при старой цене хватило бы на {r.days_old:.0f} дн."
               if pd.notna(r.days_old) else "при старой цене почти не продавался.")
        parts.append(f"Остаток {_rub(r.stock0)} шт уходит за {r.days_new:.0f} дн., {old}"
                     .replace("..", "."))
    if r.u0 > 0 and r.u1 > 0:
        parts.append(f"Продажи выросли в {r.u1 / r.u0:.1f} раза.".replace(".", ",", 1))
    if r.lost > 0:
        parts.append(f"Недополучено ≈ {_rub(r.lost)} ₽.")
    if pd.notna(r.m_1):
        if pd.notna(r.m_0) and r.m_0 >= 0 > r.m_1:
            parts.append(f"Ушли в убыток: фин. результат {r.m_0:.0f}% → {r.m_1:.0f}%.")
        elif r.m_1 < 0:
            parts.append(f"Продаём в убыток: фин. результат {r.m_1:.0f}%.")
        elif pd.notna(r.m_0):
            parts.append(f"Фин. результат {r.m_0:.0f}% → {r.m_1:.0f}%.")
    return " ".join(parts)


def build(d1: date, d2: date, brands=None, min_cut: float = 10.0):
    from .assistant import reprice
    hit, meta = reprice.analyze(d1, d2, min_cut=min_cut)
    if brands:
        hit = hit[hit["brand"].astype(str).str.upper().isin([b.upper() for b in brands])]
    hit = hit.copy()
    if not hit.empty:
        hit["verdict"] = [verdict(r) for r in hit.itertuples(index=False)]
    return hit, meta


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
        "qty": F(**line, num_format=mp.FMT_QTY), "money": F(**line, num_format=mp.FMT_MONEY),
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
    ws.set_column(1, 1, 46)
    ws.set_column(2, 2, 18)
    fast = hit[hit["days_new"].round() <= FAST] if not hit.empty else hit
    week = hit[hit["days_new"].round() <= WEEK] if not hit.empty else hit
    loss = hit[hit["m_1"] < 0] if not hit.empty else hit
    kpis = [("Подешевело артикулов", len(hit)),
            (f"Остаток уходит за {FAST} дня и быстрее", len(fast)),
            ("Остаток уходит за неделю и быстрее", len(week)),
            ("Продаются в убыток после переоценки", len(loss)),
            ("Недополучено к старой цене, ₽ (оценка)", float(hit["lost"].clip(lower=0).sum())
             if not hit.empty else 0)]
    r = 6
    for name, v in kpis:
        ws.write(r, 1, name, fmt["kpi_l"])
        ws.write_number(r, 2, v, fmt["kpi_v"])
        r += 1
    r += 1
    ws.write(r, 1, "Главное по артикулам (по недополученной сумме)", fmt["title"])
    r += 1
    ws.set_column(3, 3, 110)
    for row in hit.head(15).itertuples(index=False):
        ws.write(r, 1, f"{row.brand} · {row.sa} · {int(row.nm)}", fmt["text"])
        ws.write_number(r, 2, max(row.lost, 0), fmt["money"])
        ws.write(r, 3, row.verdict, fmt["wrap"])
        ws.set_row(r, 30)
        r += 1

    # ---- Артикулы
    ws = wb.add_worksheet("Артикулы")
    head(ws, f"Переоценки {period} по артикулам", len(COLUMNS))
    hdr = 6
    ws.set_row(hdr, 42)
    widths = {"text": 14, "id": 13, "wrap": 70, "price": 12, "pct": 10, "dec": 11,
              "qty": 11, "money": 14}
    for i, (key, name, k) in enumerate(COLUMNS):
        ws.write(hdr, 1 + i, name.upper(), fmt["hdr"])
        ws.set_column(1 + i, 1 + i, 40 if key == "title" else widths[k])
    r = hdr + 1
    for row in hit.itertuples(index=False):
        for i, (key, _n, k) in enumerate(COLUMNS):
            v = getattr(row, key)
            f = fmt[k]
            if key == "days_new" and pd.notna(v):
                f = fmt["red"] if round(v) <= FAST else fmt["amber"] if round(v) <= WEEK else f
            if v is None or (isinstance(v, float) and pd.isna(v)):
                ws.write_blank(r, 1 + i, None, f)
            elif k in ("text", "wrap"):
                ws.write_string(r, 1 + i, str(v), f)
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
