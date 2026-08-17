from __future__ import annotations

from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _write(ws, frame):
    if frame is None:
        frame = pd.DataFrame()

    for col_idx, col in enumerate(frame.columns, 1):
        cell = ws.cell(1, col_idx, col)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="E9ECEF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_idx, row in enumerate(frame.itertuples(index=False), 2):
        for col_idx, value in enumerate(row, 1):
            if hasattr(value, "isoformat") and not isinstance(value, str):
                try:
                    value = value.isoformat()
                except Exception:
                    pass
            ws.cell(row_idx, col_idx, value)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for idx, col in enumerate(frame.columns, 1):
        width = 45 if col in ("reason", "title") else max(12, min(len(str(col)) + 3, 24))
        ws.column_dimensions[get_column_letter(idx)].width = width


def build_pricing_excel(payload):
    wb = Workbook()
    default = wb.active
    wb.remove(default)

    for title, key in (
        ("Рекомендации", "recommendations"),
        ("Бренды и категории", "portfolio"),
        ("Сценарии", "scenarios"),
        ("История", "history"),
    ):
        ws = wb.create_sheet(title)
        _write(ws, pd.DataFrame(payload.get(key) or []))

    ws = wb.create_sheet("Методология")
    rows = [
        ("Дата анализа", payload.get("report_date")),
        ("WB остатки", payload.get("wb_date")),
        ("FBS остатки", payload.get("fbs_date")),
        ("Universe", "Только товары с физическим остатком WB + FBS > 0"),
        ("Fallback", "Для WB и FBS отдельно используется последний снимок <= дате анализа"),
        ("Маржа", "amount_vatless - FIFO cogs_man + net_comission"),
        ("Эластичность", "ln(Q) = a + b * ln(buyer_price); наблюдаемая связь, не причинная оценка"),
        ("Не входит", "Маркетинг, штрафы, хранение и прочие недельные расходы WB"),
    ]

    for r, (k, v) in enumerate(rows, 1):
        ws.cell(r, 1, k)
        ws.cell(r, 2, v)
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 95

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out.getvalue()
