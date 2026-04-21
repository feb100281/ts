# # budget/reporting/excel/exporter.py
# from io import BytesIO
# from django.http import HttpResponse

# from .workbook import build_budget_workbook


# def build_budget_excel_response(version):
#     output = BytesIO()

#     wb = build_budget_workbook(version)
#     wb.save(output)
#     output.seek(0)

#     response = HttpResponse(
#         output.getvalue(),
#         content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#     )
#     response["Content-Disposition"] = (
#         f'attachment; filename="budget_{version.number}.xlsx"'
#     )
#     return response





# budget/reporting/excel/exporter.py
from io import BytesIO
from django.http import HttpResponse

from .workbook import build_budget_workbook
from .data_loader import load_budget_export_data


def build_budget_excel_response(version):
    output = BytesIO()

    # 🔥 подгружаем данные (чтобы достать сценарий и даты)
    data = load_budget_export_data(version)

    wb = build_budget_workbook(version)
    wb.save(output)
    output.seek(0)

    # -------------------------
    # Формируем имя файла
    # -------------------------

    revenue_param = data.get("revenue_param", {})
    scenario = revenue_param.get("scenario", "base")

    scenario_map = {
        "base": "BASE",
        "optimistic": "OPT",
        "conservative": "CONS",
    }

    scenario_label = scenario_map.get(str(scenario).lower(), str(scenario).upper())

    date_from = data["version"].get("date_from")
    date_to = data["version"].get("date_to")

    period_str = ""
    if date_from and date_to:
        period_str = f"{date_from.strftime('%Y_%m')}-{date_to.strftime('%Y_%m')}"

    # 👉 можно с номером версии (рекомендую)
    filename = f"budget_{version.number}_{scenario_label}_{period_str}.xlsx"

    # -------------------------

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response