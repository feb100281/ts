"""
Разноска операций зарубежной компании — правила без Django (проверяются отдельно).

Порядок для каждой операции (разнесённые руками и со сплитами не трогаются):
  1. Контрагент — по счёту из выписки (справочник «Счета контрагентов»), иначе по ИНН в названии.
     Транзитные и корреспондентские счета банков контрагента не определяют.
  2. Договор и статья:
     — счёт привязан к договору → этот договор; статья — первое подходящее правило контрагента
       для этого договора, иначе автоматизация договора;
     — контрагент найден → правила его резолвера сверху вниз, первое подходящее
       (правило без статьи для направления операции пропускается);
     — контрагент не найден и ИНН в названии нет → общие правила компании.
  3. Контрагент финальный — контрагент договора.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CORR = re.compile(r"30[12]\d{17}")          # корреспондентские счета банков
INN = re.compile(r"(?:INN|ИНН)[ .:]*(\d{12}|\d{10})(?!\d)", re.I)


def is_transit(account: str | None, transit=frozenset()) -> bool:
    a = (account or "").removeprefix("SELF:")
    return a in transit or bool(CORR.fullmatch(a))


def inn_of(name: str | None) -> str | None:
    m = INN.search(name or "")
    return m.group(1) if m else None


@dataclass
class Rule:
    id: int
    regex: str
    contract: int
    item_dt: int | None
    item_cr: int | None
    _rx: re.Pattern | None = None

    def matches(self, text: str) -> bool:
        if not self.regex:
            return True
        if self._rx is None:
            try:
                self._rx = re.compile(self.regex, re.I)
            except re.error:                             # RegEx с ошибкой — строка не срабатывает
                self._rx = re.compile(r"(?!)")
        return bool(self._rx.search(text))

    def item(self, incoming: bool) -> int | None:
        return self.item_dt if incoming else self.item_cr


@dataclass
class Result:
    cp: int | None
    cp_final: int | None
    contract: int | None
    cfitem: int | None
    rule: int | None
    how: str


def resolve_one(op: dict, links: dict, inn_cps: dict, rules: dict, contracts: dict, auto: dict,
                transit=frozenset()) -> Result:
    """op: owner, dt, payer_account, reciver_account, ba_account, temp, temp_ru, cp_bs_name.
    links: счёт → (контрагент, договор|None); inn_cps: ИНН → контрагент;
    rules: (компания, контрагент|None) → [Rule]; contracts: договор → (контрагент, компания);
    auto: договор → (статья Дт, статья Кт) из автоматизации."""
    incoming = (op.get("dt") or 0) > 0
    acc = op.get("payer_account") if incoming else op.get("reciver_account")
    key = ("SELF:" + acc) if acc and acc == op.get("ba_account") else acc
    owner = op["owner"]
    text = f'{op.get("temp") or ""}\n{op.get("temp_ru") or ""}'

    cp = bound = None
    how = ""
    if key and not is_transit(key, transit) and key in links:
        cp, bound = links[key]
        how = "счёт"
    if cp is None:                       # счёт получателя в назначении (платёж через банк-посредник)
        up = (op.get("temp") or "").upper()
        for a, (c, b) in links.items():
            if len(a) >= 12 and not a.startswith("SELF:") and not is_transit(a, transit) and a in up:
                cp, bound, how = c, b, "счёт в назначении"
                break
    inn = inn_of(op.get("cp_bs_name"))
    if cp is None and inn and inn in inn_cps:
        cp, how = inn_cps[inn], "ИНН"

    if bound and contracts.get(bound, (None, None))[1] == owner:
        for r in rules.get((owner, ("bound", bound)), []):
            if r.contract == bound and r.item(incoming) and r.matches(text):
                return Result(cp, contracts[bound][0], bound, r.item(incoming), r.id, how + ", договор по счёту")
        dt_item, cr_item = auto.get(bound, (None, None))
        return Result(cp, contracts[bound][0], bound, dt_item if incoming else cr_item, None,
                      how + ", договор по счёту")

    if cp is not None:
        pool = rules.get((owner, cp), [])
    elif not inn:
        pool, how = rules.get((owner, None), []), "без контрагента"
    else:
        pool = []                        # ИНН есть, контрагента с ним нет — заведите контрагента
    for r in pool:
        if r.item(incoming) and r.matches(text):
            return Result(cp, contracts.get(r.contract, (cp, None))[0], r.contract, r.item(incoming), r.id,
                          how + ", RegEx договора")
    return Result(cp, cp, None, None, None, how or "не найден")
