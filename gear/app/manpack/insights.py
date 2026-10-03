# gear/app/manpack/insights.py
"""Уведомления месяца: новые контрагенты и сотрудники, курсы валют, займы, данные."""
from __future__ import annotations

from datetime import date, timedelta

from . import data
from .config import BANK_LAG_DAYS, FX_ALERT_PCT, FX_CURRENCIES, LOAN_DUE_DAYS
from .theme import fmt_date, money, num, pct


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def notifications(me: date) -> list[dict]:
    """Список уведомлений: tone (bad / warn / info / good), icon, title, text."""
    start, end = data.month_start(me), me
    out = []

    # --- новые контрагенты и сотрудники (первая операция в ДДС за всю историю)
    def new_parties():
        df = data.cf_first_seen()
        if df.empty:
            return
        # сотрудник — первая в истории выплата именно по подстатье «Заработная плата»
        sal = df[df["salary"]].groupby("cp").agg(first=("first", "min"),
                                                 amount=("amount", "sum")).reset_index()
        staff = sal[(sal["first"] >= start) & (sal["first"] <= end)
                    & (sal["cp"] != "Без контрагента")]
        # контрагент — первая в истории операция по любой другой подстатье
        oth = df[~df["salary"]].groupby("cp").agg(first=("first", "min"),
                                                  amount=("amount", "sum")).reset_index()
        firms = oth[(oth["first"] >= start) & (oth["first"] <= end)
                    & (oth["cp"] != "Без контрагента")
                    & ~oth["cp"].isin(sal["cp"])]
        if len(staff):
            out.append({"tone": "info", "icon": "solar:user-plus-linear",
                        "title": f"Новые сотрудники: {len(staff)}",
                        "text": "Первая выплата заработной платы в этом месяце:",
                        "items": staff.sort_values("first")["cp"].tolist()})
        if len(firms):
            top = firms.reindex(firms["amount"].abs().sort_values(ascending=False).index)
            out.append({"tone": "info", "icon": "solar:buildings-2-linear",
                        "title": f"Новые контрагенты: {len(firms)}",
                        "text": "Впервые появились в движении денег:",
                        "items": [f"{r.cp} — {money(r.amount)}" for r in top.itertuples()]})
    _safe(new_parties, None)

    # --- курсы валют
    def fx_alerts():
        df = data.fx(start - timedelta(days=5), end)
        if df.empty:
            return
        for cur in FX_CURRENCIES:
            r1, d1 = data.fx_at(df, cur, end)
            r0, _ = data.fx_at(df, cur, start - timedelta(days=1))
            if not r1 or not r0:
                continue
            ch = (r1 - r0) / r0 * 100
            if abs(ch) >= FX_ALERT_PCT:
                word = "вырос" if ch > 0 else "упал"
                out.append({"tone": "warn", "icon": "solar:dollar-minimalistic-linear",
                            "title": f"{cur} {word} на {pct(abs(ch))}",
                            "text": f"Курс {cur}: {num(r0, 4)} → {num(r1, 4)} ₽ за месяц "
                                    f"(на {fmt_date(d1)})."})
    _safe(fx_alerts, None)

    # --- займы с близким сроком погашения
    def loan_alerts():
        df = data.loans(end)
        if df.empty or "repayment_date" not in df:
            return
        today = min(date.today(), end)
        soon = df[df["repayment_date"].notna() & (df["total_debt"].abs() > 1)]
        soon = soon[(soon["repayment_date"].dt.date >= today)
                    & (soon["repayment_date"].dt.date <= today + timedelta(days=LOAN_DUE_DAYS))]
        for r in soon.sort_values("repayment_date").head(5).itertuples():
            side = "нам должны" if r.loan_direction == "issued" else "мы должны"
            out.append({"tone": "warn", "icon": "solar:calendar-mark-linear",
                        "title": f"Срок погашения {fmt_date(r.repayment_date)}",
                        "text": f"{r.counterparty_name}, договор {r.contract_number}: "
                                f"{money(r.total_debt)} ({side})."})
    _safe(loan_alerts, None)

    # --- проценты по займам: начислено за месяц и долг по процентам
    def interest_alerts():
        now = data.loans(min(end, date.today()))
        if now.empty or "interest_balance" not in now:
            return
        prev = data.loans(start - timedelta(days=1))
        now = now[now["loan_direction"] == "borrowed"]
        key = "contract_id"
        p_bal = dict(zip(prev[key], prev["interest_balance"])) if not prev.empty else {}
        has_acc = "total_interest_accrued" in now
        p_acc = (dict(zip(prev[key], prev["total_interest_accrued"]))
                 if has_acc and not prev.empty else {})
        rows = []
        for r in now.itertuples():
            bal = float(r.interest_balance or 0)
            grow = bal - float(p_bal.get(r.contract_id) or 0)
            acc = (float(r.total_interest_accrued or 0) - float(p_acc.get(r.contract_id) or 0)
                   if has_acc else None)
            if abs(bal) < 1 and abs(acc or 0) < 1:
                continue
            rows.append((r.counterparty_name or "—", acc, bal, grow))
        if not rows:
            return
        tot_bal = sum(x[2] for x in rows)
        tot_grow = sum(x[3] for x in rows)
        tot_acc = sum(x[1] or 0 for x in rows)
        by_cp = {}
        for cp, acc, bal, grow in rows:
            a = by_cp.setdefault(cp, [0.0, 0.0])
            a[0] += acc or 0
            a[1] += bal
        parts = [f"{cp} — начислено {money(a[0])}, долг по процентам {money(a[1])}"
                 for cp, a in sorted(by_cp.items(), key=lambda x: -x[1][1])]
        word = "вырос" if tot_grow >= 0 else "снизился"
        out.append({"tone": "warn" if tot_grow > 0 else "info",
                    "icon": "solar:graph-up-linear",
                    "title": f"Долг по процентам {word} на {money(abs(tot_grow))}",
                    "text": (f"За месяц начислено {money(tot_acc)} процентов по полученным "
                             f"займам, всего не уплачено {money(tot_bal)}." if has_acc else
                             f"Всего не уплачено процентов {money(tot_bal)}."),
                    "items": parts})
    _safe(interest_alerts, None)

    # --- договоры, срок которых заканчивается в этом месяце
    def contract_alerts():
        items = data.contracts_ending(start, data.month_end(end))
        if not items:
            return
        names = [f"{c['cp']} — {c['type']} № {c['number']}, до {fmt_date(c['date_end'])}"
                 for c in items]
        out.append({"tone": "warn", "icon": "solar:document-text-linear",
                    "title": f"Заканчиваются договоры: {len(items)}",
                    "text": "Срок действия истекает в этом месяце:",
                    "items": names})
    _safe(contract_alerts, None)

    # --- свежесть банковских данных (только для текущего месяца)
    def lag():
        if end < date.today() - timedelta(days=31):
            return
        _, _, last_bank = data.treasury(min(end, date.today()))
        if last_bank and (date.today() - last_bank).days > BANK_LAG_DAYS:
            out.append({"tone": "warn", "icon": "solar:clock-circle-linear",
                        "title": "Данные банка не обновлялись",
                        "text": f"Движения по счетам загружены по {fmt_date(last_bank)} — "
                                "остатки и ДДС могут быть неполными."})
    _safe(lag, None)

    if not out:
        out.append({"tone": "good", "icon": "solar:check-circle-linear",
                    "title": "Без особых событий",
                    "text": "Новых контрагентов, резких изменений курсов и близких сроков "
                            "погашения в этом месяце нет."})
    return out
