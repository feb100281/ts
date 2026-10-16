# gear/tgapp.py
"""Mini App бота продаж: страница внутри Telegram и её API.

Вход — по подписи Telegram (initData) токеном бота продаж: открыть может
только пользователь с подтверждённым доступом к боту (TelegramAccess,
bot="sales"). Отчёты — те же, что на кнопках бота (assistant/menu.py).
Файлы отдаются по подписанной ссылке на час: Telegram.WebApp.downloadFile
скачивает их без заголовков авторизации.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from datetime import date
from urllib.parse import parse_qsl, quote

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_GET

MAX_AGE = 24 * 3600
LINK_TTL = 3600


def _token() -> str:
    return (os.getenv("TELEGRAM_BOT_TOKEN_SALES") or "").strip()


def _verify(init_data: str) -> dict | None:
    """Проверка подписи Telegram WebApp; возвращает user или None."""
    token = _token()
    if not init_data or not token:
        return None
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", "")
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return None
    if time.time() - int(pairs.get("auth_date", 0) or 0) > MAX_AGE:
        return None
    try:
        return json.loads(pairs.get("user", "{}"))
    except ValueError:
        return None


def _access(request):
    from gear.models import TelegramAccess
    user = _verify(request.headers.get("X-Telegram-Init-Data", ""))
    if not user or "id" not in user:
        return None
    return TelegramAccess.objects.filter(tg_id=user["id"], bot="sales", is_allowed=True).first()


def _deny():
    return JsonResponse({"error": "Нет доступа. Откройте приложение из бота продаж."}, status=403)


def _date(v) -> date | None:
    try:
        return date.fromisoformat(str(v or ""))
    except ValueError:
        return None


def _sign(*parts) -> str:
    msg = ":".join(str(p) for p in parts).encode()
    return hmac.new(_token().encode(), msg, hashlib.sha256).hexdigest()[:32]


# ---------------------------------------------------------------- Telegram HTML → блоки
_KPI = re.compile(r"^(.+?):\s*<b>(.+?)</b>(.*)$")
_HEAD = re.compile(r"^<b>(.+)</b>$")


def blocks(text: str) -> dict:
    """Разбираем текст отчёта бота на заголовок, плитки показателей и секции."""
    lines = (text or "").split("\n")
    title = re.sub(r"<[^>]+>", "", lines[0]) if lines else ""
    sub = re.sub(r"<[^>]+>", "", lines[1]) if len(lines) > 1 and lines[1].startswith("<i>") else ""
    kpis, sections, notes, cur = [], [], [], None
    for ln in lines[2 if sub else 1:]:
        ln = ln.strip()
        if not ln:
            cur = None if cur and cur.get("rows") else cur
            continue
        if ln.startswith("<i>") and ln.endswith("</i>"):
            notes.append(ln[3:-4])
            continue
        m = _HEAD.match(ln)
        if m:
            cur = {"title": m.group(1), "rows": [], "text": []}
            sections.append(cur)
            continue
        if ln.startswith("•") or re.match(r"^\d+\.\s", ln):
            if cur is None:
                cur = {"title": "", "rows": [], "text": []}
                sections.append(cur)
            cur["rows"].append(ln.lstrip("• ").strip())
            continue
        m = _KPI.match(ln)
        if m and cur is None:
            rest = m.group(3).strip()
            kpis.append({"label": m.group(1), "value": m.group(2), "rest": rest})
            continue
        if cur is None:
            cur = {"title": "", "rows": [], "text": []}
            sections.append(cur)
        cur["text"].append(ln)
    return {"title": title, "sub": sub, "kpis": kpis, "sections": sections, "notes": notes}


# ---------------------------------------------------------------- страницы
@xframe_options_exempt
def app(request):
    return render(request, "tgapp/app.html", {})


@require_GET
def api_meta(request):
    acc = _access(request)
    if not acc:
        return _deny()
    from gear.app.daily_sales.assistant import menu
    hi = menu.loaded()
    reps = [{"code": k, "title": v, "single": k in menu.SINGLE_DAY,
             "presets": ([{"code": c, "label": t} for c, t in menu.WEEK_PRESETS] if k == "n"
                         else [{"code": "y", "label": "Вчера"}] if k in menu.SINGLE_DAY
                         else [{"code": c, "label": t} for c, t in menu.PRESETS])}
            for k, v in menu.REPORTS.items()]
    return JsonResponse({"name": (acc.full_name or "").split(" ")[0], "hi": hi.isoformat(),
                         "lo": menu.DATA_START.isoformat(), "reports": reps})


@require_GET
def api_report(request):
    acc = _access(request)
    if not acc:
        return _deny()
    from gear.app.daily_sales.assistant import menu
    rep = request.GET.get("rep", "")
    if rep not in menu.REPORTS:
        return JsonResponse({"error": "Нет такого отчёта"}, status=400)
    hi = menu.loaded()
    if request.GET.get("preset"):
        a, b = menu.preset(request.GET["preset"], hi)
    else:
        a, b = _date(request.GET.get("a")), _date(request.GET.get("b"))
        if not a or not b:
            return JsonResponse({"error": "Укажите период"}, status=400)
        a, b = sorted((max(a, menu.DATA_START), min(b, hi)))
        if rep in menu.SINGLE_DAY:
            a = b
    started = time.time()
    try:
        res = menu.build(rep, a, b)
    except Exception as e:
        print(f"[tgapp] {rep}: {type(e).__name__}: {e}", flush=True)
        return JsonResponse({"error": "Не получилось посчитать — попробуйте позже."}, status=500)
    _log(acc, f"[приложение] {menu.REPORTS[rep]} · {menu.span(a, b)}", started)
    if not res:
        return JsonResponse({"empty": True, "a": a.isoformat(), "b": b.isoformat()})
    exp = int(time.time()) + LINK_TTL
    files = []
    for code, label in res.get("files") or ():
        sig = _sign(acc.tg_id, rep, code, a, b, exp)
        files.append({"label": label, "url": (
            f"/tg/api/file/?u={acc.tg_id}&rep={rep}&code={quote(code)}&a={a}&b={b}&exp={exp}&sig={sig}")})
    out = blocks(res["text"])
    charts = res.get("charts") or ([res["chart"]] if res.get("chart") else [])
    out.update({"a": a.isoformat(), "b": b.isoformat(), "charts": _clean(charts), "files": files,
                "tables": _clean(res.get("tables") or []), "period": menu.span(a, b)})
    return JsonResponse(out)


@require_GET
def api_file(request):
    from gear.app.daily_sales.assistant import menu
    g = request.GET
    try:
        uid, exp = int(g.get("u", "")), int(g.get("exp", ""))
    except ValueError:
        return HttpResponse(status=403)
    rep, code = g.get("rep", ""), g.get("code", "")
    a, b = _date(g.get("a")), _date(g.get("b"))
    if (exp < time.time() or not a or not b or rep not in menu.REPORTS
            or not hmac.compare_digest(_sign(uid, rep, code, a, b, exp), g.get("sig", ""))):
        return HttpResponse("Ссылка устарела — откройте отчёт заново.", status=403,
                            content_type="text/plain; charset=utf-8")
    f = menu.file(rep, code, a, b)
    if not f:
        return HttpResponse("Данных для файла нет.", status=404, content_type="text/plain; charset=utf-8")
    name, data, mime = f
    resp = HttpResponse(data, content_type=mime)
    resp["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(name)}"
    return resp


def _clean(v):
    """numpy / NaN → обычные числа и None, чтобы ушло в JSON."""
    import math
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, date):
        return v.isoformat()
    return v


def _log(acc, text, started):
    try:
        from django.utils import timezone
        from gear.models import TelegramQuestion
        TelegramQuestion.objects.create(access=acc, bot="sales", text=text[:4000],
                                        seconds=round(time.time() - started, 1), has_file=False)
        type(acc).objects.filter(pk=acc.pk).update(last_seen=timezone.now())
    except Exception as e:
        print(f"[tgapp] журнал: {type(e).__name__}: {e}", flush=True)
