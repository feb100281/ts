# gear/app/daily_sales/assistant/views.py
from django.http import FileResponse, Http404

from .excel import file_path


def assistant_file(request, fid):
    """Скачивание Excel, сформированного помощником (только сотрудники)."""
    p = file_path(fid)
    if p is None:
        raise Http404("Файл не найден или устарел")
    name = p.name.split("__", 1)[1]
    return FileResponse(open(p, "rb"), as_attachment=True, filename=name)
