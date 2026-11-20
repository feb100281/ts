"""Реестры зарплаты (PDF из 1С «Список перечисляемой в банк зарплаты») → сплиты банковских оплат.

Оплата «СОТРУДНИК (РЕЕСТР)» одной суммой раскладывается по сотрудникам: сплит на каждого,
договор сотрудника, статья CF оплаты (обычно 124100). Несколько оплат одного дня с суммой,
равной итогу реестра, — одна ведомость. Нового сотрудника заводим, только если его нет
ни по лицевому счёту, ни по ФИО.
"""
from __future__ import annotations

import io
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from itertools import combinations

from django.db import transaction

from contracts.models import CfItemAuto, Contracts
from counterparties.models import Counterparty
from treasury.models import CfData, CfSplits, CounterpartyAccount

LOOKAHEAD = 5                     # дней после даты реестра, в которые ищем оплату
ROW = re.compile(r"^\s*(\d{1,4})\s+(40817\d{15})\s*(.+?)\s+(\d{1,3}(?:[  ]\d{3})*,\d{2})\s*$")
HEAD = re.compile(r"№\s*(\S+)\s+от\s+(\d{2})\.(\d{2})\.(\d{4})")
TOTAL = re.compile(r"^\s*Итого\s+(\d{1,3}(?:[  ]\d{3})*,\d{2})\s*$", re.M)


def money(s: str) -> Decimal:
    return Decimal(s.replace(" ", "").replace(" ", "").replace(",", "."))


def norm(name: str) -> str:
    return " ".join((name or "").upper().replace("Ё", "Е").split())


# ---------- чтение PDF ----------

def pdf_text(data: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except ImportError:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True,
                                  text=True, timeout=60).stdout


@dataclass
class Registry:
    name: str
    number: str = ""
    date: date | None = None
    total: Decimal = Decimal(0)
    rows: list = field(default_factory=list)          # [(лицевой счёт, ФИО, сумма)]
    error: str = ""


def parse(name: str, data: bytes) -> Registry:
    reg = Registry(name)
    text = pdf_text(data)
    m = HEAD.search(text)
    if not m:
        reg.error = "не похоже на реестр зарплаты: нет «№ … от …»"
        return reg
    reg.number, reg.date = m.group(1), date(int(m.group(4)), int(m.group(3)), int(m.group(2)))
    last = None
    for line in text.splitlines():
        r = ROW.match(line)
        if r:
            last = [r.group(2), r.group(3).strip(), money(r.group(4))]
            reg.rows.append(last)
        elif last and re.fullmatch(r"[А-ЯЁа-яё\- ]+", line.strip()) and not line.strip().startswith("Итого"):
            last[1] += " " + line.strip()                   # перенос ФИО на вторую строку
            last = None
        else:
            last = None
    reg.rows = [(a, norm(n), s) for a, n, s in reg.rows]
    t = TOTAL.search(text)
    reg.total = money(t.group(1)) if t else sum((s for *_, s in reg.rows), Decimal(0))
    if sum((s for *_, s in reg.rows), Decimal(0)) != reg.total:
        reg.error = f"сумма строк {sum(s for *_, s in reg.rows)} ≠ итог реестра {reg.total}"
    elif not reg.rows:
        reg.error = "в реестре не найдены строки сотрудников"
    return reg


# ---------- оплаты ----------

def registry_contracts():
    return Contracts.objects.filter(cp__name__icontains="РЕЕСТР", title__title__icontains="трудов")


def find_payments(reg: Registry, used: set[int]):
    """Оплаты по договору реестра без сплитов, сумма которых равна итогу реестра."""
    qs = (CfData.objects.filter(contract__in=registry_contracts(), cr__gt=0,
                                date__gte=reg.date, date__lte=reg.date + timedelta(days=LOOKAHEAD))
          .exclude(id__in=used).filter(splits__isnull=True).order_by("date", "id"))
    cand = list(qs)
    stamp = f"{reg.date:%d.%m.%Y}"
    # сначала оплаты, где в назначении дата реестра
    cand.sort(key=lambda c: (stamp not in (c.temp or ""), c.date, c.id))
    for k in range(1, min(len(cand), 6) + 1):
        for combo in combinations(cand, k):
            if len({(c.owner_id, c.date) for c in combo}) == 1 and sum(c.cr for c in combo) == reg.total:
                return list(combo)
    return []


def partition(rows: list, payments: list) -> list[list] | None:
    """Разложить строки реестра по оплатам так, чтобы суммы совпали до копейки."""
    left = list(range(len(rows)))
    out = []
    for pay in payments[:-1]:
        target = int(pay.cr * 100)
        reach = {0: None}                                 # сумма → (предыдущая сумма, индекс строки)
        for i in left:
            v = int(rows[i][2] * 100)
            for s in list(reach):
                if s + v <= target and s + v not in reach:
                    reach[s + v] = (s, i)
            if target in reach:
                break
        if target not in reach:
            return None
        pick, s = [], target
        while s:
            s, i = reach[s]
            pick.append(i)
        out.append(sorted(pick))
        left = [i for i in left if i not in pick]
    out.append(left)
    return [[rows[i] for i in grp] for grp in out]


# ---------- сотрудники ----------

def staff_contract(owner_id: int, cp) -> Contracts | None:
    return (Contracts.objects.filter(owner_id=owner_id, cp=cp, title__title__icontains="трудов")
            .order_by("-id").first())


def template(owner_id: int) -> Contracts | None:
    base = Contracts.objects.filter(owner_id=owner_id, title__title__icontains="трудов")
    return (base.exclude(cp__name__icontains="РЕЕСТР").order_by("-id").first()
            or base.order_by("-id").first())


def find_staff(owner_id: int, acc: str, name: str):
    """(контрагент, договор, как найден) или (None, None, причина)."""
    ca = CounterpartyAccount.objects.filter(account=acc).select_related("cp").first()
    if ca:
        return ca.cp, staff_contract(owner_id, ca.cp), "по счёту"
    hits = [cp for cp in Counterparty.objects.filter(name__iexact=name)] or \
           [cp for cp in Counterparty.objects.filter(name__icontains=name.split()[0]) if norm(cp.name) == name]
    if len(hits) > 1:
        with_contract = [cp for cp in hits if staff_contract(owner_id, cp)]
        hits = with_contract if len(with_contract) == 1 else hits
    if len(hits) == 1:
        return hits[0], staff_contract(owner_id, hits[0]), "по ФИО"
    if len(hits) > 1:
        return None, None, f"несколько контрагентов «{name}»"
    return None, None, "новый"


def copy_contract(tpl: Contracts, cp) -> Contracts:
    autos = list(CfItemAuto.objects.filter(contract=tpl))
    c = Contracts.objects.get(pk=tpl.pk)
    c.pk = c.id = None
    c.cp = cp
    c.regex = None
    c.number = None
    c.date = None
    c.save()
    CfItemAuto.objects.bulk_create([CfItemAuto(contract=c, regex=a.regex, defaultcfdt=a.defaultcfdt,
                                               defaultcfcr=a.defaultcfcr) for a in autos])
    return c


# ---------- план и проводка ----------

def plan(regs: list[Registry]) -> list[dict]:
    """Без записи в базу: что с чем сойдётся и кого придётся завести."""
    used, out = set(), []
    for reg in regs:
        item = {"reg": reg, "payments": [], "groups": [], "staff": [], "error": reg.error}
        if not reg.error:
            pays = find_payments(reg, used)
            if not pays:
                item["error"] = (f"нет оплаты «СОТРУДНИК (РЕЕСТР)» на {reg.total:,.2f} "
                                 f"с {reg.date:%d.%m.%Y} по {reg.date + timedelta(days=LOOKAHEAD):%d.%m.%Y}"
                                 ).replace(",", " ")
            else:
                groups = partition(reg.rows, pays)
                if groups is None:
                    item["error"] = "строки реестра не раскладываются по оплатам до копейки"
                else:
                    used |= {p.id for p in pays}
                    owner_id = pays[0].owner_id
                    item.update(payments=pays, groups=groups)
                    for acc, name, amount in reg.rows:
                        cp, contract, how = find_staff(owner_id, acc, name)
                        item["staff"].append({"acc": acc, "name": name, "amount": amount, "cp": cp,
                                              "contract": contract, "how": how})
                    if any(s["how"].startswith("несколько") for s in item["staff"]):
                        item["error"] = "есть сотрудники с несколькими совпадениями по ФИО — уточните"
                    elif template(owner_id) is None and any(s["contract"] is None for s in item["staff"]):
                        item["error"] = "нет трудового договора-образца у компании"
        out.append(item)
    return out


def apply(items: list[dict]) -> dict:
    """Сплиты по сотрудникам; новые сотрудники и договоры — только для отсутствующих."""
    res = {"registries": 0, "splits": 0, "new_staff": [], "new_contracts": []}
    with transaction.atomic():
        for it in items:
            if it["error"]:
                continue
            reg, pays = it["reg"], it["payments"]
            owner_id = pays[0].owner_id
            tpl = template(owner_id)
            staff = {}
            for s in it["staff"]:
                cp, contract = s["cp"], s["contract"]
                if cp is None:
                    cp = Counterparty.objects.create(tax_id=f"FL-{s['acc']}", name=s["name"])
                    res["new_staff"].append(s["name"])
                CounterpartyAccount.objects.get_or_create(account=s["acc"], defaults={"cp": cp, "comment": "зарплата"})
                if contract is None:
                    contract = copy_contract(tpl, cp)
                    if s["cp"] is not None:
                        res["new_contracts"].append(s["name"])
                staff[(s["acc"], s["name"])] = contract
            for pay, rows in zip(pays, it["groups"]):
                CfSplits.objects.bulk_create([
                    CfSplits(transaction=pay, cr=amount, contract=staff[(acc, name)], cfitem=pay.cfitem,
                             temp=f"Реестр № {reg.number} от {reg.date:%d.%m.%Y} · {name}")
                    for acc, name, amount in rows])
                res["splits"] += len(rows)
            res["registries"] += 1
    return res
