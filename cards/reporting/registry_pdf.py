# cards/reporting/registry_pdf.py



from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import CSS, HTML
from django.db.models import Sum, Count
from ..models import UpdDocument


def generate_registry_pdf(upd_ids):
    """
    Генерирует PDF реестр документов
    """
    
    # Получаем данные
    queryset = UpdDocument.objects.filter(
        id__in=upd_ids
    ).select_related(
        'counterparty', 'lot'
    ).annotate(
        total_amount_vatadd=Sum('income_lines__upd_amount_vatadd'),
        total_qty=Sum('income_lines__upd_qty'),
        lines_count=Count('income_lines')
    ).order_by('date', 'number')
    
    # Подготавливаем данные для шаблона
    documents = []
    total_sum = 0
    total_qty = 0
    total_lines = 0
    
    for doc in queryset:
        counterparty_name = str(doc.counterparty) if doc.counterparty else '-'
        if ' (ИНН:' in counterparty_name:
            counterparty_name = counterparty_name.split(' (ИНН:')[0]
        
        amount = doc.total_amount_vatadd or 0
        total_sum += amount
        qty = doc.total_qty or 0
        total_qty += qty
        lines = doc.lines_count or 0
        total_lines += lines
        
        documents.append({
            'counterparty': counterparty_name,
            'number': doc.number,
            'date': doc.date.strftime('%d.%m.%Y'),
            'id': doc.id,
            'amount': amount,
            'qty': qty,
            'lines': lines,
        })
    
    context = {
        'company': 'ООО "ТРЕНДСЕТТЕР"',
        'title': 'Реестр документов УПД',
        'report_date': datetime.now().strftime('%d.%m.%Y'),
        'report_time': datetime.now().strftime('%H:%M'),
        'documents': documents,
        'total_sum': total_sum,
        'total_qty': total_qty,
        'total_lines': total_lines,
        'total_count': len(documents),
    }
    
    # Генерируем HTML
    html = render_to_string(
        "reporting/registry_report.html",
        context,
    )
    
    # Путь к CSS
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "upd_issues" / "registry.css"
    
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
    
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Реестр_УПД_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
    return response