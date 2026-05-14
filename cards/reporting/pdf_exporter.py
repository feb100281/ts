# cards/reporting/pdf_exporter.py
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import CSS, HTML


def build_missing_fields_pdf_response(stats, upd_list=None, missing_nm_by_upd=None, missing_chrt_by_upd=None):

    
    # Вычисляем проценты
    total_amount = stats.get('total_amount_vatadd', 0)
    
    missing_nm_percent = 0
    missing_chrt_percent = 0
    
    if total_amount > 0:
        missing_nm_percent = round(stats.get('missing_nm_amount', 0) / total_amount * 100, 1)
        missing_chrt_percent = round(stats.get('missing_chrt_amount', 0) / total_amount * 100, 1)
    
    context = {
        'company': 'ООО "ТРЕНДСЕТТЕР"',
        'title': 'Отчет по результатам проверки УПД',
        'report_date': datetime.now().strftime('%d.%m.%Y'),
        'report_time': datetime.now().strftime('%H:%M'),
        
        # Общая статистика
        'total_upd_count': stats.get('total_upd_count', 0),
        'total_lines': stats.get('total_lines', 0),
        'total_amount_vatadd': stats.get('total_amount_vatadd', 0),
        
        # Статистика по NM_ID
        'missing_nm_count': stats.get('missing_nm_count', 0),
        'missing_nm_qty': stats.get('missing_nm_qty', 0),
        'missing_nm_amount': stats.get('missing_nm_amount', 0),
        'missing_nm_percent': missing_nm_percent,
        
        # Статистика по CHRT_ID
        'missing_chrt_count': stats.get('missing_chrt_count', 0),
        'missing_chrt_qty': stats.get('missing_chrt_qty', 0),
        'missing_chrt_amount': stats.get('missing_chrt_amount', 0),
        'missing_chrt_percent': missing_chrt_percent,
        
        # Список УПД и распределение проблем
        'upd_list': upd_list or [],
        'missing_nm_by_upd': missing_nm_by_upd or [],
        'missing_chrt_by_upd': missing_chrt_by_upd or [],
    }
    
    # Генерируем HTML
    html = render_to_string(
        "reporting/missing_fields_report.html",
        context,
    )
    
    # Путь к CSS файлу
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "upd_issues" / "report.css"
    
    stylesheets = []
    if css_path.exists():
        stylesheets.append(CSS(filename=str(css_path)))
    
    # Генерируем PDF
    pdf_bytes = HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(
        stylesheets=stylesheets,
        presentational_hints=True,
    )
    
    # Формируем ответ
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Soprovoditelnoe_pismo_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
    return response