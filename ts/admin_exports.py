# ts/admin_exports.py
import csv
from django.db import connection
from django.http import HttpResponse
from django.utils.timezone import now


def export_sql_to_csv(request, sql: str, filename_prefix: str):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    timestamp = now().strftime("%Y%m%d_%H%M%S")
    response["Content-Disposition"] = f'attachment; filename="{filename_prefix}_{timestamp}.csv"'

    # BOM для корректного открытия в Excel
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")

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
        filename_prefix="gl_rows"
    )


def export_arap_to_date(request):
    return export_sql_to_csv(
        request,
        sql="SELECT * FROM public.arap_to_date",
        filename_prefix="arap_to_date"
    )