# inventories/views.py
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .reporting.excel.sheets import StocksReportGenerator

@staff_member_required
def export_stocks_excel(request):
    """Экспорт остатков в Excel с красивым форматированием"""
    report_date = request.GET.get('report_date')
    
    if not report_date:
        return HttpResponse("Ошибка: дата не указана", status=400)
    
    try:
        generator = StocksReportGenerator()
        output = generator.generate(report_date)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="stocks_report_{report_date}.xlsx"'
        
        return response
        
    except ValueError as e:
        return HttpResponse(str(e), status=404)
    except Exception as e:
        return HttpResponse(f"Ошибка при формировании отчета: {str(e)}", status=500)