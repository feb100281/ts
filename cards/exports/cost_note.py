"""Справка по себестоимости УПД: бренды, каналы, наценка к закупочной цене, пробелы в разметке."""
from __future__ import annotations

import io
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from openpyxl import Workbook

from treasury import xlsx_style as X

CH = {"wb": "ВБ", "retail": "Розница", "none": "Не распределено"}
CH_ORDER = ("wb", "retail", "none")


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def _r2(v) -> Decimal:
    return _d(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _new():
    return {"rows": 0, "qty": Decimal(0), "base": Decimal(0), "base_priced": Decimal(0),
            "cost": Decimal(0), "no_cost": 0, "below": 0, "no_nm": 0, "no_chrt": 0,
            "ch": defaultdict(Decimal)}


def collect(docs) -> list[dict]:
    """По каждой УПД: итог и разрез по брендам и бренд × канал."""
    out = []
    for doc in docs:
        default = doc.default_channel or "wb"
        total, brands, cross = _new(), defaultdict(_new), defaultdict(_new)
        for l in doc.income_lines.all():
            ch = l.channel or default
            b = (l.brand or "").strip() or "Без бренда"
            qty, base = _d(l.upd_qty), _d(l.upd_amount_vatless)
            for a in (total, brands[b], cross[(b, ch)]):
                a["rows"] += 1
                a["qty"] += qty
                a["base"] += base
                a["ch"][ch] += qty
                a["no_nm"] += l.nm_id is None
                a["no_chrt"] += l.chrt_id is None
                if l.man_cost_per_unit is None:
                    a["no_cost"] += 1
                else:
                    a["cost"] += _r2(l.man_cost_per_unit) * qty
                    a["base_priced"] += base
                    a["below"] += _r2(l.man_cost_per_unit) < _r2(l.upd_price_vatless)
        out.append({"doc": doc, "total": total, "brands": dict(brands), "cross": dict(cross)})
    return out


def markup(a):
    return float(a["cost"] / a["base_priced"] - 1) if a["base_priced"] else None


def _m(v) -> str:
    return f"{v:,.2f}".replace(",", " ") + " ₽"


def _q(v) -> str:
    return f"{v:,.0f}".replace(",", " ")


def _p(v) -> str:
    return "—" if v is None else f"{v * 100:+.1f}%"


def _lines(item) -> list[str]:
    doc, t = item["doc"], item["total"]
    cp = str(doc.counterparty or "—").split(" (ИНН:")[0]
    L = [f"УПД № {doc.number} от {doc.date:%d.%m.%Y} · {cp}:",
         f"  Позиций {t['rows']}, штук {_q(t['qty'])}. Закупочная без НДС {_m(t['base'])}.",
         (f"  Управленческая себестоимость {_m(t['cost'])}, наценка к закупочной {_p(markup(t))}"
          + (f" (по заполненным строкам; не заполнено {t['no_cost']})" if t["no_cost"] else "") + "."),
         "  Каналы: " + " · ".join(f"{CH[c]} {_q(t['ch'][c])} шт" for c in CH_ORDER if t["ch"].get(c)) + "."]
    if t["below"]:
        L.append(f"  ⚠ Себестоимость ниже закупочной в {t['below']} строках — проверить распределение расходов.")
    gaps = []
    if t["no_nm"]:
        gaps.append(f"без карточки WB {t['no_nm']}")
    if t["no_chrt"]:
        gaps.append(f"без размера WB {t['no_chrt']}")
    if gaps:
        L.append("  Разметка: " + ", ".join(gaps) + " строк.")
    L.append("")
    L.append("  По брендам:")
    for b, a in sorted(item["brands"].items(), key=lambda x: -x[1]["base"]):
        ch = ", ".join(f"{CH[c]} {_q(a['ch'][c])}" for c in CH_ORDER if a["ch"].get(c))
        warn = f"; ниже закупочной {a['below']} из {a['rows']}" if a["below"] else ""
        empty = f"; без себестоимости {a['no_cost']}" if a["no_cost"] else ""
        L.append(f"  • {b}: {_q(a['qty'])} шт ({ch}); закупочная {_m(a['base'])}, "
                 f"себестоимость {_m(a['cost'])}, наценка {_p(markup(a))}{warn}{empty}.")
    L.append("")
    return L


def build_workbook(docs) -> bytes:
    items = collect(docs)
    wb = Workbook()
    ws = wb.active
    ws.title = "Справка"
    lines = ["Наценка = управленческая себестоимость / закупочная цена без НДС − 1, "
             "по строкам с заполненной себестоимостью. На склад WB идут только строки канала «ВБ».", ""]
    for it in items:
        lines += _lines(it)
    X.cover(ws, "Справка по себестоимости УПД",
            f"УПД: {len(items)}", lines, link_sheet="Бренд × канал")

    t = wb.create_sheet("Бренд × канал")
    rows = []
    for it in items:
        d = it["doc"]
        for (b, c), a in sorted(it["cross"].items(), key=lambda x: (x[0][0], CH_ORDER.index(x[0][1]))):
            mk = markup(a)
            rows.append([d.number, d.date, b, CH[c], a["rows"], float(a["qty"]), float(a["base"]),
                         float(a["cost"]), mk, a["below"], a["no_cost"], a["no_nm"], a["no_chrt"]])
    X.table(t, ["УПД", "Дата", "Бренд", "Канал", "Строк", "Кол-во", "Закупочная без НДС",
                "Упр. себестоимость", "Наценка", "Ниже закупочной, строк", "Без себестоимости, строк",
                "Без карточки WB", "Без размера WB"],
            rows, [12, 12, 18, 18, 9, 11, 18, 18, 11, 13, 13, 12, 12],
            money=(7, 8), dates=(2,))
    for r in range(2, len(rows) + 2):
        t.cell(row=r, column=6).number_format = "#,##0"
        t.cell(row=r, column=9).number_format = "+0.0%;-0.0%;0.0%"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
