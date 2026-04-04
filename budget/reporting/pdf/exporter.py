from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

from budget.reporting.pdf.budget_data import build_budget_pdf_context


def build_budget_pdf_response(version):
    context = build_budget_pdf_context(version)

    html = render_to_string(
        "budget/budget_report.html",
        context,
    )

    pdf_bytes = HTML(string=html).write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="budget_{version.id}.pdf"'
    return response