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


# --- PDF ---

CSS = """
@page { size: A4; margin: 14mm 12mm; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; color: #1f1f1f; font-size: 10pt; }
h1 { font-size: 17pt; color: #2F6656; margin: 0 0 2mm; }
.sub { color: #666; font-size: 9pt; margin-bottom: 5mm; }
.doc { page-break-inside: avoid; margin-bottom: 8mm; }
.doc + .doc { page-break-before: always; }
.head { background: #2F6656; color: #fff; padding: 3mm 4mm; border-radius: 2mm; }
.head b { font-size: 13pt; }
.head span { float: right; font-size: 10pt; margin-top: 1mm; }
.kpi { width: 100%; border-collapse: separate; border-spacing: 2mm; margin: 2mm -2mm; }
.kpi td { background: #E7F1ED; border-radius: 2mm; padding: 3mm; width: 25%; vertical-align: top; }
.kpi .l { color: #555; font-size: 8pt; text-transform: uppercase; letter-spacing: .3pt; }
.kpi .v { font-size: 13pt; font-weight: bold; margin-top: 1mm; white-space: nowrap; }
.kpi .n { color: #666; font-size: 8pt; }
.pos { color: #2e7d32; } .neg { color: #c62828; }
table.bar { width: 100%; border-collapse: collapse; table-layout: fixed; margin: 2mm 0 1mm; }
table.bar td { height: 6mm; color: #fff; font-size: 7.5pt; text-align: center; white-space: nowrap; overflow: hidden; padding: 0; }
.wb { background: #7B2CBF; } .retail { background: #2F6656; } .none { background: #B0A06A; }
.legend { font-size: 8.5pt; color: #444; margin-bottom: 3mm; }
.legend i { display: inline-block; width: 3mm; height: 3mm; border-radius: .7mm; margin: 0 1mm 0 3mm; vertical-align: -.3mm; }
.warn { background: #FDECEC; border-left: 1.2mm solid #c62828; padding: 2.5mm 3mm; margin: 2mm 0; font-size: 9.5pt; }
.info { background: #FFF8E1; border-left: 1.2mm solid #B8860B; padding: 2.5mm 3mm; margin: 2mm 0; font-size: 9.5pt; }
table.t { width: 100%; border-collapse: collapse; margin-top: 3mm; font-size: 9pt; }
table.t th { background: #2F6656; color: #fff; font-weight: normal; padding: 1.8mm 2mm; text-align: right; }
table.t th:first-child, table.t td:first-child { text-align: left; }
table.t td { padding: 1.6mm 2mm; border-bottom: .2mm solid #ddd; text-align: right; white-space: nowrap; }
table.t tr.brand td { background: #E7F1ED; font-weight: bold; border-top: .4mm solid #2F6656; }
table.t tr.ch td:first-child { padding-left: 6mm; color: #444; }
table.t tr.total td { background: #DCECE6; font-weight: bold; border-top: .5mm solid #2F6656; }
.foot { color: #777; font-size: 8pt; margin-top: 4mm; }
"""


def _esc(s) -> str:
    import html
    return html.escape(str(s))


def _cls(v):
    return "" if v is None else ("neg" if v < 0 else "pos")


def _r(v) -> str:
    """Рубли без копеек — для плиток и таблицы справки."""
    return f"{v:,.0f}".replace(",", " ") + " ₽"


def _doc_html(it) -> str:
    doc, t = it["doc"], it["total"]
    cp = str(doc.counterparty or "—").split(" (ИНН:")[0]
    mk = markup(t)
    qty = t["qty"] or Decimal(1)
    seg = "".join(
        f'<td class="{c}" style="width:{float(t["ch"][c] / qty * 100):.2f}%">'
        f'{CH[c] if t["ch"][c] / qty > Decimal("0.12") else ""} {float(t["ch"][c] / qty * 100):.0f}%</td>'
        for c in CH_ORDER if t["ch"].get(c))
    legend = "".join(f'<i class="{c}"></i>{CH[c]} — {_q(t["ch"][c])} шт'
                     for c in CH_ORDER if t["ch"].get(c))
    alerts = []
    if t["below"]:
        alerts.append(f'<div class="warn"><b>Себестоимость ниже закупочной в {t["below"]} строках.</b> '
                      'Управленческая себестоимость обычно не ниже цены УПД — проверить распределение расходов.</div>')
    if t["no_cost"]:
        alerts.append(f'<div class="info">Себестоимость не заполнена в {t["no_cost"]} строках — '
                      'наценка посчитана по заполненным.</div>')
    if t["ch"].get("none"):
        alerts.append(f'<div class="info">Канал не распределён: {_q(t["ch"]["none"])} шт — '
                      'на склад WB не попадают, пока не отмечены «ВБ».</div>')
    gaps = [f"без карточки WB — {t['no_nm']}" if t["no_nm"] else "",
            f"без размера WB — {t['no_chrt']}" if t["no_chrt"] else ""]
    gaps = [g for g in gaps if g]
    if gaps:
        alerts.append(f'<div class="info">Разметка строк: {", ".join(gaps)}.</div>')

    rows = []
    for b, a in sorted(it["brands"].items(), key=lambda x: -x[1]["base"]):
        m = markup(a)
        rows.append(
            f'<tr class="brand"><td>{_esc(b)}</td><td>{_q(a["qty"])}</td><td>{_r(a["base"])}</td>'
            f'<td>{_r(a["cost"])}</td><td class="{_cls(m)}">{_p(m)}</td>'
            f'<td>{a["below"] or ""}</td><td>{a["no_cost"] or ""}</td></tr>')
        for c in CH_ORDER:
            x = it["cross"].get((b, c))
            if not x:
                continue
            m = markup(x)
            rows.append(
                f'<tr class="ch"><td>{CH[c]}</td><td>{_q(x["qty"])}</td><td>{_r(x["base"])}</td>'
                f'<td>{_r(x["cost"])}</td><td class="{_cls(m)}">{_p(m)}</td>'
                f'<td>{x["below"] or ""}</td><td>{x["no_cost"] or ""}</td></tr>')
    rows.append(
        f'<tr class="total"><td>Итого</td><td>{_q(t["qty"])}</td><td>{_r(t["base"])}</td>'
        f'<td>{_r(t["cost"])}</td><td class="{_cls(mk)}">{_p(mk)}</td>'
        f'<td>{t["below"] or ""}</td><td>{t["no_cost"] or ""}</td></tr>')

    return f"""
<div class="doc">
  <div class="head"><b>УПД № {_esc(doc.number)} от {doc.date:%d.%m.%Y}</b><span>{_esc(cp)}</span></div>
  <table class="kpi"><tr>
    <td><div class="l">Закупочная без НДС</div><div class="v">{_r(t["base"])}</div>
        <div class="n">точно: {_m(t["base"])}</div></td>
    <td><div class="l">Упр. себестоимость</div><div class="v">{_r(t["cost"])}</div>
        <div class="n">точно: {_m(t["cost"])}</div></td>
    <td><div class="l">Наценка к закупочной</div><div class="v {_cls(mk)}">{_p(mk)}</div>
        <div class="n">{_r(t["cost"] - t["base_priced"])}</div></td>
    <td><div class="l">Количество</div><div class="v">{_q(t["qty"])} шт</div>
        <div class="n">ниже закупочной: {t["below"]} строк</div></td>
  </tr></table>
  <table class="bar"><tr>{seg}</tr></table>
  <div class="legend">{legend}</div>
  {''.join(alerts)}
  <table class="t">
    <tr><th>Бренд / канал</th><th>Штук</th><th>Закупочная</th><th>Себестоимость</th>
        <th>Наценка</th><th>Ниже закуп., строк</th><th>Без с/с, строк</th></tr>
    {''.join(rows)}
  </table>
</div>"""


def build_html(docs) -> str:
    from datetime import datetime
    items = collect(docs)
    body = "".join(_doc_html(it) for it in items)
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><h1>Справка по себестоимости УПД</h1>
<div class="sub">Сформировано {datetime.now():%d.%m.%Y %H:%M} · УПД: {len(items)} ·
наценка = упр. себестоимость / закупочная без НДС − 1 · на склад WB идут только строки «ВБ»</div>
{body}
<div class="foot">Себестоимость округлена до копеек за единицу — как в базе и в карточке УПД.</div>
</body></html>"""


def build_pdf(docs) -> bytes:
    from weasyprint import HTML
    return HTML(string=build_html(docs)).write_pdf()
