"""Неразнесённые операции зарубежной компании: список и текст запроса на уточнение."""
from collections import defaultdict
from io import BytesIO

from django.db.models import Q

from treasury.models import CfData


def _f(d):
    return d.strftime("%d.%m.%Y") if d else ""


def _money(x):
    return f"{x:,.2f}".replace(",", " ")


def pending(owner, date_from=None, date_to=None):
    """Операции без договора или без статьи, сгруппированные по счёту и названию контрагента."""
    qs = (CfData.objects.filter(owner=owner).filter(Q(contract__isnull=True) | Q(cfitem__isnull=True))
          .select_related("ba", "ba__bank", "contract", "contract__cp").order_by("date", "id"))
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    groups = defaultdict(lambda: {"ops": [], "dt": 0, "cr": 0, "cur": set()})
    for o in qs:
        acc = (o.payer_account if (o.dt or 0) > 0 else o.reciver_account) or ""
        name = o.cp_name_ru or o.cp_bs_name or ""
        g = groups[(acc, name)]
        g.update(account=acc, name=name, name_src=o.cp_bs_name or "")
        g["ops"].append(o)
        g["dt"] += o.dt or 0
        g["cr"] += o.cr or 0
        g["cur"].add(o.ba.currency if o.ba else "")
    out = sorted(groups.values(), key=lambda g: -(g["dt"] + g["cr"]))
    for g in out:
        g["cur"] = ", ".join(sorted(c for c in g["cur"] if c))
        g["no_contract"] = any(o.contract_id is None for o in g["ops"])
    return out


def request_text(owner, groups):
    L = ["Коллеги, добрый день!", "",
         f"Прошу пояснить назначение платежей {owner.name}: за что платёж или поступление "
         f"(товар, аренда, услуги, заём, налог и т.п.) и по какому договору.", ""]
    for n, g in enumerate(groups, 1):
        head = g["name"] or "Контрагент не указан"
        if g["name_src"] and g["name_src"] != g["name"]:
            head += f" ({g['name_src']})"
        if g["account"]:
            head += f", счёт {g['account']}"
        tot = []
        if g["dt"]:
            tot.append(f"поступления {_money(g['dt'])}")
        if g["cr"]:
            tot.append(f"списания {_money(g['cr'])}")
        L.append(f"{n}. {head} — операций: {len(g['ops'])}; {', '.join(tot)} {g['cur']}")
        for o in g["ops"][:12]:
            amt = f"+{_money(o.dt)}" if (o.dt or 0) > 0 else f"−{_money(o.cr or 0)}"
            bank = f"{o.ba.bank.name if o.ba and o.ba.bank else ''} {o.ba.account if o.ba else ''}".strip()
            L.append(f"   • {_f(o.date)}  {amt} {o.ba.currency if o.ba else ''}  ({bank})")
            if o.temp:
                L.append(f"     назначение: {o.temp}")
            if o.temp_ru and o.temp_ru != o.temp:
                L.append(f"     перевод: {o.temp_ru}")
        if len(g["ops"]) > 12:
            L.append(f"   … и ещё {len(g['ops']) - 12} операций (полный список во вложении)")
        L.append("")
    L.append("Спасибо!")
    return "\n".join(L)


def to_xlsx(owner, groups) -> bytes:
    from datetime import date
    from openpyxl import Workbook
    from treasury.xlsx_style import cover, table

    wb = Workbook()
    ws = wb.active
    ws.title = "Запрос"
    total = sum(len(g["ops"]) for g in groups)
    lines = ["Коллеги, добрый день!", "",
             f"По {owner.name} есть платежи, назначение которых нам непонятно — всего {total} "
             f"в {len(groups)} группах (группа — один контрагент).", "",
             "Просим на листе «Платежи» заполнить жёлтые колонки:",
             "   • «Что за платёж / услуга» — товар, аренда, услуги (какие), заём, налог, возврат и т.п.;",
             "   • «Договор / счёт» — номер и дата договора или счёта, если есть.",
             "Если пояснение одно на всю группу, достаточно заполнить первую строку группы.", "",
             "Группы:"]
    for n, g in enumerate(groups, 1):
        tot = []
        if g["dt"]:
            tot.append(f"поступления {_money(g['dt'])}")
        if g["cr"]:
            tot.append(f"списания {_money(g['cr'])}")
        lines.append(f"   {n}. {g['name'] or 'Контрагент не указан'}"
                     f"{', счёт ' + g['account'] if g['account'] else ''} — операций {len(g['ops'])}; "
                     f"{', '.join(tot)} {g['cur']}")
    lines += ["", "Спасибо!"]
    cover(ws, "Уточнение платежей", f"{owner.name} · сформировано {date.today():%d.%m.%Y}", lines,
          link_sheet="Платежи", link_text="→ Таблица для заполнения — на листе «Платежи»")

    rows = []
    for n, g in enumerate(groups, 1):
        for o in g["ops"]:
            rows.append([n, g["name"], g["name_src"], g["account"], o.date,
                         o.ba.bank.name if o.ba and o.ba.bank else "", o.ba.account if o.ba else "",
                         o.ba.currency if o.ba else "", float(o.dt or 0) or None, float(o.cr or 0) or None,
                         o.temp or "", o.temp_ru or "", "", ""])
    table(wb.create_sheet("Платежи"),
          ["Группа", "Контрагент", "Название в выписке", "Счёт контрагента", "Дата", "Банк", "Наш счёт",
           "Валюта", "Поступление", "Списание", "Назначение (оригинал)", "Назначение (перевод)",
           "Что за платёж / услуга", "Договор / счёт (№, дата)"],
          rows, [9, 30, 30, 22, 11, 15, 20, 7, 14, 14, 45, 45, 40, 26],
          money=(9, 10), dates=(5,), wrap=(2, 3, 11, 12, 13, 14), inputs=(13, 14), freeze="C2")
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
