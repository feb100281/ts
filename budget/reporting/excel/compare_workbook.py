from openpyxl import Workbook

from .data_loader import load_budget_export_data
from .sheets.compare_summary_sheet import build_compare_summary_sheet


def build_budget_compare_workbook(versions):
    wb = Workbook()
    wb.remove(wb.active)

    versions_data = []
    for version in versions:
        data = load_budget_export_data(version)
        versions_data.append({
            "version_obj": version,
            "data": data,
        })

    build_compare_summary_sheet(wb, versions_data)

    wb.active = wb.sheetnames.index("SUMMARY_COMPARE")
    return wb