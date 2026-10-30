import tempfile
from datetime import datetime
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, HttpResponseBadRequest

from reporting.excel.engine import build_manpack


@staff_member_required
def export_manpack(request):
    date_str = request.GET.get("report_date")

    if not date_str:
        return HttpResponseBadRequest("Не передана дата report_date")

    try:
        report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponseBadRequest("Некорректный формат даты. Ожидается YYYY-MM-DD")

    temp_dir = Path(tempfile.gettempdir())
    file_path = temp_dir / f"manpack_{report_date.strftime('%Y%m%d')}.xlsx"

    build_manpack(date_to=report_date, output_path=file_path)

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=file_path.name,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )