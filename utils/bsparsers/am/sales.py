"""
Разбор выгрузки продаж и возвратов из 1С (Армения): листы «продажи» и «возвраты».

Без Django. Возвраты хранятся с положительными суммами и видом «return»;
в отчётах они вычитаются в месяце возврата.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ZERO = Decimal("0")
VAT_AM = Decimal("0.20")

SALE_COLS = {
    "doc_number": "Номер чека", "doc_date": "Дата продажи", "article_invoice": "Артикул инвойс",
    "article": "Артикул", "size": "Размер", "barcode": "Штрихкод товара", "name": "Наименование",
    "qty": "Количество", "disc_manual_pct": "Ручная скидка процент", "disc_manual_sum": "Ручная скидка сумма",
    "bonus_sum": "Сумма бонусных баллов к списанию", "price": "Цена единицы", "cost_unit": "Себестоимость единицы",
    "amount": "Сумма", "cost_total": "Себестоимость итого", "amount_novat": "Сумма без НДС",
    "disc_auto_pct": "Авто скидка процент", "disc_auto_sum": "Авто скидка сумма",
}
RETURN_COLS = {
    "check_number": "Номер чека ККМ", "check_date": "Дата чека ККМ", "doc_number": "Номер возврата",
    "doc_date": "Дата возврата", "article_invoice": "Артикул инвойс В", "article": "Артикул В",
    "size": "Размер В", "barcode": "Штрихкод товара В", "name": "Наименование В", "qty": "Количество В",
    "price": "Цена единицы В", "amount": "Сумма В", "cost_unit": "Себестоимость единицы В",
    "cost_total": "Себестоимость итого В",
}
MONEY = {"disc_manual_sum", "bonus_sum", "price", "cost_unit", "amount", "cost_total", "amount_novat",
         "disc_auto_sum"}
NUMS = {"qty", "disc_manual_pct", "disc_auto_pct"}


class SalesError(ValueError):
    pass


@dataclass
class SaleRow:
    kind: str                                   # sale | return
    doc_number: str
    doc_date: datetime
    article_invoice: str = ""
    article: str = ""
    size: str = ""
    barcode: str = ""
    name: str = ""
    qty: Decimal = ZERO
    price: Decimal = ZERO
    amount: Decimal = ZERO                      # с НДС
    amount_novat: Decimal = ZERO
    cost_unit: Decimal = ZERO
    cost_total: Decimal = ZERO
    disc_manual_pct: Decimal = ZERO
    disc_manual_sum: Decimal = ZERO
    disc_auto_pct: Decimal = ZERO
    disc_auto_sum: Decimal = ZERO
    bonus_sum: Decimal = ZERO
    check_number: str = ""
    check_date: datetime | None = None
    key: str = ""


@dataclass
class SalesFile:
    rows: list[SaleRow] = field(default_factory=list)

    def months(self) -> set[date]:
        return {date(r.doc_date.year, r.doc_date.month, 1) for r in self.rows}

    def total(self, kind: str, attr: str) -> Decimal:
        return sum((getattr(r, attr) for r in self.rows if r.kind == kind), ZERO)


def _dt(v) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise SalesError(f"не дата: {v!r}")


def _num(v, money: bool) -> Decimal:
    if v is None or v == "":
        return ZERO
    d = Decimal(str(v).replace(" ", "").replace(",", "."))
    return d.quantize(Decimal("0.01"), ROUND_HALF_UP) if money else d


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return " ".join(str(v).replace("\xa0", " ").split())


def _sheet(wb, name):
    for ws in wb.worksheets:
        if ws.title.strip().casefold() == name:
            return ws
    return None


def _read(ws, cols: dict, kind: str) -> list[SaleRow]:
    it = ws.iter_rows(values_only=True)
    header = [_text(c) for c in next(it, [])]
    idx = {}
    for attr, title in cols.items():
        if title not in header:
            raise SalesError(f"лист «{ws.title}»: нет колонки «{title}»")
        idx[attr] = header.index(title)
    out = []
    for r in it:
        if not r or not any(c not in (None, "") for c in r[:4]):
            continue
        vals = {}
        for attr, i in idx.items():
            v = r[i] if i < len(r) else None
            if attr in ("doc_date", "check_date"):
                vals[attr] = _dt(v)
            elif attr in MONEY:
                vals[attr] = _num(v, True)
            elif attr in NUMS:
                vals[attr] = _num(v, False)
            else:
                vals[attr] = _text(v)
        if not vals.get("doc_number") or vals.get("doc_date") is None:
            continue
        row = SaleRow(kind=kind, **vals)
        if kind == "return":                    # в возвратах 1С нет суммы без НДС
            row.amount_novat = (row.amount / (1 + VAT_AM)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        out.append(row)
    return out


def _keys(rows: list[SaleRow]) -> None:
    """Ключ строки по содержимому; одинаковые строки одного чека различаются порядковым номером."""
    seen: dict[str, int] = {}
    for r in rows:
        base = "|".join([r.kind, r.doc_number, r.doc_date.isoformat(), r.barcode, r.article, r.size,
                         str(r.qty), str(r.amount), str(r.cost_total)])
        n = seen.get(base, 0)
        seen[base] = n + 1
        r.key = hashlib.sha1(f"{base}|{n}".encode("utf-8")).hexdigest()


def is_sales_file(path) -> bool:
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            wb = z.read("xl/workbook.xml").decode("utf-8", "ignore").casefold()
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
    return 'name="продажи"' in wb


def parse_sales(path) -> SalesFile:
    import openpyxl

    wb = openpyxl.load_workbook(Path(path), read_only=True, data_only=True)
    sales, returns = _sheet(wb, "продажи"), _sheet(wb, "возвраты")
    if sales is None:
        raise SalesError("нет листа «продажи»")
    f = SalesFile(rows=_read(sales, SALE_COLS, "sale") + (_read(returns, RETURN_COLS, "return") if returns else []))
    wb.close()
    _keys(f.rows)
    return f
