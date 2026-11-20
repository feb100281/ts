# budget/reporting/pdf/revenue_exporter.py
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from budget.reporting.pdf.revenue_analysis.context import build_revenue_analysis_context


def build_revenue_analysis_pdf_response(version, report_date=None):
    """
    Генерация PDF отчета по анализу выручки (доходная часть бюджета)
    """
    
    # Собираем контекст из revenue_analysis
    context = build_revenue_analysis_context(version, report_date)
    
    # Базовые флаги отображения
    context.setdefault("show_cover", False)  # Без обложки, 1 страница
    
    # Данные для шапки отчета
    context.setdefault("company", 'ООО "ТРЕНДСЕТТЕР"')
    context.setdefault("title", "Выполнение целевого оборота по соглашению с WB")
    scenario = "базовый"
    if version.revenue_param:
        scenario_code = version.revenue_param.get("scenario", "base")
        # Маппинг кода на русское название
        scenario_map = {
            "base": "Базовый",
            "optimistic": "Оптимистичный",
            "conservative": "Консервативный",
        }
        scenario = scenario_map.get(scenario_code, scenario_code.capitalize())
    context.setdefault("subtitle", f"Сценарий: {scenario}")
    # Если хотим также показать номер версии, можно добавить: f"Сценарий: {scenario} (Версия {version.number})"
    
    # Период для отчета
    if context.get("revenue_analysis"):
        context.setdefault("period_label", f"Данные на {context['revenue_analysis']['report_date_str']}")
    else:
        context.setdefault("period_label", "Нет данных за период")
    
    # Генерируем HTML
    html = render_to_string(
        "budget/revenue_analysis_report.html",
        context,
    )
    
    # CSS стили
    css_dir = Path(settings.BASE_DIR) / "static" / "css" / "budget"
    report_css_file = css_dir / "budget.css"
    
    stylesheets = []
    if report_css_file.exists():
        stylesheets.append(CSS(filename=str(report_css_file)))
    
    # Генерируем PDF
    pdf_bytes = HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(
        stylesheets=stylesheets
    )
    
    # Формируем ответ
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="wb_target_turnover_{report_date.strftime("%Y%m%d") if report_date else "now"}.pdf"'
    
    return response