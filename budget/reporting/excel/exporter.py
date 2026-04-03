# budget/reporting/excel/exporter.py
from io import BytesIO
from django.http import HttpResponse

from .workbook import build_budget_workbook


def build_budget_excel_response(version):
    output = BytesIO()

    wb = build_budget_workbook(version)
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="budget_{version.number}.xlsx"'
    )
    return response