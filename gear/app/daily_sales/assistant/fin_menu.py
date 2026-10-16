# gear/app/daily_sales/assistant/fin_menu.py
"""Меню финансового бота: готовые отчёты по кнопкам, без ИИ.

Тот же движок, что у бота продаж (menu.py): постоянное меню, период кнопками,
календарём или датами текстом, карточка с цифрами и Excel. Данные — те же
запросы, что мэн пак, дашборд «Управленческий пакет» и инструменты помощника
(treasury, cashflow, pl, finance_extra, wb_payouts, counterparties).

Контрагенты показываются полностью, включая ИП и физлиц (в ИИ — маска). callback_data: «fm:…» — формат как у menu.py.
"""
from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd

from . import menu as M
from .menu import XLSX, chg, esc, from_ymd, ndays, num, rub, span, ymd  # noqa: F401

REPORTS = {
    "b": "💰 Остатки на счетах",
    "f": "📋 Движение денег",
    "p": "💸 Оплаты контрагента",
    "k": "🛡 Проверка контрагента",
    "s": "🔍 Поиск платежей",
    "c": "📊 Месяц к месяцу",
    "t": "🎯 Точка безубыточности",
    "w": "📥 Поступления от WB",
    "l": "🏦 Займы",
    "x": "💱 Курсы валют",
    "u": "🚚 Приходы (УПД)",
    "mp": "📦 Мэн пак",
}
QUERY = {"p", "k", "s"}            # сначала текст: название, ИНН, сумма
BY_TEXT = {v: k for k, v in REPORTS.items()}
BTN_AI = M.BTN_AI
BTN_HELP = M.BTN_HELP
SINGLE_DAY = {"x"}
DATA_START = date(2024, 1, 1)

PRESETS = {
    "b": (("y", "На вчера"), ("7", "За 7 дней"), ("m", "С начала месяца"), ("pm", "Прошлый месяц")),
    "f": (("y", "Вчера"), ("7", "7 дней"), ("w", "Прошлая неделя"), ("m", "Этот месяц"),
          ("pm", "Прошлый месяц"), ("30", "30 дней")),
    "p": (("m", "Этот месяц"), ("pm", "Прошлый месяц"), ("q", "3 месяца"), ("ytd", "С начала года"),
          ("12", "12 месяцев")),
    "c": (("pm", "Прошлый месяц"), ("m", "Этот месяц")),
    "t": (("pm", "Прошлый месяц"), ("m", "Этот месяц")),
    "w": (("7", "7 дней"), ("m", "Этот месяц"), ("pm", "Прошлый месяц"), ("30", "30 дней")),
    "l": (("y", "На сегодня"), ("pm", "На конец прошлого месяца")),
    "x": (("y", "Сегодня"), ("pm", "Конец прошлого месяца")),
    "mp": (("pm", "Прошлый месяц"), ("m", "Текущий месяц")),
    "u": (("m", "Этот месяц"), ("pm", "Прошлый месяц")),
}
MONTHLY = {"c", "t", "mp", "u"}          # отчёт за месяц: берём месяц конечной даты

AI_TEXT = ("🤖 <b>Спросите своими словами</b>\n"
           "Если нужного раздела нет на кнопках — просто напишите вопрос обычным сообщением: "
           "прибыль, деньги, займы, договоры, прогноз. Отвечу и при необходимости пришлю Excel.")
HELP = ("<b>Как пользоваться</b>\n"
        "• Кнопки внизу — готовые отчёты: нажмите, выберите период — придут цифры и Excel.\n"
        "• Свой период — «📅 Свой период» (день начала, потом день конца) или просто напишите "
        "даты: 01.10–15.10.\n"
        "• «Оплаты контрагента», «Проверка контрагента», «Поиск платежей» — после кнопки "
        "напишите название, ИНН или сумму.\n"
        "• P&amp;L и точка безубыточности — по данным мэн пака; движение денег — по выписке.\n"
        "• «🚚 Приходы (УПД)» — что и когда пришло; файлы документов присылаю кнопкой 📎.\n"
        "• Нужного раздела нет — напишите вопрос своими словами, ответит ИИ.\n\n"
        "Важные цифры сверяйте с мэн паком. Если что-то не так — напишите Дарье.")


def keyboard() -> dict:
    r = REPORTS
    return {"keyboard": [[{"text": r["b"]}, {"text": r["f"]}],
                         [{"text": r["p"]}, {"text": r["k"]}],
                         [{"text": r["s"]}, {"text": r["c"]}],
                         [{"text": r["t"]}, {"text": r["w"]}],
                         [{"text": r["l"]}, {"text": r["x"]}],
                         [{"text": r["u"]}, {"text": r["mp"]}],
                         [{"text": BTN_AI}, {"text": BTN_HELP}]],
            "resize_keyboard": True, "is_persistent": True,
            "input_field_placeholder": "Кнопка или вопрос своими словами…"}


# ---------------------------------------------------------------- клавиатуры и даты
def _retag(kb: dict) -> dict:
    """Клавиатуры menu.py → префикс финансового бота."""
    for row in kb.get("inline_keyboard", []):
        for b in row:
            if b.get("callback_data", "").startswith("mn:"):
                b["callback_data"] = "fm:" + b["callback_data"][3:]
    return kb


def loaded() -> date:
    """Последний день с движением денег (банк загружен по этот день)."""
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT MAX(date_from::date) FROM public.cf_to_csv")
            d = cur.fetchone()[0]
        return min(d, date.today()) if d else date.today() - timedelta(days=1)
    except Exception:
        return date.today() - timedelta(days=1)


def preset(code: str, hi: date) -> tuple[date, date]:
    if code == "q":
        a = (hi.replace(day=1) - timedelta(days=1)).replace(day=1)
        return (a - timedelta(days=1)).replace(day=1), hi
    if code == "ytd":
        return hi.replace(month=1, day=1), hi
    if code == "12":
        return hi - timedelta(days=364), hi
    return M.preset(code, hi)


def parse_range(text: str, hi: date):
    return M.parse_range(text, hi)


def ask_text(rep: str) -> str:
    if rep in MONTHLY:
        return f"<b>{REPORTS[rep]}</b>\nЗа какой месяц? Нажмите кнопку или напишите дату внутри месяца."
    if rep in SINGLE_DAY or rep == "l":
        return f"<b>{REPORTS[rep]}</b>\nНа какую дату? Нажмите кнопку или напишите дату: <code>15.10</code>"
    return (f"<b>{REPORTS[rep]}</b>\nЗа какой период? Нажмите кнопку или напишите даты: "
            "<code>01.10–15.10</code>, <code>05.10</code>")


def period_kb(rep: str) -> dict:
    btn = [{"text": t, "callback_data": f"fm:p:{rep}:{c}"} for c, t in PRESETS.get(rep, ())]
    rows = [btn[i:i + 3] for i in range(0, len(btn), 3)]
    rows.append([{"text": "📅 " + ("Другая дата" if rep in SINGLE_DAY or rep in MONTHLY or rep == "l"
                                   else "Свой период"), "callback_data": f"fm:c:{rep}::0"}])
    return {"inline_keyboard": rows}


def calendar_kb(rep, year, month, start, lo, hi):
    single = rep in SINGLE_DAY or rep in MONTHLY or rep == "l"
    saved = set(M.SINGLE_DAY)
    try:
        if single:
            M.SINGLE_DAY.add(rep)
        return _retag(M.calendar_kb(rep, year, month, start, lo, hi))
    finally:
        M.SINGLE_DAY.clear()
        M.SINGLE_DAY.update(saved)


def _files_kb(rep, a, b, items, again=True) -> dict:
    return _retag(M._files_kb(rep, a, b, items)) if again else {"inline_keyboard": []}


def query_prompt(rep: str) -> str:
    return {
        "p": "💸 <b>Оплаты контрагента</b>\nНапишите часть названия или ИНН — например "
             "<b>спутник</b> или <b>7708</b>.",
        "k": "🛡 <b>Проверка контрагента</b>\nНапишите <b>ИНН</b> или <b>название</b> — покажу "
             "карточку, риски и наши договоры с ним.",
        "s": "🔍 <b>Поиск платежей</b> за 12 месяцев\nНапишите, что искать:\n"
             "• слово из названия контрагента, договора или статьи — <b>аренда</b>, <b>лужники</b>\n"
             "• сумму — <b>45000</b> или <b>45 000,50</b>",
    }[rep]


# ---------------------------------------------------------------- общие помощники
def _book(title, subtitle, sheets, notes=None) -> bytes:
    return M._book(title, subtitle, sheets, notes)


_NOISE = re.compile(r"(НАЧНИ ОТВЕТ|ВНИМАНИЕ:|Как объяснять|Называй|counterparty_info|wb_sales|"
                    r"pl_report|scenario_report|В ответе|ВСЕГДА показывай)", re.I)


def tsv_card(text: str, icon: str = "") -> tuple[str, list]:
    """Текст инструмента помощника (строки с табами) → карточка Telegram и листы Excel."""
    out, sheets, head, rows, title = [], [], None, [], None

    def flush():
        nonlocal head, rows
        if head and rows:
            sheets.append((f"Таблица {len(sheets) + 1}", head, rows))
        head, rows = None, []

    for i, ln in enumerate((text or "").split("\n")):
        if _NOISE.search(ln):
            continue
        if "\t" in ln:
            cols = [c.strip() for c in ln.split("\t")]
            if head is None:
                head = [re.sub(r"\s*\(.*?\)$", "", c) for c in cols]
                continue
            rows.append(cols)
            first, rest = cols[0], cols[1:]
            bits = [f"{h.lower()} <b>{esc(v)}</b>" if j == len(rest) - 1 else f"{h.lower()} {esc(v)}"
                    for j, (h, v) in enumerate(zip(head[1:], rest)) if v and v not in ("—", "0")]
            out.append(f"• {esc(first)} — " + " · ".join(bits))
            continue
        flush()
        s = ln.strip()
        if not s:
            out.append("")
            continue
        if title is None:
            title = s
            out.append(f"<b>{icon} {esc(s[:1] + s[1:].lower()) if s.isupper() else esc(s)}</b>")
            continue
        if s.isupper() or (s.endswith(":") and len(s) < 60):
            out.append(f"<b>{esc(s.rstrip(':'))}</b>")
        else:
            out.append(esc(s))
    flush()
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip(), sheets


def _num(v):
    try:
        return float(str(v).replace(" ", "").replace(" ", "").replace(",", ".").replace("−", "-"))
    except ValueError:
        return v


def _tsv_book(title, sub, sheets):
    clean = [(n, h, [[_num(c) for c in r] for r in rows]) for n, h, rows in sheets]
    return _book(title, sub, clean) if clean else None


# ---------------------------------------------------------------- графики
def _chart(fn):
    try:
        return fn()
    except Exception as e:
        print(f"[fin_menu] график: {type(e).__name__}: {e}", flush=True)
        return None


def chart_flow(days, ins, outs, title, sub) -> bytes:
    """Поступления вверх, выплаты вниз, чистый поток — линией (млн ₽)."""
    from . import digest_charts as ch
    plt = ch._plt()
    n = len(days)
    fig, ax = plt.subplots(figsize=(10.8, 7.6), dpi=100)
    xs = range(n)
    ax.bar(xs, [v / 1e6 for v in ins], width=0.72, color=ch.GREEN, label="поступления")
    ax.bar(xs, [-v / 1e6 for v in outs], width=0.72, color=ch.WARM, alpha=.85, label="выплаты")
    net = [(i - o) / 1e6 for i, o in zip(ins, outs)]
    ax.plot(xs, net, color=ch.INK, lw=2, marker="o", ms=4, label="чистый поток")
    ax.axhline(0, color=ch.AXIS, lw=1)
    step = 1 if n <= 10 else 3 if n <= 31 else 7
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{d:%d.%m}" if (n - 1 - i) % step == 0 else "" for i, d in enumerate(days)],
                       color=ch.MUTED, fontsize=12)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}".replace(".", ","))
    ax.tick_params(axis="y", labelcolor=ch.MUTED, labelsize=12)
    ax.yaxis.grid(True, color=ch.GRID, lw=1)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=12.5, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=3)
    ch._clean(ax)
    ch._head(fig, title, sub)
    fig.subplots_adjust(left=0.08, right=0.96, top=0.8, bottom=0.1)
    return ch._png(plt, fig)


def chart_months(labels, bars, line, bar_name, line_name, title, sub, dashed=False) -> bytes:
    """Столбики по месяцам (млн ₽) и линия: прибыль или ТБУ."""
    from . import digest_charts as ch
    plt = ch._plt()
    n = len(labels)
    fig, ax = plt.subplots(figsize=(10.8, 7.6), dpi=100)
    xs = range(n)
    ax.bar(xs, [v / 1e6 for v in bars], width=0.62, color=[ch.PALE] * (n - 1) + [ch.GREEN], label=bar_name)
    pts = [(x, v / 1e6) for x, v in zip(xs, line) if v is not None]
    if pts:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=ch.WARM, lw=2.5, marker="o", ms=6,
                ls=(0, (5, 4)) if dashed else "-", label=line_name)
        for x, v in pts:
            ax.text(x, v, f" {v:.1f}".replace(".", ","), color=ch.WARM, fontsize=11.5, va="bottom",
                    ha="center", fontweight="bold")
    for x, v in zip(xs, bars):
        ax.text(x, v / 1e6 * 0.5 if v > 0 else 0, f"{v / 1e6:.1f}".replace(".", ","), ha="center",
                color=ch.INK if x == n - 1 else ch.MUTED, fontsize=11.5)
    ax.axhline(0, color=ch.AXIS, lw=1)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, color=ch.MUTED, fontsize=12)
    ax.yaxis.set_visible(False)
    ax.legend(frameon=False, fontsize=12.5, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2)
    ch._clean(ax)
    ch._head(fig, title, sub)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.8, bottom=0.1)
    return ch._png(plt, fig)


def _daily(df, a, b):
    days = [a + timedelta(days=i) for i in range(ndays(a, b))]
    if df is None or df.empty:
        return days, [0] * len(days), [0] * len(days)
    g_in = df[df.amount > 0].groupby("d").amount.sum()
    g_out = -df[df.amount < 0].groupby("d").amount.sum()
    return days, [float(g_in.get(d, 0)) for d in days], [float(g_out.get(d, 0)) for d in days]


# ---------------------------------------------------------------- 💰 остатки
def _balances(on: date):
    from .treasury import _treasury
    rows, deposits, last_bank = _treasury(on)
    banks = {}
    for r in rows:
        if r[0] == "BANK":
            _, name, cur, status, _i, _o, bal, *_ = r
            banks[(name, cur)] = (status, float(bal or 0))
    wb = next((r for r in rows if r[0] == "WB"), None)
    return banks, float(deposits or 0), wb, last_bank


def report_balances(a: date, b: date) -> dict | None:
    end, dep, wb, last_bank = _balances(b)
    if not end and not wb:
        return None
    beg, dep0, wb0, _ = _balances(a - timedelta(days=1))
    by_cur, by_cur0 = defaultdict(float), defaultdict(float)
    for (n, c), (_, v) in end.items():
        by_cur[c] += v
    for (n, c), (_, v) in beg.items():
        by_cur0[c] += v
    wb_bal = float(wb[6] or 0) if wb else 0.0
    wb_bal0 = float(wb0[6] or 0) if wb0 else 0.0
    total = by_cur.get("RUB", 0) + dep + wb_bal
    total0 = by_cur0.get("RUB", 0) + dep0 + wb_bal0
    since = a - timedelta(days=1)
    lines = [f"<b>💰 Остатки на {b:%d.%m.%Y}</b>",
             f"<i>изменение с {since:%d.%m.%Y}"
             + (f" · банк загружен по {last_bank:%d.%m.%Y}" if last_bank else "") + "</i>", "",
             f"Всего в рублях: <b>{rub(total)}</b>  {_dlt(total, total0)}"]
    for c in sorted(by_cur, key=lambda c: (c != "RUB", c)):
        lines.append(f"На счетах {c}: <b>{num(by_cur[c])} {c}</b>  {_dlt(by_cur[c], by_cur0.get(c, 0), c)}")
    lines.append(f"Депозиты: <b>{rub(dep)}</b>  {_dlt(dep, dep0)}")
    if wb:
        lines.append(f"Баланс WB: <b>{rub(wb_bal)}</b>  {_dlt(wb_bal, wb_bal0)}")
        if wb[7]:
            lines.append(f"В пути от WB: <b>{rub(wb[7])}</b>")
    acc = sorted(((n, c, s, v, beg.get((n, c), (None, 0.0))[1]) for (n, c), (s, v) in end.items()
                  if s == "Действующий" or abs(v) >= 0.5), key=lambda x: (x[1] != "RUB", -abs(x[3])))
    if acc:
        lines += ["", "<b>По счетам</b>"] + [
            f"• {esc(n)} — <b>{num(v)} {c}</b>" + (f" ({'+' if v - v0 > 0 else '−'}{num(abs(v - v0))})"
                                                   if abs(v - v0) >= 1 else "")
            for n, c, s, v, v0 in acc[:15]]
        if len(acc) > 15:
            lines.append(f"…ещё {len(acc) - 15} — в Excel.")
    lines += ["", "<i>Всего в рублях = рублёвые счета + депозиты + баланс WB. Как лист «Остатки ДС» "
                  "мэн пака.</i>"]
    files = (("acc", "Excel: остатки по счетам"),)
    photo = None
    if ndays(a, b) > 1 and ndays(a, b) <= 62:
        days, ins, outs = _daily(_cf(a, b), a, b)
        photo = _chart(lambda: chart_flow(days, ins, outs, f"Всего в рублях — {rub(total)}",
                                          f"движение по счетам, млн ₽ · {span(a, b)}"))
    return {"text": "\n".join(lines), "photo": photo, "auto": "acc", "files": files,
            "kb": _files_kb("b", a, b, files)}


def _dlt(v, v0, unit="₽"):
    d = v - v0
    if abs(d) < 1:
        return ""
    return ("▲ +" if d > 0 else "▼ −") + num(abs(d)) + f" {unit}"


def file_balances(a: date, b: date):
    end, dep, wb, _ = _balances(b)
    beg, dep0, wb0, _ = _balances(a - timedelta(days=1))
    cols = ["Счёт", "Валюта", "Статус", f"На {a - timedelta(days=1):%d.%m.%Y}", f"На {b:%d.%m.%Y}",
            "Изменение"]
    rows = []
    for (n, c), (s, v) in sorted(end.items(), key=lambda x: (x[0][1] != "RUB", -abs(x[1][1]))):
        v0 = beg.get((n, c), (None, 0.0))[1]
        rows.append([n, c, s, v0, v, v - v0])
    rows.append(["Бессрочные депозиты", "RUB", "", dep0, dep, dep - dep0])
    if wb:
        rows.append(["Баланс WB", "RUB", "", float(wb0[6] or 0) if wb0 else 0, float(wb[6] or 0),
                     float(wb[6] or 0) - (float(wb0[6] or 0) if wb0 else 0)])
    data = _book("Остатки денежных средств", f"{span(a, b)} · как лист «Остатки ДС» мэн пака",
                 [("Счета", cols, rows)])
    return f"Остатки ДС {b:%d.%m.%Y}.xlsx", data, XLSX


# ---------------------------------------------------------------- 📋 движение денег
def _cf(a, b) -> pd.DataFrame:
    from .cashflow import _get
    return _get(a, b, masked=False)


def report_flow(a: date, b: date) -> dict | None:
    df = _cf(a, b)
    if df is None or df.empty:
        return None
    pa, pb = M.prev_range(a, b)
    old = _cf(pa, pb)
    inn, out = df[df.amount > 0].amount.sum(), df[df.amount < 0].amount.sum()
    oin = old[old.amount > 0].amount.sum() if not old.empty else 0
    oout = old[old.amount < 0].amount.sum() if not old.empty else 0
    lines = [f"<b>📋 Движение денег · {span(a, b)}</b>",
             f"<i>сравнение с {span(pa, pb)} · по выписке банка (ДДС)</i>", "",
             f"Поступления: <b>{rub(inn)}</b>  {chg(inn, oin)}",
             f"Выплаты: <b>{rub(-out)}</b>  {chg(-out, -oout)}",
             f"Чистый поток: <b>{('+' if inn + out >= 0 else '−') + rub(abs(inn + out))}</b>",
             f"Операций: <b>{num(len(df))}</b>"]
    act = df.groupby("activity").amount.sum().sort_values()
    if len(act) > 1:
        lines += ["", "<b>По видам деятельности</b>"] + [
            f"• {esc(k or 'Без вида')} — {('+' if v >= 0 else '−') + rub(abs(v))}" for k, v in act.items()]
    o = df[df.amount < 0].groupby("subitem").amount.sum().sort_values().head(7)
    if len(o):
        lines += ["", "<b>Крупнейшие выплаты</b>"] + [f"• {esc(k or 'Без статьи')} — {rub(-v)}"
                                                      for k, v in o.items()]
    i = df[df.amount > 0].groupby("subitem").amount.sum().sort_values(ascending=False).head(5)
    if len(i):
        lines += ["", "<b>Крупнейшие поступления</b>"] + [f"• {esc(k or 'Без статьи')} — {rub(v)}"
                                                          for k, v in i.items()]
    cps = df[df.amount < 0].groupby("cp").amount.sum().sort_values().head(5)
    if len(cps):
        lines += ["", "<b>Кому заплатили больше всего</b>"] + [f"• {esc(k)} — {rub(-v)}"
                                                               for k, v in cps.items()]
    lines += ["", "<i>Все операции — в Excel.</i>"]
    files = (("ops", "Excel: операции"), ("items", "Excel: по статьям"))
    photo = None
    if 1 < ndays(a, b) <= 62:
        days, ins_, outs_ = _daily(df, a, b)
        photo = _chart(lambda: chart_flow(days, ins_, outs_,
                                          f"Чистый поток — {('+' if inn + out >= 0 else '−') + rub(abs(inn + out))}",
                                          f"млн ₽ по дням · {span(a, b)}"))
    return {"text": "\n".join(lines), "photo": photo, "auto": "ops", "files": files,
            "kb": _files_kb("f", a, b, files)}


def _ops_rows(df):
    df = df.sort_values(["d", "amount"])
    return (["Дата", "Вид деятельности", "Статья", "Подстатья", "Контрагент", "Договор", "Сумма, ₽"],
            [[r.d, r.activity, r.item, r.subitem, r.cp, r.contract, r.amount] for r in df.itertuples()])


def file_flow(code, a, b):
    df = _cf(a, b)
    if df is None or df.empty:
        return None
    if code == "items":
        g = (df.groupby(["activity", "item", "subitem"])
               .agg(n=("amount", "size"), total=("amount", "sum")).reset_index()
               .sort_values("total"))
        cols = ["Вид деятельности", "Статья", "Подстатья", "Операций, шт", "Сумма, ₽"]
        rows = [[r.activity, r.item, r.subitem, r.n, r.total] for r in g.itertuples()]
        data = _book("Движение денег", span(a, b), [("По статьям", cols, rows)])
        return f"Движение денег по статьям {span(a, b)}.xlsx", data, XLSX
    cols, rows = _ops_rows(df)
    data = _book("Движение денег", span(a, b), [("Операции", cols, rows)])
    return f"Движение денег {span(a, b)}.xlsx", data, XLSX


# ---------------------------------------------------------------- 💸 оплаты контрагента
def _named(df):
    return df[df["cp"] != "Без контрагента"]


def cp_search(text: str, hi: date) -> list[str]:
    q = (text or "").strip().lower()
    if len(q) < 2:
        return []
    df = _named(_cf(hi - timedelta(days=730), hi))
    names = df.groupby("cp").amount.apply(lambda s: s.abs().sum()).sort_values(ascending=False)
    return [n for n in names.index if q in n.lower()][:8]


def report_cp(a: date, b: date, cp: str) -> dict | None:
    df = _cf(a, b)
    part = df[df["cp"] == cp] if df is not None and not df.empty else df
    lines = [f"<b>💸 {esc(cp)}</b>", f"<i>{span(a, b)} · по выписке банка</i>", ""]
    if part is None or part.empty:
        lines.append("За этот период операций нет. Выберите другой период:")
        return {"text": "\n".join(lines), "photo": None, "auto": None, "files": (),
                "kb": _retag({"inline_keyboard": period_kb("p")["inline_keyboard"]})}
    paid, got = -part[part.amount < 0].amount.sum(), part[part.amount > 0].amount.sum()
    if paid:
        lines.append(f"Заплатили: <b>{rub(paid)}</b>")
    if got:
        lines.append(f"Получили: <b>{rub(got)}</b>")
    lines.append(f"Операций: <b>{num(len(part))}</b> · последняя {part.d.max():%d.%m.%Y}")
    it = part.groupby("subitem").amount.sum().sort_values()
    lines += ["", "<b>По статьям</b>"] + [f"• {esc(k or 'Без статьи')} — {('+' if v >= 0 else '−') + rub(abs(v))}"
                                          for k, v in it.items()]
    ct = part.groupby("contract").amount.sum().sort_values()
    if len(ct) > 1:
        lines += ["", "<b>По договорам</b>"] + [f"• {esc(k)} — {('+' if v >= 0 else '−') + rub(abs(v))}"
                                                for k, v in ct.head(6).items()]
    last = part.sort_values("d", ascending=False).head(8)
    lines += ["", "<b>Последние операции</b>"] + [
        f"• {r.d:%d.%m.%Y} — {('+' if r.amount >= 0 else '−') + rub(abs(r.amount))} · {esc(r.subitem or r.item)}"
        for r in last.itertuples()]
    files = (("cp", "Excel: все операции"),)
    return {"text": "\n".join(lines), "photo": None, "auto": None, "files": files,
            "kb": _files_kb("p", a, b, files)}


def file_cp(a, b, cp):
    df = _cf(a, b)
    part = df[df["cp"] == cp] if df is not None and not df.empty else df
    if part is None or part.empty:
        return None
    cols, rows = _ops_rows(part)
    data = _book(cp[:60], span(a, b), [("Операции", cols, rows)])
    safe = re.sub(r"[^\w\s-]", "", cp)[:40]
    return f"Оплаты {safe} {span(a, b)}.xlsx", data, XLSX


# ---------------------------------------------------------------- 🛡 проверка контрагента
def report_check(text: str) -> dict:
    from .counterparties import counterparty_info
    raw = counterparty_info(text)
    out = []
    for ln in raw.split("\n"):
        if ln.startswith("КОНТРАГЕНТ:"):
            parts = [p.strip() for p in ln.split(" | ")]
            name = parts[0].split(":", 1)[1].strip()
            out += ["", f"<b>🛡 {esc(name)}</b>"]
            for p in parts[1:]:
                k, _, v = p.partition(":")
                if k.strip() == "риски":
                    v = v.strip()
                    out.append(("⚠️ " if v and v.lower() not in ("нет", "не выявлены", "—") else "✅ ")
                               + f"Риски: <b>{esc(v or 'не выявлены')}</b>")
                else:
                    out.append(f"{esc(k.strip().capitalize())}: <b>{esc(v.strip())}</b>")
        elif ln.strip().startswith("- "):
            if not out or "Договоры" not in out[-1] and not out[-1].startswith("•"):
                out.append("<b>Договоры</b>")
            out.append("• " + esc(ln.strip()[2:]))
        elif ln.strip() == "договоров нет":
            out.append("Договоров нет.")
        elif ln.strip():
            out.append(esc(ln.strip()))
    text_out = "\n".join(out).strip() or esc(raw)
    return {"text": text_out + "\n\n<i>По справочнику контрагентов и договорам компании.</i>",
            "photo": None, "auto": None, "files": (), "kb": {"inline_keyboard": [
                [{"text": "🔁 Проверить другого", "callback_data": "fm:o:k"}]]}}


# ---------------------------------------------------------------- 🔍 поиск платежей
_AMOUNT = re.compile(r"^\s*[\d\s ]+([.,]\d{1,2})?\s*$")


def search_payments(text: str, hi: date):
    a = hi - timedelta(days=364)
    df = _cf(a, hi)
    if df is None or df.empty:
        return None, a
    q = (text or "").strip()
    if _AMOUNT.match(q):
        v = float(q.replace(" ", "").replace(" ", "").replace(",", "."))
        hit = df[(df.amount.abs() - v).abs() < 0.51]
    else:
        ql = q.lower()
        mask = pd.Series(False, index=df.index)
        for c in ("cp", "contract", "item", "subitem"):
            mask |= df[c].str.lower().str.contains(ql, regex=False)
        hit = df[mask]
    return hit.sort_values("d", ascending=False), a


def report_search(text: str) -> dict:
    hi = loaded()
    hit, a = search_payments(text, hi)
    lines = [f"<b>🔍 «{esc(text)}»</b>", f"<i>{span(a, hi)} · по выписке банка</i>", ""]
    if hit is None or hit.empty:
        lines.append("Ничего не нашлось. Попробуйте другое слово или сумму.")
        return {"text": "\n".join(lines), "photo": None, "auto": None, "files": (),
                "kb": {"inline_keyboard": [[{"text": "🔁 Искать ещё", "callback_data": "fm:o:s"}]]}}
    paid, got = -hit[hit.amount < 0].amount.sum(), hit[hit.amount > 0].amount.sum()
    lines.append(f"Найдено операций: <b>{num(len(hit))}</b>")
    if paid:
        lines.append(f"Выплаты: <b>{rub(paid)}</b>")
    if got:
        lines.append(f"Поступления: <b>{rub(got)}</b>")
    lines += ["", "<b>Последние</b>"] + [
        f"• {r.d:%d.%m.%Y} — {('+' if r.amount >= 0 else '−') + rub(abs(r.amount))} · {esc(r.cp)}"
        f" · {esc(r.subitem or r.item)}" for r in hit.head(12).itertuples()]
    if len(hit) > 12:
        lines.append(f"…ещё {len(hit) - 12} — в Excel.")
    _LAST_SEARCH["q"] = text
    return {"text": "\n".join(lines), "photo": None, "auto": None,
            "files": (("found", "Excel: найденные операции"),),
            "kb": {"inline_keyboard": [[{"text": "⬇️ Excel: найденные операции",
                                         "callback_data": f"fm:f:s:found:{ymd(a)}:{ymd(hi)}"}],
                                       [{"text": "🔁 Искать ещё", "callback_data": "fm:o:s"}]]}}


_LAST_SEARCH: dict = {}


def file_search(a, b, q):
    hit, _ = search_payments(q or _LAST_SEARCH.get("q", ""), b)
    if hit is None or hit.empty:
        return None
    cols, rows = _ops_rows(hit)
    data = _book("Поиск платежей", f"«{q}» · {span(a, b)}", [("Найдено", cols, rows)])
    return f"Поиск платежей {span(a, b)}.xlsx", data, XLSX


# ---------------------------------------------------------------- 📊 месяц к месяцу / 🎯 ТБУ
PL_LINES = [("rev", "Выручка без НДС"), ("cogs", "Себестоимость"), ("comm", "Комиссия WB"),
            ("sell", "Расходы на реализацию"), ("promo", "Продвижение WB"), ("md", "Маржинальный доход"),
            ("kmd", "КМД, %"), ("other", "Прочие доходы и расходы"), ("ovh", "Накладные"),
            ("corp", "Корпоративные"), ("fin", "Финансовые"), ("ebt", "Результат до налога"),
            ("tax", "Налог на прибыль"), ("net", "Чистая прибыль")]


def _margin_off() -> bool:
    try:
        from .tools import MARGIN_OFF
        return bool(MARGIN_OFF)
    except Exception:
        return True


def _pl():
    from .pl import get_pl
    return get_pl()


def _month_of(b: date, months):
    me = (b.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return me if me in months else None


def report_mom(a: date, b: date) -> dict | None:
    data = _pl()
    months = data["months"]
    me = _month_of(b, months)
    if not me or months.index(me) == 0:
        return None
    pm = months[months.index(me) - 1]
    cur, old = data["derived"][me], data["derived"][pm]
    rd = data["report_date"]
    partial = me > rd
    lines = [f"<b>📊 P&amp;L · {M.MONTHS[me.month - 1].lower()} {me.year}</b>",
             f"<i>сравнение с прошлым месяцем ({pm:%m.%Y})</i>",
             f"<i>по данным мэн пака на {rd:%d.%m.%Y}"
             + (" · месяц ещё не закрыт" if partial else "") + "</i>", ""]
    for k, lbl in PL_LINES:
        if _margin_off() and k in ("md", "kmd"):
            continue
        v, v0 = cur.get(k), old.get(k)
        if v is None:
            continue
        if k == "kmd":
            lines.append(f"{lbl}: <b>{num(v, 1)}%</b>  {chg(v, v0, pp=True)}")
        else:
            d = (v or 0) - (v0 or 0)
            lines.append(f"{lbl}: <b>{('−' if v < 0 else '') + rub(abs(v))}</b>"
                         + (f"  {'▲' if d > 0 else '▼'} {('+' if d > 0 else '−') + rub(abs(d))}" if abs(d) >= 1 else ""))
    try:
        from ...manpack import data as md
        s = md.month_summary(me)
        if s.get("headline"):
            lines += ["", "<b>Главное</b>", esc(s["headline"])]
    except Exception as e:
        print(f"[fin_menu] выводы: {type(e).__name__}: {e}", flush=True)
    lines += ["", "<i>Расходы — со знаком минус, ▲▼ — изменение в рублях к прошлому месяцу. "
                  "Как лист P&amp;L мэн пака.</i>"]
    files = (("pl", "Excel: P&L за 12 месяцев"),)
    ms = [m for m in months if m <= me][-6:]
    photo = _chart(lambda: chart_months(
        [f"{M.MONTHS[m.month - 1][:3].lower()}" for m in ms],
        [data["derived"][m].get("rev") or 0 for m in ms],
        [data["derived"][m].get("net") for m in ms], "выручка без НДС", "чистая прибыль",
        "Выручка и чистая прибыль, млн ₽", f"последние {len(ms)} мес. · мэн пак"))
    return {"text": "\n".join(lines), "photo": photo, "auto": "pl", "files": files,
            "kb": _files_kb("c", a, b, files)}


def file_pl(a, b):
    data = _pl()
    months = data["months"][-12:]
    keys = [(k, l) for k, l in PL_LINES if not (_margin_off() and k in ("md", "kmd"))]
    keys += [("tbu", "ТБУ"), ("zfp_pct", "Запас прочности, %")]
    cols = ["Показатель"] + [f"{m:%m.%Y}" for m in months]
    rows = [[l] + [data["derived"][m].get(k) for m in months] for k, l in keys]
    out = _book("P&L по месяцам", f"данные мэн пака на {data['report_date']:%d.%m.%Y}",
                [("P&L", cols, rows)], notes=[("Источник", "Те же расчёты, что лист P&L мэн пака."),
                                               ("Знаки", "Расходы со знаком минус.")])
    return "P&L по месяцам.xlsx", out, XLSX


def report_tbu(a: date, b: date) -> dict | None:
    data = _pl()
    months = data["months"]
    rd = data["report_date"]
    closed = [m for m in months if m <= rd]
    if not closed:
        return None
    me = _month_of(b, months) or closed[-1]
    show = [m for m in closed if m <= me][-3:] or closed[-3:]
    lines = [f"<b>🎯 Точка безубыточности</b>", f"<i>по данным мэн пака на {rd:%d.%m.%Y}</i>", ""]
    for m in show:
        d = data["derived"][m]
        if d.get("tbu") is None:
            lines.append(f"{M.MONTHS[m.month - 1]}: ТБУ не определена (маржинальность ≤ 0)")
            continue
        zp = d.get("zfp_pct")
        lines.append(f"{M.MONTHS[m.month - 1]} {m.year}: ТБУ <b>{rub(d['tbu'])}</b> · выручка {rub(d['rev'])}"
                     + (f" · запас прочности <b>{num(zp, 1)}%</b>" if zp is not None else ""))
    last = data["derived"][show[-1]]
    if last.get("tbu"):
        diff = last["rev"] - last["tbu"]
        lines += ["", ("✅ Выручка выше точки безубыточности на " if diff >= 0 else
                       "⚠️ До безубыточности не хватает ") + f"<b>{rub(abs(diff))}</b> в месяц."]
        lines.append(f"Постоянные затраты месяца: {rub(abs(last.get('fc') or 0))}.")
    cur_m = _month_of(rd, months)
    if cur_m and cur_m > show[-1]:
        fact = data["derived"][cur_m].get("rev") or 0
        if last.get("tbu"):
            lines += ["", f"<b>Текущий месяц на {rd:%d.%m}</b>",
                      f"Выручка: {rub(fact)} — это {num(fact / last['tbu'] * 100, 0)}% от ТБУ прошлого месяца."]
    lines += ["", "<i>ТБУ = постоянные затраты / доля маржинального дохода. Учитывает всю финансовую "
                  "нагрузку, включая проценты по займам.</i>"]
    files = (("pl", "Excel: P&L и ТБУ за 12 месяцев"),)
    ms = [m for m in closed if m <= me][-6:]
    photo = _chart(lambda: chart_months(
        [f"{M.MONTHS[m.month - 1][:3].lower()}" for m in ms],
        [data["derived"][m].get("rev") or 0 for m in ms],
        [data["derived"][m].get("tbu") for m in ms], "выручка без НДС", "точка безубыточности",
        "Выручка против ТБУ, млн ₽", "выше линии — прибыль, ниже — убыток", dashed=True))
    return {"text": "\n".join(lines), "photo": photo, "auto": None, "files": files,
            "kb": _files_kb("t", a, b, files)}


# ---------------------------------------------------------------- 📥 WB, 🏦 займы, 💱 курсы
def report_tool(rep: str, a: date, b: date) -> dict | None:
    from . import finance_extra as fx
    from .wb_payouts import wb_payouts_report
    if rep == "w":
        raw, icon = wb_payouts_report(a.isoformat(), b.isoformat(), details=True), "📥"
    elif rep == "l":
        raw, icon = fx.loans_report(b.isoformat()), "🏦"
    else:
        raw, icon = fx.fx_report(b.isoformat()), "💱"
    text, sheets = tsv_card(raw, icon)
    _TOOL_CACHE[(rep, a, b)] = sheets
    files = (("xl", "Excel"),) if sheets else ()
    return {"text": text, "photo": None, "auto": None, "files": files,
            "kb": _files_kb(rep, a, b, files)}


_TOOL_CACHE: dict = {}


def file_tool(rep, a, b):
    sheets = _TOOL_CACHE.get((rep, a, b))
    if sheets is None:
        report_tool(rep, a, b)
        sheets = _TOOL_CACHE.get((rep, a, b))
    data = _tsv_book(REPORTS[rep][2:], span(a, b), sheets or [])
    return (f"{REPORTS[rep][2:]} {span(a, b)}.xlsx", data, XLSX) if data else None


# ---------------------------------------------------------------- 🚚 приходы (УПД)
def _upd(b: date):
    from ...manpack import data as md
    from ...manpack.tabs import upd
    me = md.month_end(b)
    docs, brands, tot = upd.tables(me)
    return me, docs, brands, tot


def report_upd(a: date, b: date) -> dict | None:
    me, docs, brands, tot = _upd(b)
    title = f"{M.MONTHS[me.month - 1].lower()} {me.year}"
    if not tot:
        return {"text": f"<b>🚚 Приходы (УПД) · {title}</b>\n\nЗа этот месяц приходов нет.",
                "photo": None, "auto": None, "files": (), "kb": _retag(period_kb("u"))}
    files_n = _files_count(list(docs["doc_id"]))
    diff = tot["man"] - tot["buh"]
    lines = [f"<b>🚚 Приходы (УПД) · {title}</b>", "<i>суммы без НДС</i>", "",
             f"Документов: <b>{num(tot['docs'])}</b> · товара <b>{num(tot['qty'])} шт</b>",
             f"Стоимость по УПД (бух.): <b>{rub(tot['buh'])}</b>",
             f"Управленческая себестоимость: <b>{rub(tot['man'])}</b>",
             f"Разница упр. − бух.: <b>{('+' if diff >= 0 else '−') + rub(abs(diff))}</b>"]
    if tot.get("no_man"):
        lines.append(f"⚠️ Строк без управленческой себестоимости: {num(tot['no_man'])}")
    lines += ["", "<b>Документы</b>"] + [
        f"• {r.d:%d.%m} — №{esc(r.number)} · {esc(r.cp)} · {num(r.qty)} шт · {rub(r.buh)}"
        + (f" · 📎{files_n[r.doc_id]}" if files_n.get(r.doc_id) else "")
        for r in docs.head(15).itertuples()]
    if len(docs) > 15:
        lines.append(f"…ещё {len(docs) - 15} — в Excel.")
    if len(brands):
        lines += ["", "<b>По брендам</b>"] + [f"• {esc(r.brand)} — {num(r.qty)} шт · {rub(r.buh)}"
                                              for r in brands.head(6).itertuples()]
    with_files = [r for r in docs.itertuples() if files_n.get(r.doc_id)][:10]
    if with_files:
        lines += ["", "📎 Файлы документов — кнопками ниже, пришлю в чат."]
    kb = _files_kb("u", a, b, (("xl", "Excel: приходы"),))
    kb["inline_keyboard"] = [[{"text": f"📎 №{r.number} · {str(r.cp)[:22]}",
                               "callback_data": f"fm:u:u:{r.doc_id}"}] for r in with_files] \
        + kb["inline_keyboard"]
    return {"text": "\n".join(lines), "photo": None, "auto": None,
            "files": (("xl", "Excel: приходы"),), "kb": kb}


def _files_count(ids) -> dict:
    try:
        from django.db.models import Count
        from cards.models import UpdDocumentFile
        return dict(UpdDocumentFile.objects.filter(upd_document_id__in=ids)
                    .values_list("upd_document_id").annotate(n=Count("id")))
    except Exception as e:
        print(f"[fin_menu] файлы УПД: {type(e).__name__}: {e}", flush=True)
        return {}


def upd_files(doc_id: int) -> list[tuple[str, bytes, str]]:
    """Файлы, прикреплённые к УПД в админке: (имя, байты, mime)."""
    import mimetypes
    import os
    from cards.models import UpdDocumentFile
    out = []
    for f in UpdDocumentFile.objects.filter(upd_document_id=doc_id).order_by("uploaded_at"):
        try:
            with f.file.open("rb") as fh:
                data = fh.read()
        except Exception as e:
            print(f"[fin_menu] файл УПД {f.pk}: {type(e).__name__}: {e}", flush=True)
            continue
        name = f.name or os.path.basename(f.file.name)
        if "." not in name:
            name += os.path.splitext(f.file.name)[1]
        out.append((name, data, mimetypes.guess_type(name)[0] or "application/octet-stream"))
    return out


def file_upd(a, b):
    me, docs, brands, tot = _upd(b)
    if not tot:
        return None
    d_cols = ["Дата", "УПД", "Поставщик", "Договор", "Кол-во, шт", "Бух. стоимость, ₽",
              "Упр. стоимость, ₽", "Разница, ₽"]
    d_rows = [[r.d, r.number, r.cp, r.contract or "", r.qty, r.buh, r.man, r.diff] for r in docs.itertuples()]
    b_cols = ["Бренд", "Кол-во, шт", "Бух. стоимость, ₽", "Упр. стоимость, ₽", "Разница, ₽"]
    b_rows = [[r.brand, r.qty, r.buh, r.man, r.diff] for r in brands.itertuples()]
    data = _book("Приходы (УПД)", f"{me:%m.%Y} · без НДС", [("Документы", d_cols, d_rows),
                                                             ("Бренды", b_cols, b_rows)])
    return f"Приходы УПД {me:%m.%Y}.xlsx", data, XLSX


# ---------------------------------------------------------------- 📦 мэн пак
def report_mp(a: date, b: date) -> dict:
    me = (b.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    on = min(me, loaded())
    lines = [f"<b>📦 Мэн пак на {on:%d.%m.%Y}</b>", "",
             "Собираю файл: P&amp;L, Cash Flow, остатки ДС, юнит-экономика, ТБУ, расшифровки. "
             "Это занимает до пары минут — файл придёт следом."]
    return {"text": "\n".join(lines), "photo": None, "auto": "xl", "files": (("xl", "Excel: мэн пак"),),
            "kb": {"inline_keyboard": [[{"text": "🔁 Другой месяц", "callback_data": "fm:o:mp"}]]}}


def file_mp(a, b):
    from gear.management.commands import mp
    import tempfile
    from pathlib import Path
    me = (b.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    on = min(me, loaded())
    out = Path(tempfile.gettempdir()) / f"manpack_bot_{on:%Y%m%d}.xlsx"
    path, _ = mp.build_management_pack(on, out_path=str(out))
    return f"Мэн пак {on:%d.%m.%Y}.xlsx", Path(path).read_bytes(), XLSX


# ---------------------------------------------------------------- диспетчер
def build(rep: str, a: date, b: date, arg: str | None = None) -> dict | None:
    if rep == "b":
        return report_balances(a, b)
    if rep == "f":
        return report_flow(a, b)
    if rep == "p" and arg:
        return report_cp(a, b, arg)
    if rep == "c":
        return report_mom(a, b)
    if rep == "t":
        return report_tbu(a, b)
    if rep in ("w", "l", "x"):
        return report_tool(rep, a, b)
    if rep == "mp":
        return report_mp(a, b)
    if rep == "u":
        return report_upd(a, b)
    return None


def file(rep: str, code: str, a: date, b: date, arg: str | None = None):
    if rep == "b":
        return file_balances(a, b)
    if rep == "f":
        return file_flow(code, a, b)
    if rep == "p" and arg:
        return file_cp(a, b, arg)
    if rep == "s":
        return file_search(a, b, arg)
    if rep in ("c", "t"):
        return file_pl(a, b)
    if rep in ("w", "l", "x"):
        return file_tool(rep, a, b)
    if rep == "mp":
        return file_mp(a, b)
    if rep == "u":
        return file_upd(a, b)
    return None


def query(rep: str, text: str, hi: date):
    """Текстовый запрос: результат отчёта или список вариантов [(подпись, значение)]."""
    if rep == "k":
        return report_check(text)
    if rep == "s":
        return report_search(text)
    if rep == "p":
        return cp_search(text, hi)
    return None
