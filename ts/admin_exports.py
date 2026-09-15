# ts/admin_exports.py
import csv
from django.db import connection
from django.http import HttpResponse

import tempfile
from datetime import datetime
from pathlib import Path

from django.http import FileResponse, HttpResponseBadRequest, JsonResponse
from reporting.excel.engine import build_manpack

import json
from django.views.decorators.http import require_http_methods
from budget.reporting.pdf.revenue_exporter import build_revenue_analysis_pdf_response


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
    
    

# ============================================================
# API для получения списка бюджетов (прямо из БД)
# ============================================================
@require_http_methods(["GET"])
def api_budgets(request):
    """API для получения списка версий бюджетов"""
    sql = """
        SELECT 
            id, 
            number, 
            budget_type, 
            description, 
            date_from, 
            date_to, 
            revenue_param
        FROM public.budget_budgetversion
        ORDER BY date_from DESC, id DESC
    """
    
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
    
    result = []
    for row in rows:
        budget_dict = dict(zip(columns, row))
        
        # Парсим revenue_param если это строка JSON
        revenue_param = budget_dict.get('revenue_param')
        if isinstance(revenue_param, str):
            try:
                revenue_param = json.loads(revenue_param)
            except:
                revenue_param = {}
        
        result.append({
            'id': budget_dict['id'],
            'number': budget_dict['number'],
            'budget_type': budget_dict['budget_type'],
            'description': budget_dict['description'],
            'date_from': budget_dict['date_from'].isoformat() if budget_dict['date_from'] else None,
            'date_to': budget_dict['date_to'].isoformat() if budget_dict['date_to'] else None,
            'revenue_param': revenue_param,
        })
    
    return JsonResponse(result, safe=False)


# ============================================================
# Экспорт анализа бюджета 
# ============================================================
def export_budget_analysis(request):
    """Экспорт анализа бюджета (PDF) - только доходная часть"""
    budget_id = request.GET.get('budget_id')
    report_date = request.GET.get('report_date')
    
    if not budget_id or not report_date:
        return HttpResponseBadRequest("Не указан budget_id или report_date")
    
    try:
        report_date_obj = datetime.strptime(report_date, "%Y-%m-%d").date()
        from budget.models import BudgetVersion
        budget = BudgetVersion.objects.get(id=budget_id)
    except BudgetVersion.DoesNotExist:
        return HttpResponseBadRequest("Бюджет не найден")
    except ValueError:
        return HttpResponseBadRequest("Некорректный формат даты. Ожидается YYYY-MM-DD")
    
    # Генерируем PDF через новый экспортер
    return build_revenue_analysis_pdf_response(budget, report_date_obj)


# ============================================================
# Управленческий пакет (Титул + P&L + Cash Flow + пояснения)
# Собирается тем же кодом, что и команда `manage.py mp`,
# см. gear/management/commands/mp.py :: build_management_pack
# ============================================================
def export_management_pack(request):
    """Отдаёт xlsx управленческого пакета за выбранную отчётную дату."""
    date_str = request.GET.get("report_date")

    if not date_str:
        return HttpResponseBadRequest("Не передана дата report_date")

    try:
        report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponseBadRequest("Некорректный формат даты. Ожидается YYYY-MM-DD")

    start_year_raw = request.GET.get("start_year")
    try:
        start_year = int(start_year_raw) if start_year_raw else None
    except ValueError:
        return HttpResponseBadRequest("Некорректный start_year")

    # импорт внутри view: модуль тянет duckdb-подключение и sql-витрины,
    # незачем поднимать это при старте админки
    from gear.management.commands.mp import (
        build_management_pack,
        DEFAULT_START_YEAR,
    )

    temp_dir = Path(tempfile.gettempdir())
    file_path = temp_dir / f"management_pack_{report_date.strftime('%Y%m%d')}.xlsx"

    try:
        build_management_pack(
            report_date,
            start_year=start_year or DEFAULT_START_YEAR,
            out_path=file_path,
        )
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=file_path.name,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
#  Выгрузки витрин управленческого пакета в csv (разделитель «|»)
#
#  Сводных таблиц в самом пакете больше нет: вместо них отдаём те же
#  витрины отдельными файлами, чтобы сводную можно было собрать у себя.
# ---------------------------------------------------------------------------

def _export_manpack_csv(request, kind, prefix):
    date_str = request.GET.get("report_date")

    if not date_str:
        return HttpResponseBadRequest("Не передана дата report_date")

    try:
        report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponseBadRequest("Некорректный формат даты. Ожидается YYYY-MM-DD")

    # импорт внутри view: модуль тянет duckdb-подключение и sql-витрины
    from gear.management.commands.mp import export_raw_csv

    temp_dir = Path(tempfile.gettempdir())
    file_path = temp_dir / f"{prefix}_{report_date.strftime('%Y%m%d')}.csv"

    try:
        export_raw_csv(kind, report_date, out_path=file_path)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    # имя файла постоянное (cash_flow.csv, pl.csv): он подключается
    # источником к сводной, и от выгрузки к выгрузке не должен меняться
    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=f"{prefix}.csv",
        content_type="text/csv; charset=utf-8",
    )


def export_cf_csv(request):
    """Витрина движения денежных средств на отчётную дату, csv с «|»."""
    return _export_manpack_csv(request, "cf", "cash_flow")


def export_pl_csv(request):
    """Витрина P&L на отчётную дату, csv с «|»."""
    return _export_manpack_csv(request, "pl", "pl")
