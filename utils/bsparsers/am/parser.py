"""
Разбор банковских выписок Армении.

Форматы:
  * AccountStatement.xlsx (Америабанк, Армбизнесбанк) — лист AccountStatementReport;
  * «Տեղեկանք» из системы «Банк-клиент» (АйДи, Ардшин, ВТБ-Армения) — XML Spreadsheet 2003 (.xls).

Результат — Statement: шапка (счёт, валюта, период, остатки) и операции.
Приход — dt, расход — cr (как в выписках РФ). Django не нужен.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

ZERO = Decimal("0.00")

BANK_CODES = {
    "103": "ЦБ АРМЕНИИ", "900": "ЦБ АРМЕНИИ", "115": "АРМБИЗНЕСБАНК", "118": "АЙДИ БАНК",
    "151": "АРАРАТБАНК", "157": "АМЕРИАБАНК", "160": "ВТБ-АРМЕНИЯ", "161": "ВТБ-АРМЕНИЯ",
    "163": "АРМЭКОНОМБАНК", "166": "ЭВОКАБАНК", "193": "КОНВЕРС БАНК", "205": "ИНЕКОБАНК",
    "214": "БИБЛОС БАНК", "217": "АРДШИНБАНК", "218": "АРДШИНБАНК", "247": "АРДШИНБАНК",
    "248": "АРДШИНБАНК", "220": "АКБА БАНК", "223": "АРЦАХБАНК", "241": "ЮНИБАНК",
}


class StatementError(ValueError):
    pass


@dataclass
class Row:
    date: date
    doc_number: str
    op_type: str
    dt: Decimal                 # приход
    cr: Decimal                 # расход
    cp_account: str
    cp_name: str
    purpose: str
    dt_eq: Decimal | None = None    # в AMD для валютных счетов, если банк дал эквивалент
    cr_eq: Decimal | None = None
    key: str = ""


@dataclass
class Statement:
    fmt: str
    bank: str | None
    account: str
    currency: str
    start: date
    finish: date
    bb: Decimal
    eb: Decimal
    rows: list[Row] = field(default_factory=list)
    owner_name: str = ""
    owner_tax_id: str = ""

    @property
    def total_dt(self) -> Decimal:
        return sum((r.dt for r in self.rows), ZERO)

    @property
    def total_cr(self) -> Decimal:
        return sum((r.cr for r in self.rows), ZERO)

    @property
    def balance_gap(self) -> Decimal:
        """Расхождение: вход + приход − расход − исход. Должно быть 0."""
        return self.bb + self.total_dt - self.total_cr - self.eb


# ============================================================
# Хелперы
# ============================================================

def money(text) -> Decimal:
    if text is None:
        return ZERO
    if isinstance(text, (int, float, Decimal)):
        return Decimal(str(text)).quantize(Decimal("0.01"))
    s = re.sub(r"[^\d.\-]", "", str(text).replace(",", ""))
    if s in ("", "-", "."):
        return ZERO
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise StatementError(f"не сумма: {text!r}") from exc


def to_date(text) -> date | None:
    if text is None:
        return None
    if isinstance(text, date):
        return text
    m = re.match(r"\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", str(text))
    if not m:
        return None
    d, mth, y = (int(x) for x in m.groups())
    if y < 100:
        y += 2000
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def clean(text) -> str:
    return " ".join(str(text or "").replace("\xa0", " ").split())


def bank_by_account(account: str) -> str | None:
    return BANK_CODES.get((account or "")[:3])


def make_keys(account: str, rows: list[Row]) -> None:
    """Ключ операции по содержимому. Одинаковые строки внутри файла различаются порядковым номером."""
    seen: dict[str, int] = {}
    for r in rows:
        base = "|".join([account, r.date.isoformat(), r.doc_number, r.op_type, str(r.dt), str(r.cr),
                         r.cp_account, r.purpose])
        n = seen.get(base, 0)
        seen[base] = n + 1
        r.key = hashlib.sha1(f"{base}|{n}".encode("utf-8")).hexdigest()


# ============================================================
# Формат 1: AccountStatement.xlsx
# ============================================================

def parse_ameria(path: Path) -> Statement:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    head: dict[str, list] = {}
    header_idx = None
    data = []
    for row in ws.iter_rows(values_only=True):
        cells = list(row)
        first = clean(cells[0]) if cells else ""
        if header_idx is None:
            if first == "Ամսաթիվ":
                header_idx = [clean(c) for c in cells]
                continue
            if first:
                head[first] = [c for c in cells[1:] if c not in (None, "")]
            continue
        if to_date(cells[0]) is None:
            continue                                   # итоги и пустые строки
        data.append(cells)
    wb.close()

    def h(prefix):
        for k, v in head.items():
            if k.startswith(prefix):
                return v
        raise StatementError(f"в шапке нет «{prefix}»")

    account = re.sub(r"\D", "", str(h("Հաշիվ N")[0]))
    acc_row = h("Հաշիվ N")
    st = Statement(
        fmt="ameria", bank=bank_by_account(account), account=account,
        currency=clean(h("Արժույթ")[0]).upper(),
        start=to_date(h("Ժամանակահատվածի սկիզբ")[0]), finish=to_date(h("Ժամանակահատվածի վերջ")[0]),
        bb=money(h("Սկզբնական մնացորդ")[0]), eb=money(h("Վերջնական մնացորդ")[0]),
        owner_name=clean(acc_row[1]) if len(acc_row) > 1 else "",
        owner_tax_id=re.sub(r"\D", "", clean(head.get("ՀՎՀՀ", [""])[0]))[-8:],      # 1200532316 → 00532316
    )
    if header_idx is None:
        raise StatementError("не найдена строка заголовков операций")
    col = {name: i for i, name in enumerate(header_idx)}
    need = ["Ամսաթիվ", "Փաստ.N", "ԳՏ", "Հաշիվ", "Նպատակ", "Մուտք", "Ելք", "Վճարող/Շահառու"]
    missing = [n for n in need if n not in col]
    if missing:
        raise StatementError(f"нет колонок: {missing}")
    g = lambda cells, n: cells[col[n]] if col[n] < len(cells) else None
    for cells in data:
        st.rows.append(Row(
            date=to_date(g(cells, "Ամսաթիվ")), doc_number=clean(g(cells, "Փաստ.N")),
            op_type=clean(g(cells, "ԳՏ")), dt=money(g(cells, "Մուտք")), cr=money(g(cells, "Ելք")),
            cp_account=clean(g(cells, "Հաշիվ")), cp_name=clean(g(cells, "Վճարող/Շահառու")),
            purpose=clean(g(cells, "Նպատակ")),
        ))
    # контроль с итогами банка
    tot_cr, tot_dt = head.get("Ընդհանուր շարժ դեբետով"), head.get("Ընդհանուր շարժ կրեդիտով")
    if tot_cr and money(tot_cr[0]) != st.total_cr:
        raise StatementError(f"расход по строкам {st.total_cr} ≠ итог банка {money(tot_cr[0])}")
    if tot_dt and money(tot_dt[0]) != st.total_dt:
        raise StatementError(f"приход по строкам {st.total_dt} ≠ итог банка {money(tot_dt[0])}")
    return st


# ============================================================
# Формат 2: «Банк-клиент» (XML Spreadsheet 2003)
# ============================================================

def _spreadsheetml(path: Path) -> list[list[str]]:
    from xml.etree import ElementTree as ET

    ns = "{urn:schemas-microsoft-com:office:spreadsheet}"
    rows = []
    for _, el in ET.iterparse(path):
        if el.tag != f"{ns}Row":
            continue
        cells, pos = [], 0
        for c in el.findall(f"{ns}Cell"):
            idx = c.get(f"{ns}Index")
            if idx:
                while pos < int(idx) - 1:
                    cells.append("")
                    pos += 1
            d = c.find(f"{ns}Data")
            cells.append(clean("".join(d.itertext())) if d is not None else "")
            pos += 1
        rows.append(cells)
        el.clear()
    return rows


def parse_bank_client(path: Path) -> Statement:
    rows = _spreadsheetml(path)
    header_at = next((i for i, r in enumerate(rows) if "Փաստաթղթի համար" in r), None)
    if header_at is None:
        raise StatementError("не найдена строка заголовков операций")
    shift = rows[header_at].index("Փաստաթղթի համար")      # пустые колонки слева
    rows = [r[shift:] for r in rows]
    head = [[c for c in r if c] for r in rows[:header_at]]   # в шапке — только непустые ячейки

    bank_name = account = currency = ""
    start = finish = None
    bb = eb = None
    owner = ""
    for r in head:
        first = r[0] if r else ""
        m = re.search(r"(\d{2}/\d{2}/\d{2,4})\s*-\s*(\d{2}/\d{2}/\d{2,4})", first)
        if m and start is None:
            start, finish = to_date(m.group(1)), to_date(m.group(2))
        if first.startswith("Բանկ:"):
            bank_name = first
        if first.startswith("Հաճախորդ:"):
            owner = clean(first.split(":", 1)[1])
        if first.startswith("Հաշվի համարը:"):
            m = re.search(r"(\d{10,20})\s*([A-Z]{3})?", first)
            if m:
                account, currency = m.group(1), m.group(2) or ""
        if first.startswith("Սկզբնական մնացորդ") and len(r) > 1:
            bb = money(r[1].split()[0])
        if first.startswith("Վերջնական մնացորդ") and len(r) > 1:
            eb = money(r[1].split()[0])
    if not account or start is None or bb is None or eb is None:
        raise StatementError("в шапке нет счёта, периода или остатков")

    hdr = rows[header_at]
    # две колонки «Համարժեք»: первая — к дебету, вторая — к кредиту
    idx = {}
    for i, name in enumerate(hdr):
        if name == "Համարժեք":
            idx["eq_cr" if "eq_cr" not in idx else "eq_dt"] = i
        else:
            idx.setdefault(name, i)
    need = ["Համար", "Ամսաթիվ", "Դեբետ", "Կրեդիտ", "Շահառուի/վճարողի հաշիվ", "Շահառու/վճարող", "Նպատակը", "Տիպ"]
    missing = [n for n in need if n not in idx]
    if missing:
        raise StatementError(f"нет колонок: {missing}")

    st = Statement(fmt="bank_client", bank=bank_by_account(account), account=account,
                   currency=currency, start=start, finish=finish, bb=bb, eb=eb,
                   owner_name=re.sub(r"\d+$", "", owner).strip(), owner_tax_id=(re.search(r"(\d{8})$", owner) or [None, ""])[1])
    g = lambda r, n: r[idx[n]] if idx[n] < len(r) else ""
    foreign = currency and currency != "AMD"
    for r in rows[header_at + 1:]:
        if not r or to_date(g(r, "Ամսաթիվ")) is None or r[0].startswith("("):
            continue
        dt, cr = money(g(r, "Կրեդիտ")), money(g(r, "Դեբետ"))
        st.rows.append(Row(
            date=to_date(g(r, "Ամսաթիվ")),
            doc_number=g(r, "Փաստաթղթի համար") or g(r, "Համար"),
            op_type=g(r, "Տիպ"), dt=dt, cr=cr,
            cp_account=g(r, "Շահառուի/վճարողի հաշիվ"), cp_name=g(r, "Շահառու/վճարող").lstrip("*").strip(),
            purpose=g(r, "Նպատակը"),
            dt_eq=money(r[idx["eq_dt"]]) if foreign and "eq_dt" in idx and idx["eq_dt"] < len(r) else None,
            cr_eq=money(r[idx["eq_cr"]]) if foreign and "eq_cr" in idx and idx["eq_cr"] < len(r) else None,
        ))
    return st


# ============================================================
# Вход
# ============================================================

def parse_statement(path: str | Path) -> Statement:
    path = Path(path)
    head = path.read_bytes()[:2000]
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        st = parse_ameria(path)
    elif b"<?xml" in head or b"<Workbook" in head:
        st = parse_bank_client(path)
    else:
        raise StatementError("неизвестный формат выписки")
    make_keys(st.account, st.rows)
    return st
