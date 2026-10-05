# gear/app/daily_sales/assistant/finance_extra.py
"""Финансовые инструменты помощника на данных дашборда «Управленческий пакет»:
займы и кредиты, курсы валют, приходы (УПД), выводы за месяц."""
from __future__ import annotations

from datetime import date


def _d(v, default=None):
    return date.fromisoformat(str(v)[:10]) if v else (default or date.today())


def _f(v, d=0):
    return "—" if v is None or v != v else f"{float(v):,.{d}f}".replace(",", " ")


def _me(v):
    from ...manpack import data
    return data.month_end(_d(v))


def loans_report(as_of=None) -> str:
    from ...manpack import data
    d = _d(as_of)
    df = data.loans(d)
    if df.empty:
        return f"На {d:%d.%m.%Y} займов и кредитов нет."
    lines = [f"ЗАЙМЫ И КРЕДИТЫ на {d:%d.%m.%Y} (основной долг + начисленные неуплаченные проценты)"]
    for code, title in (("borrowed", "МЫ ДОЛЖНЫ"), ("issued", "НАМ ДОЛЖНЫ")):
        part = df[(df["loan_direction"] == code) & (df["total_debt"].abs() > 1)]
        lines.append(f"\n{title}: всего {_f(part['total_debt'].sum())}, тело "
                     f"{_f(part['ending_balance'].sum())}, проценты {_f(part['interest_balance'].sum())}")
        if part.empty:
            continue
        lines.append("Контрагент\tДоговор\tВалюта\tСтавка, %\tТело\tПроценты\tВсего\tСрок погашения")
        for r in part.sort_values("total_debt", ascending=False).itertuples():
            inn = str(getattr(r, "inn", "") or "")
            cp = f"ИП/физлицо (ИНН …{inn[-4:]})" if len(inn) == 12 else (r.counterparty_name or "—")
            rep = getattr(r, "repayment_date", None)
            due = rep.strftime("%d.%m.%Y") if rep is not None and rep == rep else "—"
            lines.append(f"{cp}\t{r.contract_type or ''} № {r.contract_number or 'б/н'}\t"
                         f"{r.currency or 'RUB'}\t{_f(r.rate, 2)}\t{_f(r.ending_balance)}\t"
                         f"{_f(r.interest_balance)}\t{_f(r.total_debt)}\t{due}")
    lines.append("\nСуммы в валюте договора. Источник — дашборд «Займы и кредиты».")
    return "\n".join(lines)


def fx_report(month=None) -> str:
    from ...manpack import data
    from ...manpack.tabs import fx
    me = _me(month)
    st, _ = fx.stats(me)
    if not st:
        return "В справочнике курсов нет данных по USD, EUR, CNY, AMD за этот период."
    lines = ["КУРСЫ ВАЛЮТ (рублей за единицу)",
             "Валюта\tКурс\tДата\tИзменение за месяц, %\tИзменение с начала года, %"]
    for s in st:
        lines.append(f"{s['cur']}\t{_f(s['rate'], 4)}\t{s['date']:%d.%m.%Y}\t"
                     f"{_f(s['m_ch'], 1)}\t{_f(s['y_ch'], 1)}")
    kr, kr_d = data.key_rate(min(me, date.today()))
    if kr is not None:
        lines.append(f"Ключевая ставка ЦБ: {_f(kr, 2)}% (с {kr_d:%d.%m.%Y})")
    lines.append("Источник — справочник «Макро». Это курсы из базы компании, не онлайн-котировки.")
    return "\n".join(lines)


def upd_report(month=None, by="brand") -> str:
    from ...manpack.tabs import upd
    me = _me(month)
    docs, brands, tot = upd.tables(me)
    if not tot:
        return f"Приходов (УПД) за {me:%m.%Y} нет."
    diff = tot["man"] - tot["buh"]
    lines = [f"ПРИХОДЫ (УПД) за {me:%m.%Y}: документов {tot['docs']}, {_f(tot['qty'])} шт; "
             f"бух. стоимость {_f(tot['buh'])} ₽, упр. стоимость {_f(tot['man'])} ₽, "
             f"разница упр. − бух. {_f(diff)} ₽. Строк без упр. себестоимости: {tot['no_man']}."]
    if by == "document":
        lines.append("Дата\tУПД\tПоставщик\tКол-во\tБух., ₽\tУпр., ₽\tРазница, ₽")
        for r in docs.head(60).itertuples():
            lines.append(f"{r.d:%d.%m.%Y}\t{r.number}\t{r.cp}\t{_f(r.qty)}\t{_f(r.buh)}\t"
                         f"{_f(r.man)}\t{_f(r.diff)}")
    else:
        lines.append("Бренд\tКол-во\tБух., ₽\tУпр., ₽\tРазница, ₽\tБух. цена/шт\tУпр. цена/шт")
        for r in brands.head(60).itertuples():
            lines.append(f"{r.brand}\t{_f(r.qty)}\t{_f(r.buh)}\t{_f(r.man)}\t{_f(r.diff)}\t"
                         f"{_f(r.buh_unit, 2)}\t{_f(r.man_unit, 2)}")
    lines.append("Суммы без НДС. Бух. — цена УПД, упр. — управленческая себестоимость.")
    return "\n".join(lines)


def month_conclusions(month=None) -> str:
    from ...manpack import data
    me = _me(month)
    s = data.month_summary(me)
    lines = [f"ВЫВОДЫ ЗА {s.get('title', '').upper()} (лист «Выводы» мэн пака)",
             "ГЛАВНОЕ: " + s.get("headline", "")]
    if s.get("partial"):
        lines.append("Месяц неполный: %d из %d дней." % s["partial"])
    for n, (head, paras) in enumerate(s.get("blocks", []), 1):
        lines.append(f"\n{n}. {head}")
        lines += list(paras)
    return "\n".join(lines)


def scenario_report(month=None, base="3", revenue_pct=0, kmd_pp=0, fixed_add=0,
                    ex_conv=False) -> str:
    """Сценарий «что будет, если»: тот же расчёт, что на вкладке «Прогноз и ТБУ»."""
    from ...manpack import data
    from ...manpack.tabs import forecast
    me = _me(month)
    rd = data.pl_bundle()["report_date"]
    partial = me > rd                                   # месяц ещё не закрыт
    mode = str(base or "3")
    if partial and mode == "me":
        mode = "3"                                      # по неполному месяцу ТБУ не считаем
    d, label = forecast.base(me, mode)
    if not d or not d.get("rev"):
        return "Нет данных P&L для расчёта сценария."
    b0 = forecast.scenario(d, ex_conv=bool(ex_conv))
    s = forecast.scenario(d, float(revenue_pct or 0), float(kmd_pp or 0),
                          float(fixed_add or 0), bool(ex_conv))

    def block(title, x):
        return (f"{title}: выручка {_f(x['rev'])} ₽, КМД {_f(x['kmd'], 1)}%, маржинальный доход "
                f"{_f(x['md'])} ₽, постоянные затраты {_f(x['fc'])} ₽, результат до налога "
                f"{_f(x['ebt'])} ₽ в месяц ({_f(x['ebt'] * 12)} ₽ за 12 мес.), ТБУ "
                + (f"{_f(x['tbu'])} ₽, запас прочности {_f(x['zfp_pct'], 1)}%"
                   if x["tbu"] is not None else "не определена (КМД ≤ 0)"))
    lines = [f"СЦЕНАРИЙ. ПЕРИОД ЦИФР: {label} (средний месяц базы; "
             f"{'без' if ex_conv else 'с'} процентов по конвертируемым займам)",
             block("База", b0), block("Сценарий", s),
             f"Изменение результата: {_f(s['ebt'] - b0['ebt'])} ₽ в месяц."]
    if s["tbu"] is not None and s["tbu"] > s["rev"]:
        lines.append(f"До безубыточности не хватает {_f(s['tbu'] - s['rev'])} ₽ выручки в месяц.")
    if partial:
        f, _ = forecast.base(me, "me")
        fact = (f or {}).get("rev") or 0.0
        lines.append(
            f"НАЧНИ ОТВЕТ С ФРАЗЫ: «Месяц {me:%m.%Y} ещё не закрыт, поэтому ТБУ посчитана "
            f"по среднему за {label}; факт месяца — на {rd:%d.%m.%Y}». "
            f"ВНИМАНИЕ: {me:%m.%Y} не закрыт. Выручка и запас прочности выше — это НЕ факт "
            f"{me:%m.%Y}, а средний месяц базы ({label}). ФАКТ {me:%m.%Y} на {rd:%d.%m.%Y}: "
            f"выручка {_f(fact)} ₽"
            + (f", это {_f(fact / s['tbu'] * 100, 1)}% от ТБУ, до ТБУ осталось "
               f"{_f(max(0.0, s['tbu'] - fact))} ₽." if s["tbu"] else "."))
    lines.append("Расчёт линейный: КМД и постоянные затраты не зависят от объёма; прочие "
                 "доходы и расходы — как в базе. Это оценка, а не план.")
    return "\n".join(lines)


def contracts_ending_report(month=None) -> str:
    from ...manpack import data
    me = _me(month)
    items = data.contracts_ending(data.month_start(me), me)
    if not items:
        return f"Договоров с окончанием в {me:%m.%Y} нет (по датам окончания условий)."
    lines = [f"ДОГОВОРЫ, ЗАКАНЧИВАЮЩИЕСЯ В {me:%m.%Y}: {len(items)}",
             "Контрагент\tТип\tНомер\tДата договора\tОкончание"]
    for c in items[:60]:
        lines.append(f"{c['cp']}\t{c['type']}\t{c['number']}\t"
                     f"{c['date']:%d.%m.%Y}\t{c['date_end']:%d.%m.%Y}" if c["date"] else
                     f"{c['cp']}\t{c['type']}\t{c['number']}\t—\t{c['date_end']:%d.%m.%Y}")
    return "\n".join(lines)


def profit_vs_cash_report(month=None) -> str:
    """Прибыль (начисление) против денежного потока за месяц — одной таблицей."""
    from ...manpack import data
    me = _me(month)
    p = data.profit_vs_cash(me)
    if p["net"] is None:
        return "Нет данных P&L за этот месяц."
    acts = "; ".join(f"{k}: {_f(v)} ₽" for k, v in
                     sorted(p["by_activity"].items(), key=lambda x: -abs(x[1])))
    top = list(p["top_cf"].items())
    outs = "; ".join(f"{k}: {_f(v)}" for k, v in top[:6])
    ins = "; ".join(f"{k}: {_f(v)}" for k, v in top[::-1][:4])
    lines = [
        f"ПРИБЫЛЬ ПРОТИВ ДЕНЕГ, {me:%m.%Y}",
        "Показатель\tP&L (начисление), ₽\tДеньги (ДДС), ₽",
        f"Итог месяца\t{_f(p['net'])} (чистая прибыль)\t{_f(p['cf_net'])} (сальдо ДДС)",
        f"Выручка / поступления от WB\t{_f(p['rev'])}\t"
        + (_f(p["wb_in"]) if p["wb_in"] is not None else "н/д"),
        f"Проценты по займам\t{_f(p['fin'])} (начислено, раздел 8)\t"
        f"{_f(p['interest_paid'])} (уплачено и получено)",
        f"Налог на прибыль\t{_f(p['tax'])}\t{_f(p['tax_paid'])}",
        f"Товар\t{_f(p['cogs'])} (себестоимость проданного)\tоплаты поставщикам — см. выплаты ниже",
        f"Разница прибыль − деньги: {_f(p['net'] - p['cf_net'])} ₽",
        f"ДДС по видам деятельности: {acts or 'нет данных'}",
        f"Крупнейшие выплаты (подстатьи ДДС): {outs or 'нет'}",
        f"Крупнейшие поступления: {ins or 'нет'}",
        "Как объяснять: получение и возврат займов — деньги, но не прибыль; закупка товара — "
        "деньги сейчас, расход при продаже; начисленные, "
        "но не уплаченные проценты уменьшают прибыль, но не деньги; выручка WB приходит на "
        "счёт с задержкой. Называй только те причины, которые видны в цифрах выше.",
    ]
    return "\n".join(lines)
