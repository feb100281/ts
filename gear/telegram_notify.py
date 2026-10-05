# gear/telegram_notify.py
"""Сообщение сотруднику в Telegram, когда ему открыли или закрыли доступ к помощнику."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

TEXT = {
    True: "Доступ открыт. Напишите вопрос или нажмите /start — покажу примеры.",
    False: "Доступ к помощнику закрыт. Если это ошибка — напишите Дарье.",
}


def _opener():
    proxy = (os.getenv("TELEGRAM_PROXY") or "").strip()
    if not proxy:
        return urllib.request.build_opener()
    if proxy.startswith("socks"):
        import socks
        from sockshandler import SocksiPyHandler
        u = urllib.parse.urlparse(proxy)
        return urllib.request.build_opener(SocksiPyHandler(
            socks.SOCKS5, u.hostname or "127.0.0.1", u.port or 1080, rdns=True,
            username=u.username, password=u.password))
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"https": proxy, "http": proxy}))


def access_changed(tg_id: int, bot: str, allowed: bool) -> bool:
    """Не мешает сохранению в админке: при любой ошибке просто возвращает False."""
    token = (os.getenv(f"TELEGRAM_BOT_TOKEN_{bot.upper()}") or "").strip()
    if not token:
        return False
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": tg_id, "text": TEXT[bool(allowed)]}).encode("utf-8"),
            headers={"content-type": "application/json"}, method="POST")
        with _opener().open(req, timeout=10) as r:
            return bool(json.loads(r.read().decode("utf-8")).get("ok"))
    except Exception:
        return False
