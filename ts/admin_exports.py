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
# Экспорт анализа бюджета (пока заглушка)
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