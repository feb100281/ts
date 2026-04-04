# budget/reporting/pdf/exporter.py

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS

from budget.reporting.pdf.budget_data import build_budget_pdf_context


def build_budget_pdf_response(version):
    context = build_budget_pdf_context(version)

    html = render_to_string(
        "budget/budget_report.html",
        context,
    )

    css_file = Path(settings.BASE_DIR) / "static" / "css" / "budget" / "budget.css"

    pdf_bytes = HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(
        stylesheets=[CSS(filename=str(css_file))]
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="budget_{version.id}.pdf"'
    return response