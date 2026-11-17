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
@page {
  size: A4; margin: 18mm 16mm 20mm;
  @bottom-left { content: "Справка по себестоимости УПД"; font: 7.5pt 'DejaVu Sans', Arial, sans-serif; color: #777; }
  @bottom-right { content: "Стр. " counter(page) " из " counter(pages); font: 7.5pt 'DejaVu Sans', Arial, sans-serif; color: #777; }
}
body { font-family: 'DejaVu Sans', Arial, sans-serif; color: #222; font-size: 9pt; line-height: 1.35; }
.top { border-bottom: .6mm solid #1f3d34; padding-bottom: 2mm; margin-bottom: 5mm; }
.top .org { font-size: 8pt; letter-spacing: .6pt; text-transform: uppercase; color: #555; }
.top h1 { font-size: 14pt; font-weight: bold; margin: 1mm 0 0; color: #111; }
.top .meta { font-size: 8pt; color: #555; margin-top: 1mm; }
.doc + .doc { page-break-before: always; }
h2 { font-size: 10.5pt; margin: 0 0 2mm; color: #111; }
h3 { font-size: 8.5pt; text-transform: uppercase; letter-spacing: .5pt; color: #1f3d34;
     margin: 5mm 0 1.5mm; border-bottom: .2mm solid #1f3d34; padding-bottom: .8mm; }
table { width: 100%; border-collapse: collapse; }
table.req td { padding: .8mm 0; vertical-align: top; }
table.req td.k { width: 42mm; color: #555; }
table.sum td, table.sum th, table.t td, table.t th { padding: 1.4mm 2mm; border-bottom: .2mm solid #cfcfcf; }
table.sum th, table.t th { font-weight: bold; font-size: 8pt; color: #333; text-align: right;
     border-top: .4mm solid #1f3d34; border-bottom: .4mm solid #1f3d34; background: #f3f5f4; }
table.sum th:first-child, table.t th:first-child { text-align: left; }
table.sum td { text-align: right; white-space: nowrap; }
table.sum td:first-child { text-align: left; color: #333; }
table.sum tr.k td { font-weight: bold; border-top: .4mm solid #1f3d34; }
table.t td { text-align: right; white-space: nowrap; }
table.t td:first-child { text-align: left; }
table.t tr.b td { font-weight: bold; }
table.t tr.c td:first-child { padding-left: 6mm; color: #444; }
table.t tr.k td { font-weight: bold; border-top: .4mm solid #1f3d34; border-bottom: .4mm solid #1f3d34; }
.neg { color: #a31515; }
table.bar { table-layout: fixed; margin: 1mm 0 2.5mm; }
table.bar td { height: 7mm; padding: 0; color: #fff; font-size: 8pt; font-weight: bold;
     text-align: center; white-space: nowrap; overflow: hidden; border-right: .5mm solid #fff; }
table.bar td:last-child { border-right: 0; }
.wb { background: #1f3d34; } .retail { background: #5e8f80; } .none { background: #b9bdbb; color: #333 !important; }
.sw { display: inline-block; width: 3mm; height: 3mm; margin-right: 2mm; vertical-align: -.4mm; }
ol.notes { margin: 0; padding-left: 5mm; }
ol.notes li { margin-bottom: 1.2mm; }
.muted { color: #666; font-size: 8pt; }
.sign { margin-top: 10mm; font-size: 8.5pt; }
.sign td { padding-top: 6mm; }
.sign .line { border-bottom: .2mm solid #333; width: 55mm; }
"""


def _esc(s) -> str:
    import html
    return html.escape(str(s))


def _r(v) -> str:
    return f"{v:,.2f}".replace(",", " ").replace(".", ",")


def _pc(v) -> str:
    return "—" if v is None else f"{v * 100:+.1f}%".replace(".", ",")


def _neg(v) -> str:
    return ' class="neg"' if v is not None and v < 0 else ""


def _share(a, b) -> str:
    return f"{float(a / b * 100):.1f}%".replace(".", ",") if b else "—"


def _row(cls, name, a):
    m = markup(a)
    return (f'<tr class="{cls}"><td>{_esc(name)}</td><td>{_q(a["qty"])}</td><td>{_r(a["base"])}</td>'
            f'<td>{_r(a["cost"])}</td><td>{_r(a["cost"] - a["base_priced"])}</td>'
            f'<td{_neg(m)}>{_pc(m)}</td><td>{a["below"] or "—"}</td></tr>')


def _doc_html(it) -> str:
    doc, t = it["doc"], it["total"]
    cp = str(doc.counterparty or "—").split(" (ИНН:")[0]
    mk = markup(t)
    contract = getattr(doc, "contract", None)

    present = [c for c in CH_ORDER if t["ch"].get(c)]
    ch_rows = "".join(
        f'<tr><td><span class="sw {c}"></span>{CH[c]}</td><td>{_q(t["ch"][c])}</td>'
        f'<td>{_share(t["ch"][c], t["qty"])}</td></tr>' for c in present)
    qty = t["qty"] or Decimal(1)
    bar = "".join(
        f'<td class="{c}" style="width:{max(float(t["ch"][c] / qty * 100), 1.5):.2f}%">'
        f'{_share(t["ch"][c], t["qty"]) if t["ch"][c] / qty >= Decimal("0.06") else ""}</td>'
        for c in present)

    notes = []
    if t["below"]:
        notes.append(f"Управленческая себестоимость ниже закупочной цены в {t['below']} строках из {t['rows']}. "
                     "Требуется проверка распределения дополнительных расходов по позициям.")
    if t["ch"].get("none"):
        notes.append(f"Канал продаж не определён для {_q(t['ch']['none'])} шт. "
                     "Позиции не включаются в складской учёт WB до определения канала.")
    if t["no_cost"]:
        notes.append(f"Управленческая себестоимость не указана в {t['no_cost']} строках; "
                     "наценка рассчитана по строкам с заполненной себестоимостью.")
    if t["no_nm"] or t["no_chrt"]:
        parts = [f"без карточки WB — {t['no_nm']}" if t["no_nm"] else "",
                 f"без размера WB — {t['no_chrt']}" if t["no_chrt"] else ""]
        notes.append("Не завершено сопоставление с номенклатурой WB: " + ", ".join(p for p in parts if p) + " строк.")
    notes_html = ("<ol class='notes'>" + "".join(f"<li>{n}</li>" for n in notes) + "</ol>"
                  if notes else "<div>Замечаний нет.</div>")

    rows = []
    for b, a in sorted(it["brands"].items(), key=lambda x: -x[1]["base"]):
        rows.append(_row("b", b, a))
        for c in CH_ORDER:
            if (b, c) in it["cross"]:
                rows.append(_row("c", CH[c], it["cross"][(b, c)]))
    rows.append(_row("k", "Итого", t))

    return f"""
<div class="doc">
  <h2>УПД № {_esc(doc.number)} от {doc.date:%d.%m.%Y}</h2>
  <table class="req">
    <tr><td class="k">Поставщик</td><td>{_esc(cp)}</td></tr>
    {f'<tr><td class="k">Договор</td><td>{_esc(contract)}</td></tr>' if contract else ''}
    <tr><td class="k">Количество позиций</td><td>{t["rows"]}</td></tr>
  </table>

  <h3>1. Основные показатели</h3>
  <table class="sum">
    <tr><th>Показатель</th><th>Значение</th></tr>
    <tr><td>Количество, шт.</td><td>{_q(t["qty"])}</td></tr>
    <tr><td>Закупочная стоимость без НДС, руб.</td><td>{_r(t["base"])}</td></tr>
    <tr><td>Управленческая себестоимость, руб.</td><td>{_r(t["cost"])}</td></tr>
    <tr><td>Отклонение от закупочной стоимости, руб.</td><td>{_r(t["cost"] - t["base_priced"])}</td></tr>
    <tr class="k"><td>Наценка к закупочной стоимости</td><td{_neg(mk)}>{_pc(mk)}</td></tr>
  </table>

  <h3>2. Распределение по каналам продаж</h3>
  <table class="bar"><tr>{bar}</tr></table>
  <table class="sum">
    <tr><th>Канал</th><th>Количество, шт.</th><th>Доля</th></tr>
    {ch_rows}
  </table>

  <h3>3. Себестоимость в разрезе брендов и каналов, руб.</h3>
  <table class="t">
    <tr><th>Бренд / канал</th><th>Кол-во, шт.</th><th>Закупочная</th><th>Себестоимость</th>
        <th>Отклонение</th><th>Наценка</th><th>Ниже закуп., строк</th></tr>
    {''.join(rows)}
  </table>

  <h3>4. Замечания</h3>
  {notes_html}
</div>"""


def build_html(docs) -> str:
    from datetime import datetime
    items = collect(docs)
    body = "".join(_doc_html(it) for it in items)
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="top">
  <div class="org">ООО «Трендсеттер» · управленческий учёт</div>
  <h1>Справка по управленческой себестоимости поступлений</h1>
  <div class="meta">Дата формирования: {datetime.now():%d.%m.%Y %H:%M} · Документов: {len(items)}</div>
</div>
{body}
<p class="muted" style="margin-top:6mm">Методика: наценка = управленческая себестоимость / закупочная стоимость
без НДС − 1, по строкам с заполненной себестоимостью. Себестоимость единицы округляется до копеек.
В складской учёт WB включаются только позиции канала «ВБ».</p>
<table class="sign"><tr><td style="width:45mm">Подготовил(а)</td><td class="line"></td>
<td style="width:10mm"></td><td style="width:20mm">Дата</td><td class="line" style="width:35mm"></td></tr></table>
</body></html>"""


def build_pdf(docs) -> bytes:
    from weasyprint import HTML
    return HTML(string=build_html(docs)).write_pdf()
