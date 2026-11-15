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
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Уточнить"
    head = ["№ группы", "Контрагент", "Название в выписке", "Счёт контрагента", "Дата", "Банк", "Наш счёт",
            "Валюта", "Поступление", "Списание", "Назначение (оригинал)", "Назначение (перевод)", "Пояснение"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E293B")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for n, g in enumerate(groups, 1):
        for o in g["ops"]:
            ws.append([n, g["name"], g["name_src"], g["account"], o.date,
                       o.ba.bank.name if o.ba and o.ba.bank else "", o.ba.account if o.ba else "",
                       o.ba.currency if o.ba else "", float(o.dt or 0) or None, float(o.cr or 0) or None,
                       o.temp or "", o.temp_ru or "", ""])
    widths = [8, 32, 32, 22, 11, 16, 20, 7, 14, 14, 50, 50, 40]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        row[4].number_format = "DD.MM.YYYY"
        for c in (row[8], row[9]):
            c.number_format = "# ##0.00"
        for c in (row[10], row[11]):
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
