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
SINGLE_DAY: set = set()
DATA_START = date(2024, 1, 1)

PRESETS = {
    "b": (("y", "На вчера"), ("7", "За 7 дней"), ("m", "С начала месяца"),
          ("pm", "Прошлый месяц"), ("30", "30 дней"), ("90", "90 дней")),
    "f": (("y", "Вчера"), ("7", "7 дней"), ("w", "Прошлая неделя"), ("m", "Этот месяц"),
          ("pm", "Прошлый месяц"), ("30", "30 дней")),
    "p": (("m", "Этот месяц"), ("pm", "Прошлый месяц"), ("90", "90 дней"),
          ("ytd", "С начала года"), ("12", "12 месяцев"), ("24", "2 года")),
    "c": (("pm", "Прошлый месяц"), ("m", "Этот месяц")),
    "t": (("pm", "Прошлый месяц"), ("m", "Этот месяц")),
    "w": (("7", "7 дней"), ("30", "30 дней"), ("90", "90 дней"),
          ("m", "Этот месяц"), ("pm", "Прошлый месяц"), ("ytd", "С начала года")),
    "l": (("y", "На сегодня"), ("pm", "На конец прошлого месяца")),
    "x": (("30", "30 дней"), ("q", "3 месяца"), ("ytd", "С начала года"), ("12", "12 месяцев")),
    "mp": (("pm", "Прошлый месяц"), ("m", "Текущий месяц")),
    "u": (("m", "Этот месяц"), ("pm", "Прошлый месяц")),
}
MONTHLY = {"c", "t", "mp", "u"}          # отчёт за месяц: берём месяц конечной даты
ONE_DATE = {"l"}                         # отчёт на дату
AI = False                               # ИИ в финботе выключен: только отчёты по кнопкам

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
        "• Можно просто написать название, ИНН или сумму — предложу, где искать.\n\n"
        "Важные цифры сверяйте с мэн паком. Если что-то не так — напишите Дарье.")


def keyboard() -> dict:
    r = REPORTS
    return {"keyboard": [[{"text": r["b"]}, {"text": r["f"]}],
                         [{"text": r["p"]}, {"text": r["k"]}],
                         [{"text": r["s"]}, {"text": r["c"]}],
                         [{"text": r["t"]}, {"text": r["w"]}],
                         [{"text": r["l"]}, {"text": r["x"]}],
                         [{"text": r["u"]}, {"text": r["mp"]}],
                         [{"text": BTN_AI}, {"text": BTN_HELP}] if AI else [{"text": BTN_HELP}]],
            "resize_keyboard": True, "is_persistent": True,
            "input_field_placeholder": "Кнопка, название, ИНН или сумма…"}


def text_kb(text: str) -> tuple[str, dict]:
    """Свободный текст без ИИ: предлагаем, где искать."""
    t = esc(text[:60])
    return (f"Где искать «{t}»?", {"inline_keyboard": [
        [{"text": "🔍 В платежах за год", "callback_data": "fm:t:s"}],
        [{"text": "🛡 Проверить контрагента", "callback_data": "fm:t:k"}],
        [{"text": "💸 Оплаты контрагента за период", "callback_data": "fm:t:p"}]]})


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
    if code in ("90", "24"):
        return hi - timedelta(days=89 if code == "90" else 729), hi
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
    if rep in SINGLE_DAY or rep in ONE_DATE:
        return f"<b>{REPORTS[rep]}</b>\nНа какую дату? Нажмите кнопку или напишите дату: <code>15.10</code>"
    return (f"<b>{REPORTS[rep]}</b>\nЗа какой период? Нажмите кнопку или напишите даты: "
            "<code>01.10–15.10</code>, <code>05.10</code>")


def period_kb(rep: str) -> dict:
    btn = [{"text": t, "callback_data": f"fm:p:{rep}:{c}"} for c, t in PRESETS.get(rep, ())]
    rows = [btn[i:i + 3] for i in range(0, len(btn), 3)]
    if rep in MONTHLY:                       # выбор месяца, а не дат
        rows.append([{"text": "🗓 Другой месяц", "callback_data": f"fm:y:{rep}:{loaded().year}"}])
    else:
        rows.append([{"text": "📅 " + ("Другая дата" if rep in ONE_DATE else "Свой период"),
                      "callback_data": f"fm:c:{rep}::0"}])
    return {"inline_keyboard": rows}


def month_kb(rep: str, year: int, lo: date, hi: date) -> dict:
    """Сетка месяцев года: нажатие сразу открывает отчёт за месяц."""
    btn = []
    for m in range(1, 13):
        first = date(year, m, 1)
        last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        if last < lo or first > hi:
            btn.append({"text": "·", "callback_data": "fm:n:" + rep})
            continue
        btn.append({"text": M.MONTHS[m - 1][:3] + (" ✓" if first <= hi <= last else ""),
                    "callback_data": f"fm:e:{rep}:{ymd(first)}:{ymd(min(last, hi))}"})
    nav = [{"text": f"‹ {year - 1}" if year - 1 >= lo.year else "·",
            "callback_data": f"fm:y:{rep}:{year - 1}" if year - 1 >= lo.year else "fm:n:" + rep},
           {"text": str(year), "callback_data": "fm:n:" + rep},
           {"text": f"{year + 1} ›" if year + 1 <= hi.year else "·",
            "callback_data": f"fm:y:{rep}:{year + 1}" if year + 1 <= hi.year else "fm:n:" + rep}]
    return {"inline_keyboard": [nav] + [btn[i:i + 3] for i in range(0, 12, 3)]}


def calendar_kb(rep, year, month, start, lo, hi):
    single = rep in SINGLE_DAY or rep in MONTHLY or rep in ONE_DATE
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


def chart_months(labels, bars, line, bar_name, line_name, title, sub, dashed=False,
                 line2=None, line2_name=None) -> bytes:
    """Столбики по месяцам (млн ₽) и одна-две линии: прибыль или ТБУ."""
    from . import digest_charts as ch
    plt = ch._plt()
    n = len(labels)
    fig, ax = plt.subplots(figsize=(10.8, 7.6), dpi=100)
    xs = range(n)
    ax.bar(xs, [v / 1e6 for v in bars], width=0.62, color=[ch.PALE] * (n - 1) + [ch.GREEN], label=bar_name)
    for vals, name, color, style, va in ((line, line_name, ch.WARM, (0, (5, 4)) if dashed else "-", "bottom"),
                                         (line2, line2_name, ch.MID, (0, (2, 3)), "top")):
        pts = [(x, v / 1e6) for x, v in zip(xs, vals or ()) if v is not None]
        if not pts:
            continue
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=2.5, marker="o", ms=6,
                ls=style, label=name)
        for x, v in pts:
            ax.text(x, v, f" {v:.1f}".replace(".", ","), color=color, fontsize=11.5, va=va,
                    ha="center", fontweight="bold")
    for x, v in zip(xs, bars):
        ax.text(x, v / 1e6 * 0.5 if v > 0 else 0, f"{v / 1e6:.1f}".replace(".", ","), ha="center",
                color=ch.INK if x == n - 1 else ch.MUTED, fontsize=11.5)
    ax.axhline(0, color=ch.AXIS, lw=1)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, color=ch.MUTED, fontsize=12)
    ax.yaxis.set_visible(False)
    ax.legend(frameon=False, fontsize=12, loc="lower right", bbox_to_anchor=(1.0, 1.0),
              ncol=3 if line2 else 2)
    ch._clean(ax)
    ch._head(fig, title, sub)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.8, bottom=0.1)
    return ch._png(plt, fig)


def chart_bars(labels, vals, title, sub, color=None) -> bytes:
    """Простые столбики (млн ₽) с подписями."""
    from . import digest_charts as ch
    plt = ch._plt()
    n = len(labels)
    fig, ax = plt.subplots(figsize=(10.8, 7.6), dpi=100)
    xs = range(n)
    k, u = (1e6, "млн") if max([abs(v) for v in vals] or [0]) >= 1e6 else (1e3, "тыс.")
    sub = sub.replace("млн ₽", f"{u} ₽")
    ys = [v / k for v in vals]
    ax.bar(xs, ys, width=0.62 if n < 20 else 0.8, color=color or ch.GREEN)
    if n <= 16:
        for x, v in zip(xs, ys):
            if v:
                ax.text(x, v, f"{v:.1f}".replace(".", ",") if k == 1e6 else f"{v:,.0f}".replace(",", " "),
                        ha="center", va="bottom", color=ch.INK, fontsize=11.5)
    step = 1 if n <= 13 else 3 if n <= 31 else 7
    ax.set_xticks(list(xs))
    ax.set_xticklabels([t if (n - 1 - i) % step == 0 else "" for i, t in enumerate(labels)],
                       color=ch.MUTED, fontsize=12)
    ax.yaxis.set_visible(False)
    ch._clean(ax)
    ch._head(fig, title, sub)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.82, bottom=0.1)
    return ch._png(plt, fig)


def chart_hbar(names, vals, title, sub) -> bytes:
    """Горизонтальные столбики (млн ₽): кто сколько."""
    from . import digest_charts as ch
    plt = ch._plt()
    n = len(names)
    fig, ax = plt.subplots(figsize=(10.8, max(5.0, 1.6 + 0.75 * n)), dpi=100)
    ys = list(range(n))[::-1]
    v = [x / 1e6 for x in vals]
    ax.barh(ys, v, height=0.62, color=[ch.GREEN] + [ch.MID] * (n - 1))
    for y, x in zip(ys, v):
        ax.text(x, y, f"  {x:,.1f}".replace(",", " ").replace(".", ","), va="center",
                color=ch.INK, fontsize=12.5, fontweight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels([s if len(s) <= 28 else s[:27] + "…" for s in names], color=ch.INK, fontsize=12.5)
    ax.xaxis.set_visible(False)
    ax.set_xlim(0, max(v) * 1.22 if v and max(v) > 0 else 1)
    ch._clean(ax)
    top = 1 - 1.25 / fig.get_figheight()
    ch._head(fig, title, sub, y=1 - 0.45 / fig.get_figheight())
    fig.subplots_adjust(left=0.36, right=0.97, top=top, bottom=0.04)
    return ch._png(plt, fig)


def chart_rate(days, rates, cur, title, sub) -> bytes:
    """Курс валюты: аккуратная линия с заливкой, минимум, максимум и последнее значение."""
    from . import digest_charts as ch
    plt = ch._plt()
    fig, ax = plt.subplots(figsize=(10.8, 7.0), dpi=100)
    xs = list(range(len(days)))
    lo, hi = min(rates), max(rates)
    pad = (hi - lo) * 0.18 or hi * 0.01
    ax.plot(xs, rates, color=ch.GREEN, lw=2.6)
    ax.fill_between(xs, rates, lo - pad, color=ch.GREEN, alpha=.08)
    d = 4 if rates[-1] < 1 else 2
    for i, c, va in ((rates.index(hi), ch.GREEN, "bottom"), (rates.index(lo), ch.WARM, "top")):
        ax.plot([i], [rates[i]], "o", color=c, ms=6)
        ax.text(i, rates[i], f"\n{rates[i]:.{d}f}\n".replace(".", ","), color=c, fontsize=12,
                ha="center", va=va)
    ax.plot([xs[-1]], [rates[-1]], "o", color=ch.INK, ms=8)
    ax.text(xs[-1], rates[-1], f"  {rates[-1]:.{d}f}".replace(".", ","), color=ch.INK, fontsize=14,
            fontweight="bold", va="center", ha="left")
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(-0.5, xs[-1] * 1.1 + 1)
    n = len(days)
    ticks = sorted({0, n - 1, *range(0, n, max(1, n // 5))})
    ticks = [t for t in ticks if t == n - 1 or n - 1 - t > n / 12]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{days[t]:%d.%m}" if n <= 100 else f"{days[t]:%m.%y}" for t in ticks],
                       color=ch.MUTED, fontsize=12)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.{d}f}".replace(".", ","))
    ax.tick_params(axis="y", labelcolor=ch.MUTED, labelsize=12)
    ax.yaxis.grid(True, color=ch.GRID, lw=1)
    ax.set_axisbelow(True)
    ch._clean(ax)
    ch._head(fig, title, sub)
    fig.subplots_adjust(left=0.1, right=0.96, top=0.8, bottom=0.1)
    return ch._png(plt, fig)


def _mln(v, unit="₽") -> str:
    v = float(v or 0)
    if abs(v) >= 1e6:
        return num(v / 1e6, 2) + f" млн {unit}"
    return num(v) + f" {unit}"


_CODE = re.compile(r"^\d{3,}\s+")


def _art(s) -> str:
    """Статья без кода: «123400 Консалтинг» → «Консалтинг»."""
    return _CODE.sub("", str(s or "")).strip()


def _sgn(v) -> str:
    return ("+" if v >= 0 else "−") + rub(abs(v))


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
    tr = float(wb[7] or 0) if wb and len(wb) > 7 else 0.0
    tr0 = float(wb0[7] or 0) if wb0 and len(wb0) > 7 else 0.0
    bank, bank0 = by_cur.get("RUB", 0.0), by_cur0.get("RUB", 0.0)
    total, total0 = bank + wb_bal + tr, bank0 + wb_bal0 + tr0
    since = a - timedelta(days=1)
    lines = [f"<b>💰 Остатки на {b:%d.%m.%Y}</b>",
             f"<i>изменение с {since:%d.%m.%Y}"
             + (f" · банк загружен по {last_bank:%d.%m.%Y}" if last_bank else "") + "</i>", "",
             f"Итого денежных средств: <b>{rub(total)}</b>  {_dlt(total, total0)}",
             f"Банковские счета: <b>{rub(bank)}</b>  {_dlt(bank, bank0)}"]
    if wb:
        lines.append(f"Баланс WB: <b>{rub(wb_bal)}</b>  {_dlt(wb_bal, wb_bal0)}")
    if abs(tr) >= 0.5:
        lines.append(f"Деньги в пути от WB: <b>{rub(tr)}</b>")
    for c in sorted(c for c in by_cur if c != "RUB"):
        if abs(by_cur[c]) >= 0.5 or abs(by_cur0.get(c, 0)) >= 0.5:
            lines.append(f"Счета в {c}: <b>{num(by_cur[c])} {c}</b>  {_dlt(by_cur[c], by_cur0.get(c, 0), c)}")
    acc = sorted(((n, c, v, beg.get((n, c), (None, 0.0))[1]) for (n, c), (s, v) in end.items()
                  if abs(v) >= 0.5), key=lambda x: (x[1] != "RUB", -abs(x[2])))
    if acc:
        lines += ["", "<b>По счетам</b>"] + [
            f"• {esc(n)} — <b>{num(v)} {c}</b>" + (f" ({'+' if v - v0 > 0 else '−'}{num(abs(v - v0))})"
                                                   if abs(v - v0) >= 1 else "")
            for n, c, v, v0 in acc[:15]]
        if len(acc) > 15:
            lines.append(f"…ещё {len(acc) - 15} — в Excel.")
    if abs(dep) >= 0.5 or abs(dep0) >= 0.5:
        lines += ["", f"Справочно — банковские депозиты: <b>{rub(dep)}</b>  {_dlt(dep, dep0)}",
                  "<i>Размещены под проценты, в итог денежных средств не входят.</i>"]
    lines += ["", "<i>Итого = рублёвые счета + баланс WB + деньги в пути. Как лист «Остатки ДС» "
                  "мэн пака.</i>"]
    files = (("acc", "Excel: остатки по счетам"),)
    photo = None
    if 1 < ndays(a, b) <= 62:
        days, ins, outs = _daily(_cf(a, b), a, b)
        photo = _chart(lambda: chart_flow(days, ins, outs, f"Итого денежных средств — {rub(total)}",
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
        if abs(v) >= 0.5 or abs(v0) >= 0.5:
            rows.append([n, c, s, v0, v, v - v0])
    if wb:
        w0 = float(wb0[6] or 0) if wb0 else 0.0
        rows.append(["Баланс WB", "RUB", "", w0, float(wb[6] or 0), float(wb[6] or 0) - w0])
    rows.append(["Справочно: банковские депозиты (в итог не входят)", "RUB", "", dep0, dep, dep - dep0])
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
        lines += ["", "<b>Крупнейшие выплаты</b>"] + [f"• {esc(_art(k) or 'Без статьи')} — {rub(-v)}"
                                                      for k, v in o.items()]
    i = df[df.amount > 0].groupby("subitem").amount.sum().sort_values(ascending=False).head(5)
    if len(i):
        lines += ["", "<b>Крупнейшие поступления</b>"] + [f"• {esc(_art(k) or 'Без статьи')} — {rub(v)}"
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
    lines += ["", "<b>По статьям</b>"] + [f"• {esc(_art(k) or 'Без статьи')} — {('+' if v >= 0 else '−') + rub(abs(v))}"
                                          for k, v in it.items()]
    ct = part.groupby("contract").amount.sum().sort_values()
    if len(ct) > 1:
        lines += ["", "<b>По договорам</b>"] + [f"• {esc(k)} — {('+' if v >= 0 else '−') + rub(abs(v))}"
                                                for k, v in ct.head(6).items()]
    last = part.sort_values("d", ascending=False).head(8)
    lines += ["", "<b>Последние операции</b>"] + [
        f"• {r.d:%d.%m.%Y} — {('+' if r.amount >= 0 else '−') + rub(abs(r.amount))} · {esc(_art(r.subitem or r.item))}"
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
    again = [{"text": "🔁 Искать ещё", "callback_data": "fm:o:s"}]
    if hit is None or hit.empty:
        lines.append("Ничего не нашлось. Попробуйте другое слово или сумму.")
        return {"text": "\n".join(lines), "photo": None, "auto": None, "files": (),
                "kb": {"inline_keyboard": [again]}}
    paid, got = -hit[hit.amount < 0].amount.sum(), hit[hit.amount > 0].amount.sum()
    lines.append(f"Найдено: <b>{num(len(hit))} операций</b>")
    if paid:
        lines.append(f"Выплачено: <b>{rub(paid)}</b>")
    if got:
        lines.append(f"Получено: <b>{rub(got)}</b>")
    groups = hit.groupby("cp").amount.agg(["sum", "size"])
    groups = groups.reindex(groups["sum"].abs().sort_values(ascending=False).index)
    shown = 0
    for cp, g in groups.head(5).iterrows():
        part = hit[hit.cp == cp]
        arts = part.subitem.where(part.subitem != "", part.item).map(_art)
        main = arts.mode().iat[0] if len(arts) else ""
        lines += ["", f"<b>{esc(cp)}</b>",
                  f"{num(g['size'])} опер. · <b>{_sgn(g['sum'])}</b>" + (f" · {esc(main)}" if main else "")]
        for r, art in zip(part.head(6).itertuples(), arts.head(6)):
            lines.append(f"• {r.d:%d.%m.%Y} — <b>{_sgn(r.amount)}</b>"
                         + (f" · {esc(art)}" if art and art != main else ""))
            shown += 1
        if len(part) > 6:
            lines.append(f"…ещё {len(part) - 6}")
    if len(groups) > 5:
        lines += ["", f"…и ещё {len(groups) - 5} контрагентов — в Excel."]
    _LAST_SEARCH["q"] = text
    photo = None
    mon = hit.assign(m=[d.replace(day=1) for d in hit.d]).groupby("m").amount.apply(lambda s: s.abs().sum())
    if len(mon) >= 3:
        ms, m = [], a.replace(day=1)
        while m <= hi:
            ms.append(m)
            m = (m + timedelta(days=32)).replace(day=1)
        photo = _chart(lambda: chart_bars([f"{M.MONTHS[x.month - 1][:3].lower()}" for x in ms],
                                          [float(mon.get(x, 0)) for x in ms],
                                          f"«{text[:30]}» по месяцам", "сумма операций, млн ₽"))
    return {"text": "\n".join(lines), "photo": photo, "auto": None,
            "files": (("found", "Excel: найденные операции"),),
            "kb": {"inline_keyboard": [[{"text": "⬇️ Excel: найденные операции",
                                         "callback_data": f"fm:f:s:found:{ymd(a)}:{ymd(hi)}"}], again]}}


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
    keys += [("tbu", "ТБУ с конв. займами"), ("zfp_pct", "Запас прочности с конв. займами, %"),
             ("tbu_ex", "ТБУ без конв. займов"), ("zfp_ex_pct", "Запас прочности без конв. займов, %")]
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
    lines = ["<b>🎯 Точка безубыточности</b>", f"<i>по данным мэн пака на {rd:%d.%m.%Y} · "
             "две ТБУ: с процентами по конвертируемым займам и без них</i>"]
    W, X = "с конв. займами", "без конв. займов"

    def two(d, fmt):
        """Строки сравнения сразу с обеими ТБУ."""
        out = []
        for key, name in (("tbu", W), ("tbu_ex", X)):
            if d.get(key) is not None:
                out.append(fmt(d[key], name))
        return out

    for m in show:
        d = data["derived"][m]
        lines += ["", f"<b>{M.MONTHS[m.month - 1]} {m.year}</b> · выручка {rub(d['rev'])}"]
        if d.get("tbu") is None:
            lines.append("ТБУ не определена (маржинальность ≤ 0)")
            continue
        zp = {"tbu": d.get("zfp_pct"), "tbu_ex": d.get("zfp_ex_pct")}
        for key, name in (("tbu", W), ("tbu_ex", X)):
            if d.get(key) is not None:
                lines.append(f"ТБУ {name}: <b>{rub(d[key])}</b>"
                             + (f" · запас {num(zp[key], 1)}%" if zp[key] is not None else ""))
    last = data["derived"][show[-1]]
    if last.get("tbu"):
        lines += ["", f"<b>Итог за {M.MONTHS[show[-1].month - 1].lower()}</b>"] + two(last, lambda t, n: (
            ("✅ Выручка выше ТБУ " if last["rev"] >= t else "⚠️ До ТБУ ")
            + f"{n}" + (" на " if last["rev"] >= t else " не хватает ")
            + f"<b>{rub(abs(last['rev'] - t))}</b> в месяц."))
        lines.append(f"Постоянные затраты месяца: {rub(abs(last.get('fc') or 0))}, из них % по "
                     f"конвертируемым займам {rub(abs(last.get('conv') or 0))}.")
    cur_m = _month_of(rd, months)
    if cur_m and cur_m > show[-1] and last.get("tbu"):
        fact = data["derived"][cur_m].get("rev") or 0
        lines += ["", f"<b>Текущий месяц на {rd:%d.%m}</b>", f"Выручка: {rub(fact)}"] + two(
            last, lambda t, n: f"• {num(fact / t * 100, 0)}% от ТБУ {n} прошлого месяца"
                               + (f" — осталось {rub(t - fact)}" if t > fact else " — пройдена ✅"))
    lines += ["", "<i>ТБУ = постоянные затраты / доля маржинального дохода. Проценты по конвертируемым "
                  "займам начисляются, но деньгами не платятся — поэтому второй вариант без них.</i>"]
    files = (("pl", "Excel: P&L и ТБУ за 12 месяцев"),)
    ms = [m for m in closed if m <= me][-6:]
    ex = [data["derived"][m].get("tbu_ex") for m in ms]
    photo = _chart(lambda: chart_months(
        [f"{M.MONTHS[m.month - 1][:3].lower()}" for m in ms],
        [data["derived"][m].get("rev") or 0 for m in ms],
        [data["derived"][m].get("tbu") for m in ms], "выручка без НДС", "ТБУ с конв. займами",
        "Выручка против двух ТБУ, млн ₽", "выше линии — прибыль, ниже — убыток", dashed=True,
        line2=ex if any(v is not None for v in ex) else None, line2_name="ТБУ без конв. займов"))
    return {"text": "\n".join(lines), "photo": photo, "auto": None, "files": files,
            "kb": _files_kb("t", a, b, files)}


# ---------------------------------------------------------------- 📥 WB, 🏦 займы, 💱 курсы
def report_wb(a: date, b: date) -> dict | None:
    rec, transit, last_in = _wb(a, b)
    lines = [f"<b>📥 Поступления от WB · {span(a, b)}</b>",
             "<i>на расчётный счёт" + (f" · банк загружен по {last_in:%d.%m.%Y}" if last_in else "")
             + "</i>", ""]
    if not rec:
        lines.append("За этот период поступлений от WB не было.")
    else:
        total = sum(p["out_amount"] for p in rec)
        lines.append(f"Зачислено: <b>{rub(total)}</b> · {num(len(rec))} поступлений")
        lines.append(f"В среднем: {rub(total / len(rec))}")
    if transit:
        lines.append(f"В пути: <b>{rub(sum(p['out_amount'] for p in transit))}</b> — выведено из кабинета, "
                     "на счёт ещё не пришло")
    if rec:
        lines += ["", "<b>Зачисления</b>"] + [
            f"• {p['in_dt']:%d.%m.%Y}, {WD[p['in_dt'].weekday()]} — <b>{rub(p['out_amount'])}</b>"
            for p in sorted(rec, key=lambda x: x["in_dt"], reverse=True)[:15]]
        if len(rec) > 15:
            lines.append(f"…ещё {len(rec) - 15} — в Excel.")
    lines += ["", "<i>Кассовый метод: деньги на счёт, а не продажи. Как лист «Поступления от WB» мэн пака.</i>"]
    photo = None
    if rec and ndays(a, b) > 1:
        days = [a + timedelta(days=i) for i in range(ndays(a, b))]
        by = defaultdict(float)
        for p in rec:
            by[p["in_dt"]] += p["out_amount"]
        if ndays(a, b) <= 62:
            photo = _chart(lambda: chart_bars([f"{d:%d.%m}" for d in days], [by.get(d, 0) for d in days],
                                              f"Поступления от WB — {rub(sum(by.values()))}",
                                              f"по дням зачисления, млн ₽ · {span(a, b)}"))
        else:
            mon = defaultdict(float)
            for d, v in by.items():
                mon[d.replace(day=1)] += v
            ms = sorted(mon)
            photo = _chart(lambda: chart_bars([f"{M.MONTHS[m.month - 1][:3].lower()}" for m in ms],
                                              [mon[m] for m in ms],
                                              f"Поступления от WB — {rub(sum(by.values()))}",
                                              f"по месяцам, млн ₽ · {span(a, b)}"))
    files = (("xl", "Excel: поступления"),) if rec else ()
    return {"text": "\n".join(lines), "photo": photo, "auto": None, "files": files,
            "kb": _files_kb("w", a, b, files)}


def _wb(a: date, b: date):
    from gear.management.commands import mp
    from .wb_payouts import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        con.execute(mp.read_sql("wb_payouts.txt"), parameters={"date_from": b})
        rows = con.execute("SELECT * FROM wb_payouts").fetchall()
    outs, ins = mp.split_payouts(rows)
    pairs = mp.match_wb_payouts(outs, ins)
    rec = [p for p in pairs if p["in_dt"] and a <= p["in_dt"] <= b]
    transit = [p for p in pairs if p["in_dt"] is None and p["out_dt"] <= b]
    last_in = max((i["dt"] for i in ins), default=None)
    return rec, transit, last_in


def file_wb(a, b):
    rec, transit, _ = _wb(a, b)
    if not rec and not transit:
        return None
    rows = [[p["in_dt"], p["out_amount"]] for p in sorted(rec, key=lambda x: x["in_dt"])]
    sheets = [("Зачисления", ["Дата зачисления", "Сумма, ₽"], rows)]
    if transit:
        sheets.append(("В пути", ["Вывод из кабинета", "Сумма, ₽"], [[p["out_dt"], p["out_amount"]]
                                                                       for p in transit]))
    return f"Поступления от WB {span(a, b)}.xlsx", _book("Поступления от WB", span(a, b), sheets), XLSX


_LOAN_TYPE = (("конвертируем", "конвертируемый заём"), ("кредит", "кредит"), ("займ", "заём"))


def _loan_type(t) -> str:
    t = str(t or "").lower()
    return next((v for k, v in _LOAN_TYPE if k in t), t or "договор")


def _loans(on: date):
    from ...manpack import data as md
    df = md.loans(on)
    if df is None or df.empty:
        return df
    return df[df["total_debt"].abs() > 1].sort_values("total_debt", ascending=False)


def report_loans(a: date, b: date) -> dict | None:
    df = _loans(b)
    lines = [f"<b>🏦 Займы и кредиты на {b:%d.%m.%Y}</b>",
             "<i>тело + начисленные неуплаченные проценты</i>"]
    if df is None or df.empty:
        lines += ["", "Займов и кредитов нет."]
        return {"text": "\n".join(lines), "photo": None, "auto": None, "files": (),
                "kb": _retag(period_kb("l"))}
    photo = None
    for code, title in (("borrowed", "📕 Мы должны"), ("issued", "📗 Нам должны")):
        part = df[df["loan_direction"] == code]
        if part.empty:
            continue
        lines += ["", f"<b>{title} — {_mln(part['total_debt'].sum())}</b>",
                  f"тело {_mln(part['ending_balance'].sum())} · проценты {_mln(part['interest_balance'].sum())}"]
        for i, r in enumerate(part.itertuples(), 1):
            cur = r.currency or "RUB"
            unit = "₽" if cur == "RUB" else cur
            rep_d = getattr(r, "repayment_date", None)
            due = f" · до {rep_d:%d.%m.%Y}" if rep_d is not None and rep_d == rep_d else ""
            rate = f" · {num(r.rate, 2).rstrip('0').rstrip(',')}%" if r.rate == r.rate and r.rate else ""
            cn = r.contract_number if isinstance(r.contract_number, str) and r.contract_number.strip() else "б/н"
            lines += ["", f"{i}. <b>{esc(r.counterparty_name or '—')}</b>",
                      f"<b>{_mln(r.total_debt, unit)}</b>{rate}{due}",
                      f"<i>{_loan_type(r.contract_type)} № {esc(cn)} · "
                      f"тело {_mln(r.ending_balance, unit)}, % {_mln(r.interest_balance, unit)}</i>"]
        if code == "borrowed" and len(part) > 1:
            rub_part = part[(part["currency"].fillna("RUB") == "RUB")].head(8)
            photo = _chart(lambda: chart_hbar(list(rub_part["counterparty_name"].fillna("—").astype(str)),
                                              list(rub_part["total_debt"]),
                                              f"Мы должны — {_mln(part['total_debt'].sum())}",
                                              "тело + проценты, млн ₽"))
    lines += ["", "<i>Суммы в валюте договора. Как дашборд «Займы и кредиты».</i>"]
    files = (("xl", "Excel: займы"),)
    return {"text": "\n".join(lines), "photo": photo, "auto": None, "files": files,
            "kb": _files_kb("l", a, b, files)}


def file_loans(a, b):
    df = _loans(b)
    if df is None or df.empty:
        return None
    cols = ["Направление", "Контрагент", "Договор", "Валюта", "Ставка, %", "Тело", "Проценты", "Всего",
            "Срок погашения"]
    rows = []
    for r in df.itertuples():
        rep_d = getattr(r, "repayment_date", None)
        rows.append(["Мы должны" if r.loan_direction == "borrowed" else "Нам должны",
                     r.counterparty_name or "", f"{r.contract_type or ''} № "
                     + (r.contract_number if isinstance(r.contract_number, str) and r.contract_number else "б/н"),
                     r.currency or "RUB", r.rate, r.ending_balance, r.interest_balance, r.total_debt,
                     rep_d if rep_d is not None and rep_d == rep_d else ""])
    return f"Займы на {b:%d.%m.%Y}.xlsx", _book("Займы и кредиты", f"на {b:%d.%m.%Y}", [("Займы", cols, rows)]), XLSX


def _fx(a: date, b: date):
    from ...manpack import data as md
    df = md.fx(a, b)
    return md, df


def _fx_series(df, cur, a, b):
    d = df[df["currency"] == cur].dropna(subset=["rate"])
    before = d[d["date"] < a]
    d = d[(d["date"] >= a) & (d["date"] <= b)]
    if not before.empty and (d.empty or d["date"].iat[0] > a):
        d = pd.concat([before.tail(1), d])
    return list(d["date"]), [float(x) for x in d["rate"]]


def report_fx(a: date, b: date, cur: str | None = None) -> dict | None:
    md, df = _fx(a, b)
    curs = [c for c in md.FX_CURRENCIES if not df.empty and (df["currency"] == c).any()]
    if not curs:
        return None
    cur = cur if cur in curs else curs[0]
    days, rates = _fx_series(df, cur, a, b)
    if not rates:
        return None
    d = 4 if rates[-1] < 1 else 2
    f = lambda v: num(v, d)  # noqa: E731
    ch = (rates[-1] - rates[0]) / rates[0] * 100 if rates[0] else 0
    lines = [f"<b>💱 {cur} · {f(rates[-1])} ₽</b>",
             f"<i>курс ЦБ на {days[-1]:%d.%m.%Y} · {span(a, b)}</i>", "",
             f"За период: <b>{'▲ +' if ch > 0 else '▼ −' if ch < 0 else ''}{num(abs(ch), 1)}%</b> "
             f"({f(rates[0])} → {f(rates[-1])})",
             f"Минимум: {f(min(rates))} · {days[rates.index(min(rates))]:%d.%m.%Y}",
             f"Максимум: {f(max(rates))} · {days[rates.index(max(rates))]:%d.%m.%Y}"]
    others = []
    for c in curs:
        if c == cur:
            continue
        _, rr = _fx_series(df, c, a, b)
        if rr:
            dd = 4 if rr[-1] < 1 else 2
            cc = (rr[-1] - rr[0]) / rr[0] * 100 if rr[0] else 0
            others.append(f"• {c} — <b>{num(rr[-1], dd)} ₽</b> ({'▲ +' if cc > 0 else '▼ −' if cc < 0 else ''}"
                          f"{num(abs(cc), 1)}%)")
    if others:
        lines += ["", "<b>Другие валюты за период</b>"] + others
    kr, kr_d = md.key_rate(min(b, date.today()))
    if kr is not None:
        lines += ["", f"Ключевая ставка ЦБ: <b>{num(kr, 2)}%</b> с {kr_d:%d.%m.%Y}"]
    photo = _chart(lambda: chart_rate(days, rates, cur, f"{cur} — {f(rates[-1])} ₽",
                                      f"рублей за единицу · {span(a, b)}"))
    files = (("xl", "Excel: курсы"),)
    kb = _files_kb("x", a, b, files)
    pick = [{"text": ("✓ " if c == cur else "") + c, "callback_data": f"fm:a:x:{c}:{ymd(a)}:{ymd(b)}"}
            for c in curs]
    per = [{"text": t, "callback_data": f"fm:p:x:{c}"} for c, t in PRESETS["x"]]
    kb["inline_keyboard"] = [pick, per[:2], per[2:]] + kb["inline_keyboard"]
    kb["inline_keyboard"] = [r for r in kb["inline_keyboard"] if r]
    return {"text": "\n".join(lines), "photo": photo, "auto": None, "files": files, "kb": kb}


def file_fx(a, b):
    md, df = _fx(a, b)
    if df.empty:
        return None
    p = df[(df["date"] >= a) & (df["date"] <= b)].pivot_table(index="date", columns="currency",
                                                              values="rate", aggfunc="last").sort_index()
    cols = ["Дата"] + list(p.columns)
    rows = [[d] + [None if v != v else float(v) for v in r] for d, r in zip(p.index, p.values)]
    return f"Курсы валют {span(a, b)}.xlsx", _book("Курсы валют ЦБ", f"рублей за единицу · {span(a, b)}",
                                                   [("Курсы", cols, rows)]), XLSX




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
    lines = [f"<b>🚚 Приходы (УПД) · {title}</b>", "<i>суммы без НДС</i>", "",
             f"Документов: <b>{num(tot['docs'])}</b> · товара <b>{num(tot['qty'])} шт</b>",
             f"Сумма по УПД: <b>{rub(tot['buh'])}</b>"]
    lines += ["", "<b>Документы</b>"] + [
        f"• {r.d:%d.%m.%Y} · УПД №{esc(r.number)} · <b>{esc(r.cp)}</b> · {rub(r.buh)} · {num(r.qty)} шт"
        + (f" · 📎{files_n[r.doc_id]}" if files_n.get(r.doc_id) else "")
        for r in docs.head(15).itertuples()]
    if len(docs) > 15:
        lines.append(f"…ещё {len(docs) - 15} — в Excel.")
    with_files = [r for r in docs.itertuples() if files_n.get(r.doc_id)][:10]
    if with_files:
        lines += ["", "📎 Файлы документов — кнопками ниже, пришлю в чат."]
    kb = _files_kb("u", a, b, (("xl", "Excel: приходы"),))
    kb["inline_keyboard"] = [[{"text": f"📎 {r.d:%d.%m} · №{r.number} · {str(r.cp)[:18]} · {rub(r.buh)}",
                               "callback_data": f"fm:u:u:{r.doc_id}"}] for r in with_files] \
        + kb["inline_keyboard"]
    return {"text": "\n".join(lines), "photo": None, "auto": None,
            "files": (("xl", "Excel: приходы"),), "kb": kb}


def upd_title(doc_id: int) -> str:
    """Подпись к файлам УПД: номер, дата, поставщик, сумма."""
    try:
        from django.db.models import Sum
        from cards.models import UpdDocument
        d = UpdDocument.objects.select_related("counterparty").get(pk=doc_id)
        s = d.income_lines.aggregate(s=Sum("upd_amount_vatless"))["s"]
        return (f"📎 <b>УПД №{esc(d.number)} от {d.date:%d.%m.%Y}</b>\n"
                f"{esc(d.counterparty.name if d.counterparty else 'Без поставщика')}"
                + (f" · {rub(s)} без НДС" if s else ""))
    except Exception as e:
        print(f"[fin_menu] УПД {doc_id}: {type(e).__name__}: {e}", flush=True)
        return ""


WD = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")




def cp_find(text: str) -> list[tuple[str, str]]:
    """Контрагенты из справочника по части названия или ИНН: [(подпись, id)]."""
    from django.db.models import Q
    from counterparties.models import Counterparty
    q = (text or "").strip()
    if len(q) < 2:
        return []
    flt = Q(name__icontains=q) | Q(fullname__icontains=q)
    if q.isdigit():
        flt |= Q(tax_id__startswith=q)
    out = []
    for cp in Counterparty.objects.filter(flt).order_by("name")[:8]:
        out.append((f"{cp.name}" + (f" · ИНН {cp.tax_id}" if cp.tax_id else ""), str(cp.pk)))
    return out


def report_check(cp_id) -> dict:
    from contracts.models import Contracts
    from counterparties.models import Counterparty
    from .counterparties import _risks
    again = {"inline_keyboard": [[{"text": "🔁 Проверить другого", "callback_data": "fm:o:k"}]]}
    cp = Counterparty.objects.select_related("gr").filter(pk=cp_id).first()
    if not cp:
        return {"text": "Контрагент не найден.", "photo": None, "auto": None, "files": (), "kb": again}
    risks = _risks(cp)
    lines = [f"<b>🛡 {esc(cp.name)}</b>"]
    if cp.fullname and cp.fullname.strip().lower() != cp.name.strip().lower():
        lines.append(f"<i>{esc(cp.fullname)}</i>")
    lines.append("")
    head = [("ИНН", cp.tax_id), ("ОПФ", cp.okopf_name),
            ("Группа", cp.gr.name if cp.gr_id else None),
            ("ОКВЭД", f"{cp.okved_code} {cp.okved_name or ''}".strip() if cp.okved_code else None),
            ("Регион", cp.region), ("Налоговый режим", cp.taxregime)]
    lines += [f"{k}: <b>{esc(v)}</b>" for k, v in head if v]
    lines.append(("✅ Риски не отмечены" if risks == "не отмечены" else f"⚠️ Риски: <b>{esc(risks)}</b>"))
    cl = list(Contracts.objects.filter(cp=cp).select_related("title", "owner").order_by("-date")[:16])
    if cl:
        lines += ["", f"<b>Договоры ({len(cl) if len(cl) < 16 else '15+'})</b>"]
        for c in cl[:15]:
            t = getattr(c.title, "title", "") or "Договор"
            lines.append(f"• {esc(t)} № {esc(c.number or 'б/н')}"
                         + (f" от {c.date:%d.%m.%Y}" if c.date else "")
                         + ("" if c.is_signed else " · <i>не подписан</i>")
                         + (" · <i>неактивен</i>" if getattr(c, "is_active", None) is False else ""))
    else:
        lines += ["", "Договоров нет."]
    try:
        hi = loaded()
        df = _cf(hi - timedelta(days=364), hi)
        part = df[df["cp"].str.lower() == cp.name.strip().lower()] if df is not None and not df.empty else None
        if part is not None and not part.empty:
            paid, got = -part[part.amount < 0].amount.sum(), part[part.amount > 0].amount.sum()
            lines += ["", "<b>Деньги за 12 месяцев</b>"]
            if paid:
                lines.append(f"Заплатили: <b>{rub(paid)}</b>")
            if got:
                lines.append(f"Получили: <b>{rub(got)}</b>")
            lines.append(f"Последняя операция: {part.d.max():%d.%m.%Y}")
    except Exception as e:
        print(f"[fin_menu] проверка: деньги: {type(e).__name__}: {e}", flush=True)
    lines += ["", "<i>По справочнику контрагентов, договорам и выписке банка.</i>"]
    return {"text": "\n".join(lines), "photo": None, "auto": None, "files": (), "kb": again}


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
    if rep == "w":
        return report_wb(a, b)
    if rep == "l":
        return report_loans(a, b)
    if rep == "x":
        return report_fx(a, b, arg)
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
    if rep == "w":
        return file_wb(a, b)
    if rep == "l":
        return file_loans(a, b)
    if rep == "x":
        return file_fx(a, b)
    if rep == "mp":
        return file_mp(a, b)
    if rep == "u":
        return file_upd(a, b)
    return None


PICK_REPORT = {"k"}                 # выбор из вариантов сразу даёт отчёт


def picked(rep: str, value: str) -> dict | None:
    return report_check(value) if rep == "k" else None


def query(rep: str, text: str, hi: date):
    """Текстовый запрос: результат отчёта или список вариантов [(подпись, значение)]."""
    if rep == "k":
        found = cp_find(text)
        if len(found) == 1:
            return report_check(found[0][1])
        return found
    if rep == "s":
        return report_search(text)
    if rep == "p":
        return [(n, n) for n in cp_search(text, hi)]
    return None
