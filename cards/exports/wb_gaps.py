# cards/exports/wb_gaps.py
"""Excel: строки канала «ВБ» без карточки WB или без размера — для разметки УПД."""
from __future__ import annotations

from datetime import date
from io import BytesIO
import re

from django.db.models import Q

from cards.models import UpdDocument, UPDData, WbProduct, WbSizes


def _wb_lines(doc_ids):
    return (UPDData.objects
            .filter(upd_document_id__in=doc_ids)
            .filter(Q(channel='wb') | (Q(channel__isnull=True) & Q(upd_document__default_channel='wb'))))


def build_wb_gaps_xlsx(doc_ids) -> tuple[bytes, str]:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from gear.management.commands import mp
    from gear.app.daily_sales.assistant.excel import _write_table

    docs = {d.id: d for d in UpdDocument.objects.filter(id__in=doc_ids).select_related('counterparty')}
    wb_lines = _wb_lines(doc_ids)
    gaps = list(wb_lines.filter(Q(nm__isnull=True) | Q(chrt__isnull=True))
                .order_by('upd_document__date', 'upd_document_id', 'upd_pos')
                .values('upd_document_id', 'upd_pos', 'brand', 'upd_title', 'upd_sa_name',
                        'upd_size', 'upd_qty', 'upd_price_vatless', 'nm_id', 'chrt_id'))

    # подсказки: карточка с точно таким артикулом и размеры карточки
    sas = {(g['upd_sa_name'] or '').strip().upper() for g in gaps if g['nm_id'] is None}
    by_sa = {}
    for r in WbProduct.objects.exclude(sa_name__isnull=True).values('card_id', 'sa_name'):
        k = r['sa_name'].strip().upper()
        if k in sas:
            by_sa.setdefault(k, []).append(r['card_id'])
    nms = {g['nm_id'] for g in gaps if g['nm_id']}
    sizes = {}
    for r in WbSizes.objects.filter(nm_id__in=nms).values('nm_id', 'tech_size').order_by('tech_size'):
        sizes.setdefault(r['nm_id'], []).append(r['tech_size'] or '')

    def doc_cols(doc_id):
        d = docs.get(doc_id)
        if d is None:
            return ['', None, '']
        return [d.number, d.date, getattr(d.counterparty, 'name', '') or '']

    rows = []
    for g in gaps:
        problem = 'Нет карточки' if g['nm_id'] is None else 'Нет размера'
        hint = ''
        if g['nm_id'] is None:
            c = by_sa.get((g['upd_sa_name'] or '').strip().upper(), [])
            hint = str(c[0]) if len(c) == 1 else (f'несколько: {len(c)}' if c else '')
        qty = float(g['upd_qty'] or 0)
        price = float(g['upd_price_vatless'] or 0)
        rows.append(doc_cols(g['upd_document_id']) + [
            g['upd_pos'], problem, g['brand'] or '', g['upd_title'] or '', g['upd_sa_name'] or '',
            g['upd_size'] or '', g['nm_id'], hint, ', '.join(sizes.get(g['nm_id'], [])),
            qty, price, round(qty * price, 2)])

    # сводка по УПД
    summary = []
    for doc_id in sorted(docs, key=lambda i: (docs[i].date, docs[i].number)):
        q = wb_lines.filter(upd_document_id=doc_id)
        n_wb = q.count()
        n_nm = q.filter(nm__isnull=True).count()
        n_ch = q.filter(nm__isnull=False, chrt__isnull=True).count()
        if not n_nm and not n_ch:
            continue
        summary.append(doc_cols(doc_id) + [n_wb, n_nm, n_ch,
                                           round(100.0 * (n_nm + n_ch) / n_wb, 1) if n_wb else None])

    today = date.today()
    sub = f"Строки канала «ВБ» без карточки или размера · на {today:%d.%m.%Y}"
    wb = Workbook()
    ws = wb.active
    ws.title = "Сводка по УПД"
    s_cols = ["УПД", "Дата", "Поставщик", "Строк ВБ", "Нет карточки, строк",
              "Нет размера, строк", "С пробелами, %"]
    _write_table(ws, mp, "Пробелы разметки ВБ", sub, f"УПД с пробелами: {len(summary)}",
                 s_cols, summary, totals=True, freeze_cols=1, header_max=14,
                 col_formats={6: mp.FMT_PCT})

    ws = wb.create_sheet("Строки")
    l_cols = ["УПД", "Дата", "Поставщик", "Поз.", "Проблема", "Бренд", "Название УПД",
              "Артикул УПД", "Размер УПД", "NM_ID", "Карточка с таким артикулом",
              "Размеры WB", "Кол-во, шт", "Цена без НДС, ₽", "Сумма без НДС, ₽"]
    _write_table(ws, mp, "Строки без карточки или размера", sub, f"Строк: {len(rows)}",
                 l_cols, rows, totals=True, freeze_cols=4, header_max=14,
                 col_formats={0: "@", 3: "0", 9: "0", 13: mp.FMT_MONEY_DEC, 14: mp.FMT_MONEY_DEC})

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue(), _file_name(docs, today)


def _file_name(docs, today):
    """Одна УПД: «номер дата поставщик»; несколько — их число и дата выгрузки."""
    if len(docs) == 1:
        d = next(iter(docs.values()))
        name = f"УПД № {d.number} от {d.date:%d.%m.%Y} {getattr(d.counterparty, 'name', '') or ''}".strip()
    else:
        name = f"Пробелы ВБ {len(docs)} УПД {today:%d.%m.%Y}"
    name = re.sub(r'[\\/:*?"<>|]+', '-', name)
    return f"{name}.xlsx"
