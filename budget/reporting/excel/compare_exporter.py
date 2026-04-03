# budget/reporting/excel/compare_exporter.py
from io import BytesIO

from django.http import HttpResponse

from .compare_workbook import build_budget_compare_workbook


def build_budget_compare_excel_response(versions):
    output = BytesIO()

    wb = build_budget_compare_workbook(versions)
    wb.save(output)
    output.seek(0)

    if versions:
        valid_date_from = [v.date_from for v in versions if v.date_from]
        valid_date_to = [v.date_to for v in versions if v.date_to]

        if valid_date_from and valid_date_to:
            period_str = f"{min(valid_date_from).strftime('%Y_%m')}-{max(valid_date_to).strftime('%Y_%m')}"
        else:
            period_str = "compare"
    else:
        period_str = "compare"

    filename = f"budget_compare_{period_str}.xlsx"

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response