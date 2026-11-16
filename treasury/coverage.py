"""Контроль полноты банковских выписок компании и текст запроса недостающего."""
import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from corporate.models import BankAccount
from treasury.models import BankStatements, CfData

DAY = timedelta(days=1)
OWN_NAME = re.compile(r"трендсеттер|trendsetter|տրենդսետտեր", re.I)
OWN_TRANSFER = re.compile(r"սեփական միջոց|իմ հաշիվների|sobstvennyh|собственных средств", re.I)
TRANSIT = re.compile(r"swift transfer|տարանցիկ|transit", re.I)          # служебные счета банков
CORR = re.compile(r"\d[\d ]{12,20}\d")                                    # номер счёта внутри реквизитов


def period_end(today: date) -> date:
    """Последний закрытый месяц."""
    return today.replace(day=1) - DAY


def fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def gaps(start: date, end: date, covered) -> list:
    """Непокрытые выписками отрезки [start; end]."""
    out, cur = [], start
    for s, f in sorted(covered):
        if f < cur:
            continue
        if s > cur:
            out.append((cur, min(s - DAY, end)))
        cur = max(cur, f + DAY)
        if cur > end:
            break
    if cur <= end:
        out.append((cur, end))
    return [g for g in out if g[0] <= g[1]]


def _bank(ba) -> str:
    return getattr(ba.bank, "name", "") or (ba.bs_acc.name.split()[0] if ba.bs_acc else "Банк")


def check(owner, today: date | None = None) -> dict:
    today = today or date.today()
    end = period_end(today)
    start = owner.activity_start
    accounts = list(BankAccount.objects.filter(corporate=owner).select_related("bank", "bs_acc")
                    .order_by("bank__name", "currency", "account"))
    turns = {r["bs"]: r for r in CfData.objects.filter(owner=owner).values("bs")
             .annotate(dt=Sum("dt"), cr=Sum("cr"))}

    rows, ask, refetch = [], defaultdict(list), defaultdict(list)
    for ba in accounts:
        st = list(BankStatements.objects.filter(ba=ba).order_by("start", "finish"))
        st = [s for s in st if s.start and s.finish]
        issues = []
        first = st[0].start if st else None
        frm = start or first
        last_eb = st[-1].eb if st else None
        if not st:
            issues.append(("нет выписок", f"с {fmt(frm)} по {fmt(end)}" if frm else "за весь период работы"))
            ask[_bank(ba)].append((ba, [(frm, end)] if frm else None))
        else:
            miss = gaps(frm, end, [(s.start, s.finish) for s in st])
            for a, b in miss:
                issues.append(("нет выписки", f"{fmt(a)} – {fmt(b)}"))
            if miss:
                ask[_bank(ba)].append((ba, miss))
            prev = None
            for s in st:
                per = f"{fmt(s.start)} – {fmt(s.finish)}"
                if s.bb is None or s.eb is None:
                    issues.append(("в файле нет остатков", per))
                    refetch[_bank(ba)].append((ba, s, "нет входящего или исходящего остатка"))
                else:
                    t = turns.get(s.pk)
                    if t:
                        diff = (s.bb + (t["dt"] or 0) - (t["cr"] or 0)) - s.eb
                        if abs(diff) > Decimal("0.01"):
                            issues.append(("обороты не сходятся с остатками", f"{per}: разница {diff:,.2f}"))
                            refetch[_bank(ba)].append((ba, s, f"обороты не сходятся с остатками на {diff:,.2f}"))
                if prev:
                    if s.start <= prev.finish:
                        issues.append(("периоды выписок перекрываются",
                                       f"{fmt(prev.start)}–{fmt(prev.finish)} и {per}"))
                    elif s.start == prev.finish + DAY and None not in (prev.eb, s.bb) and prev.eb != s.bb:
                        issues.append(("остатки не стыкуются",
                                       f"исход {fmt(prev.finish)} {prev.eb:,.2f} ≠ вход {fmt(s.start)} {s.bb:,.2f}"))
                prev = s
        if ba.is_active is False and last_eb not in (None, 0):
            issues.append(("счёт закрыт, но остаток не нулевой", f"{last_eb:,.2f} — нужна выписка до закрытия"))
        rows.append({"ba": ba, "bank": _bank(ba), "count": len(st),
                     "first": first, "last": st[-1].finish if st else None,
                     "eb": last_eb, "issues": issues})

    unknown = _unknown_accounts(owner, {a.account for a in BankAccount.objects.all()})
    return {"owner": owner, "start": start, "end": end, "rows": rows, "unknown": unknown,
            "text": _request(owner, start, end, ask, refetch, unknown),
            "ok": all(not r["issues"] for r in rows) and not unknown}


def _unknown_accounts(owner, ours: set) -> list:
    """Счета в выписках, похожие на счета самой компании, по которым выписок нет."""
    found = {}
    rows = CfData.objects.filter(owner=owner).values_list(
        "date", "dt", "cr", "payer_account", "reciver_account", "cp_bs_name", "temp")
    for d, dt, cr, payer, recv, name, temp in rows:
        acc = payer if (dt or 0) > 0 else recv
        if not acc or acc in ours or TRANSIT.search(name or ""):
            continue
        if not (OWN_NAME.search(name or "") or OWN_TRANSFER.search(temp or "")):
            continue
        if acc.startswith("301"):                                  # корсчёт банка РФ — берём счёт из реквизитов
            real = [x.replace(" ", "") for x in CORR.findall(name or "")]
            real = [x for x in real if 14 <= len(x) <= 16 and x not in ours]
            if not real:
                continue
            acc, name = real[0], f"{name} (через корсчёт {acc})"
        x = found.setdefault(acc, {"account": acc, "name": name or "", "count": 0, "first": d, "last": d,
                                   "sample": (temp or "")[:90]})
        x["count"] += 1
        x["first"] = min(x["first"], d) if d else x["first"]
        x["last"] = max(x["last"], d) if d else x["last"]
    return sorted(found.values(), key=lambda x: -x["count"])


def _request(owner, start, end, ask, refetch, unknown) -> str:
    L = [f"Коллеги, добрый день!", "",
         f"Для управленческого учёта {owner.name} прошу прислать банковские выписки "
         f"(Excel из интернет-банка, за любой период, обязательно с входящим и исходящим остатком):", ""]
    for bank in sorted(ask):
        L.append(bank)
        for ba, per in ask[bank]:
            p = "; ".join(f"{fmt(a)} – {fmt(b)}" for a, b in per) if per else "за весь период работы счёта"
            L.append(f"  • счёт {ba.account} ({ba.currency}): {p}")
        L.append("")
    if refetch:
        L.append("Прошу выгрузить заново (в присланных файлах ошибка):")
        for bank in sorted(refetch):
            for ba, s, why in refetch[bank]:
                L.append(f"  • {bank}, счёт {ba.account} ({ba.currency}), {fmt(s.start)} – {fmt(s.finish)}: {why}")
        L.append("")
    if unknown:
        L.append("В выписках встречаются счета, похожие на счета компании, по которым выписок нет. "
                 "Прошу подтвердить, наши ли это счета, и прислать выписки по ним:")
        for u in unknown:
            L.append(f"  • {u['account']} — {u['name'] or 'без названия'} (операций: {u['count']}, "
                     f"{fmt(u['first'])} – {fmt(u['last'])})")
        L.append("")
    since = fmt(start) if start else "даты открытия"
    L += [f"И выписки по всем остальным счетам компании во всех банках и валютах — открытым, закрытым, "
          f"депозитным и карточным — с {since} по {fmt(end)}, а также список всех счетов компании "
          f"с датами открытия и закрытия (справка из банков или из налоговой).", "", "Спасибо!"]
    return "\n".join(L)


def to_xlsx(data) -> bytes:
    from io import BytesIO
    from openpyxl import Workbook
    from treasury.xlsx_style import cover, table

    wb = Workbook()
    ws = wb.active
    ws.title = "Запрос"
    owner = data["owner"]
    per = f"проверка с {fmt(data['start'])}" if data["start"] else "проверка с первой выписки"
    cover(ws, "Запрос банковских выписок", f"{owner.name} · {per} по {fmt(data['end'])} · "
          f"сформировано {date.today():%d.%m.%Y}", data["text"].split("\n"),
          link_sheet="Счета", link_text="→ Подробности по каждому счёту — на листе «Счета»")

    rows = [[r["bank"], r["ba"].account, r["ba"].currency,
             "закрыт" if r["ba"].is_active is False else "действующий", r["count"], r["first"], r["last"],
             float(r["eb"]) if r["eb"] is not None else None,
             "\n".join(f"{k}: {v}" for k, v in r["issues"]) or "в порядке"] for r in data["rows"]]
    table(wb.create_sheet("Счета"),
          ["Банк", "Счёт", "Валюта", "Статус", "Выписок", "Первая с", "Последняя по", "Исходящий остаток",
           "Замечания"], rows, [18, 24, 8, 13, 9, 12, 13, 18, 70],
          money=(8,), dates=(6, 7), wrap=(9,), freeze="C2")
    if data["unknown"]:
        rows = [[u["account"], u["name"], u["count"], u["first"], u["last"], u["sample"], ""] for u in data["unknown"]]
        table(wb.create_sheet("Возможные счета"),
              ["Счёт", "Название в выписке", "Операций", "С", "По", "Пример назначения", "Наш ли это счёт?"],
              rows, [26, 40, 10, 12, 12, 60, 30], dates=(4, 5), wrap=(2, 6, 7), inputs=(7,), freeze="B2")
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
