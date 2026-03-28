# ts/admin_exports.py
import csv
from django.db import connection
from django.http import HttpResponse

import tempfile
from datetime import datetime
from pathlib import Path

from django.http import FileResponse, HttpResponseBadRequest
from reporting.excel.engine import build_manpack


def export_sql_to_csv(request, sql: str, filename_prefix: str):
    response = HttpResponse(content_type="text/csv; charset=utf-8")

    response["Content-Disposition"] = f'attachment; filename="{filename_prefix}.csv"'

    # BOM для Excel
    response.write("\ufeff")
    writer = csv.writer(response, delimiter="|")

    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        writer.writerow(columns)

        for row in cursor.fetchall():
            writer.writerow(row)

    return response


def export_pl_for_csv(request):
    return export_sql_to_csv(
        request,
        sql="SELECT * FROM public.pl_for_csv",
        filename_prefix="gl_data"
    )


def export_arap_to_date(request):
    return export_sql_to_csv(
        request,
        sql="SELECT * FROM public.arap_to_date",
        filename_prefix="arap_data"
    )
    
def export_contracts_gl_check(request):
    return export_sql_to_csv(
        request,
        sql="SELECT * FROM public.contracts_gl_check",
        filename_prefix="contracts_gl_check"
    )
    
    
def export_manpack(request):
    date_str = request.GET.get("report_date")

    if not date_str:
        return HttpResponseBadRequest("Не передана дата report_date")

    try:
        report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponseBadRequest("Некорректный формат даты. Ожидается YYYY-MM-DD")

    # временный файл
    temp_dir = Path(tempfile.gettempdir())
    file_path = temp_dir / f"manpack_{report_date.strftime('%Y%m%d')}.xlsx"

    # генерация
    build_manpack(date_to=report_date, output_path=file_path)

    # отдача файла
    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=file_path.name,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )