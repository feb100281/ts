from io import BytesIO

from django.http import HttpResponse

from .compare_workbook import build_budget_compare_workbook


def build_budget_compare_excel_response(versions):
    output = BytesIO()

    wb = build_budget_compare_workbook(versions)
    wb.save(output)
    output.seek(0)

    if versions:
        date_from = min(v.date_from for v in versions if v.date_from)
        date_to = max(v.date_to for v in versions if v.date_to)

        if date_from and date_to:
            period_str = f"{date_from.strftime('%Y_%m')}-{date_to.strftime('%Y_%m')}"
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