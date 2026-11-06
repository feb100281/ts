from django.http import FileResponse
from django.contrib.admin.views.decorators import staff_member_required

from reports.services.pdf import export_report_pdf


@staff_member_required
def download_report_pdf(request, report_id):

    pdf_path = export_report_pdf(
        request=request,
        report_id=report_id,
    )

    return FileResponse(
        open(pdf_path, "rb"),
        as_attachment=True,
        filename=pdf_path.name,
        content_type="application/pdf",
    )
