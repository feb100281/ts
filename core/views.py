import subprocess
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect


@staff_member_required
def run_gl_etl(request):
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "gl-etl.service"],
            capture_output=True,
            text=True,
            check=True,
        )
        messages.success(request, "gl-etl.service запущен")
    except subprocess.CalledProcessError as e:
        err = e.stderr or e.stdout or str(e)
        messages.error(request, f"Ошибка запуска gl-etl.service: {err}")

    return redirect(request.META.get("HTTP_REFERER", "/admin/"))