# gear/app/daily_sales/assistant/counterparties.py
"""Справка по контрагентам и договорам (только чтение, через модели Django).

Персональные данные не передаются: для ИП и физлиц (ИНН из 12 цифр) имя и ИНН
маскируются; ФИО руководителей, телефоны, e-mail и адреса не выводятся никогда.
"""
from __future__ import annotations

from django.db.models import Q

MAX_CP = 10
MAX_CONTRACTS = 25


def _is_person(cp) -> bool:
    inn = (cp.tax_id or "").strip()
    return len(inn) == 12 and inn.isdigit()


def _cp_name(cp) -> str:
    if _is_person(cp):
        return f"ИП/физлицо (ИНН …{cp.tax_id[-4:]})"
    return cp.name


def _risks(cp) -> str:
    flags = [
        ("risk_sanctions", "санкции"),
        ("risk_sanctioned_founder", "санкции у учредителя"),
        ("risk_illegal_fin", "нелегальная фин. деятельность"),
        ("risk_disq_persons", "дисквалифицированные лица"),
        ("risk_mass_directors", "массовый руководитель"),
        ("risk_mass_founders", "массовый учредитель"),
    ]
    hit = [t for f, t in flags if getattr(cp, f, None)]
    return ", ".join(hit) if hit else "не отмечены"


def _contract_line(c) -> str:
    parts = [
        getattr(c.title, "title", "") or "Договор",
        f"№ {c.number}" if c.number else "без номера",
        f"от {c.date:%d.%m.%Y}" if c.date else "",
        f"компания: {getattr(c.owner, 'name', '')}",
        f"валюта: {c.currency}" if getattr(c, "currency", None) else "",
        "подписан" if c.is_signed else "не подписан",
    ]
    if getattr(c, "subconto_pl", None):
        parts.append(f"статья: {c.subconto_pl.name}")
    if getattr(c, "pid_id", None):
        parts.append("(доп. соглашение)")
    if getattr(c, "is_active", None) is False:
        parts.append("неактивен")
    items = [i.item for i in c.contractitems_set.all()[:3] if i.item]
    if items:
        parts.append("предмет: " + "; ".join(x[:120] for x in items))
    return " · ".join(p for p in parts if p)


def counterparty_info(query: str) -> str:
    from counterparties.models import Counterparty
    from contracts.models import Contracts

    q = (query or "").strip()
    if len(q) < 2:
        return "Укажи название, часть названия или ИНН контрагента."
    flt = Q(name__icontains=q) | Q(fullname__icontains=q)
    if q.isdigit():
        flt |= Q(tax_id=q)
    cps = list(Counterparty.objects.filter(flt).select_related("gr")[:MAX_CP + 1])
    if not cps:
        return f"Контрагент «{q}» не найден."

    out = []
    if len(cps) > MAX_CP:
        out.append(f"Найдено больше {MAX_CP} — показаны первые; уточни запрос.")
    for cp in cps[:MAX_CP]:
        person = _is_person(cp)
        head = [
            f"КОНТРАГЕНТ: {_cp_name(cp)}",
            f"ИНН: {'скрыт' if person else cp.tax_id}",
            f"ОПФ: {cp.okopf_name}" if cp.okopf_name and not person else "",
            f"группа: {cp.gr.name}" if cp.gr_id else "",
            f"ОКВЭД: {cp.okved_code} {cp.okved_name or ''}".strip() if cp.okved_code else "",
            f"регион: {cp.region}" if cp.region and not person else "",
            f"страна: {cp.country}" if cp.country and cp.country != "RU" else "",
            f"налоговый режим: {cp.taxregime}" if cp.taxregime else "",
            f"риски: {_risks(cp)}",
        ]
        out.append(" | ".join(h for h in head if h))
        contracts = (Contracts.objects.filter(cp=cp)
                     .select_related("title", "owner", "subconto_pl")
                     .prefetch_related("contractitems_set")
                     .order_by("-date")[:MAX_CONTRACTS + 1])
        cl = list(contracts)
        if not cl:
            out.append("  договоров нет")
        for c in cl[:MAX_CONTRACTS]:
            out.append("  - " + _contract_line(c))
        if len(cl) > MAX_CONTRACTS:
            out.append(f"  …показаны последние {MAX_CONTRACTS} договоров")
    return "\n".join(out)
