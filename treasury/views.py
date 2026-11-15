"""Приём файлов Армении с компьютера (кнопка на рабочем столе)."""

import hashlib
import hmac
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from utils.bsparsers.am.loader import load_statement, sniff

KINDS = {"statement", "sales"}
MAX_SIZE = 50 * 1024 * 1024


def _authorized(request) -> bool:
    token = getattr(settings, "AM_UPLOAD_TOKEN", "") or ""
    got = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    return bool(token) and hmac.compare_digest(got, token)


@csrf_exempt
@require_POST
def am_upload(request):
    if not _authorized(request):
        return JsonResponse({"ok": False, "error": "нет доступа"}, status=403)
    kind = request.POST.get("kind", "")
    upload = request.FILES.get("file")
    if kind not in KINDS or upload is None:
        return JsonResponse({"ok": False, "error": "нужны поля kind и file"}, status=400)
    if upload.size > MAX_SIZE:
        return JsonResponse({"ok": False, "error": "файл больше 50 МБ"}, status=400)

    data = upload.read()
    digest = hashlib.sha1(data).hexdigest()
    rel = request.POST.get("path", upload.name)
    folder = Path(settings.MEDIA_ROOT) / "am_inbox" / kind
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{digest[:12]}_{Path(upload.name).name}"
    target.write_bytes(data)

    if kind == "sales":
        from utils.bsparsers.am.sales_loader import load_sales
        log = []
        try:
            res = load_sales(target, log=log.append)
        except Exception as exc:
            return JsonResponse({"ok": False, "file": rel, "error": str(exc), "log": log}, status=422)
        return JsonResponse({"ok": True, "file": rel, "message": "; ".join(log)})

    if not sniff(target):
        return JsonResponse({"ok": False, "file": rel, "error": "не похоже на армянскую выписку"}, status=400)
    log = []
    try:
        res = load_statement(target, log=log.append)
    except Exception as exc:                       # ответ с причиной — кнопка покажет её
        return JsonResponse({"ok": False, "file": rel, "error": str(exc), "log": log}, status=422)
    if res.get("new"):
        from utils.bsparsers.am.staff import auto_staff
        try:
            auto_staff(res["owner_id"], log.append)       # новые сотрудники — договор по образцу
        except Exception as exc:
            log.append(f"  сотрудники не заведены: {exc}")
    return JsonResponse({"ok": True, "file": rel, "new": res["new"], "existing": res["existing"],
                         "warnings": res["warnings"], "log": log})
