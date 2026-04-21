# # budget/reporting/pdf/exporter.py
# from pathlib import Path

# from django.conf import settings
# from django.http import HttpResponse
# from django.template.loader import render_to_string
# from weasyprint import CSS, HTML

# from budget.reporting.pdf.context.budget_context import build_budget_pdf_context


# def build_budget_pdf_response(version):
#     context = build_budget_pdf_context(version)

#     # Базовые флаги отображения
#     context.setdefault("show_cover", True)
#     context.setdefault("show_toc", True)

#     # Данные для обложки
#     context.setdefault("company", 'ООО "ТРЕНДСЕТТЕР"')
#     context.setdefault("cover_title", context.get("title"))
#     context.setdefault("cover_subtitle", context.get("subtitle"))
#     context.setdefault("cover_type", "Управленческая отчетность")
#     context.setdefault("cover_system", "Financial & Performance Analysis")
#     context.setdefault("report_type", "Ежемесячный")
#     context.setdefault("author", "Финансовый департамент")
#     context.setdefault("confidential", True)

#     # Период для обложки
#     if context.get("detail_month"):
#         context.setdefault("period_label", context["detail_month"])

#     html = render_to_string(
#         "budget/budget_report.html",
#         context,
#     )

#     css_dir = Path(settings.BASE_DIR) / "static" / "css" / "budget"
#     report_css_file = css_dir / "budget.css"
#     cover_css_file = css_dir / "cover.css"

#     stylesheets = [CSS(filename=str(report_css_file))]

#     if cover_css_file.exists():
#         stylesheets.append(CSS(filename=str(cover_css_file)))

#     pdf_bytes = HTML(
#         string=html,
#         base_url=str(settings.BASE_DIR),
#     ).write_pdf(
#         stylesheets=stylesheets
#     )

#     response = HttpResponse(pdf_bytes, content_type="application/pdf")
#     response["Content-Disposition"] = f'attachment; filename="budget_{version.id}.pdf"'
#     return response


# budget/reporting/pdf/exporter.py
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from budget.reporting.pdf.context.budget_context import build_budget_pdf_context


def build_budget_pdf_response(version):
    context = build_budget_pdf_context(version)

    # Базовые флаги отображения
    context.setdefault("show_cover", True)
    context.setdefault("show_toc", True)

    # Данные для обложки
    context.setdefault("company", 'ООО "ТРЕНДСЕТТЕР"')
    context.setdefault("cover_title", context.get("title"))
    context.setdefault("cover_subtitle", context.get("subtitle"))
    context.setdefault("cover_type", "Управленческая отчетность")
    context.setdefault("cover_system", "Financial & Performance Analysis")
    context.setdefault("report_type", "Ежемесячный")
    context.setdefault("author", "Финансовый департамент")
    context.setdefault("confidential", True)

    # Период для обложки
    if context.get("detail_month"):
        context.setdefault("period_label", context["detail_month"])

    html = render_to_string(
        "budget/budget_report.html",
        context,
    )

    css_dir = Path(settings.BASE_DIR) / "static" / "css" / "budget"
    report_css_file = css_dir / "budget.css"
    cover_css_file = css_dir / "cover.css"
    toc_css_file = css_dir / "toc.css"  

    stylesheets = [CSS(filename=str(report_css_file))]

    if cover_css_file.exists():
        stylesheets.append(CSS(filename=str(cover_css_file)))

    # ✅ Добавляем toc.css если существует
    if toc_css_file.exists():
        stylesheets.append(CSS(filename=str(toc_css_file)))

    pdf_bytes = HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(
        stylesheets=stylesheets
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="budget_{version.id}.pdf"'
    return response