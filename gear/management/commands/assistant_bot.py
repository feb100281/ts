# gear/management/commands/assistant_bot.py
"""ИИ-помощник в Telegram: тот же помощник, что в дашбордах.

    python manage.py assistant_bot --profile sales
    python manage.py assistant_bot --profile finance

Токены — в .env: TELEGRAM_BOT_TOKEN_SALES, TELEGRAM_BOT_TOKEN_FINANCE.
TELEGRAM_PROXY=socks5://127.0.0.1:1080 — если Telegram недоступен напрямую.
TELEGRAM_ADMIN_ID — кому писать о новых заявках (необязательно).
Доступ выдаётся в админке: «Помощник в Telegram: доступ». Только личные чаты.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone

API = "https://api.telegram.org/bot{token}/{method}"
HISTORY_TURNS = 8            # сколько последних реплик помнить в диалоге
HISTORY_TTL = 2 * 60 * 60    # через сколько секунд тишины диалог начинается заново
LIMIT = 3900                 # запас до лимита Telegram 4096 символов
NAMES = {"sales": "помощник по продажам", "finance": "финансовый помощник"}


class Bot:
    def __init__(self, token: str, profile: str):
        self.token, self.profile = token, profile
        self.history: dict[int, tuple[float, list]] = {}
        self.opener = self._opener()

    # ---------------------------------------------------------------- сеть
    @staticmethod
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

    def call(self, method: str, timeout=40, **params):
        req = urllib.request.Request(
            API.format(token=self.token, method=method),
            data=json.dumps(params).encode("utf-8"),
            headers={"content-type": "application/json"}, method="POST")
        with self.opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def send_document(self, chat_id: int, path, name: str):
        boundary = uuid.uuid4().hex
        body = b"".join([
            f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n'
            f'{chat_id}\r\n'.encode(),
            f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
            f'filename="{name}"\r\nContent-Type: application/vnd.openxmlformats-'
            f'officedocument.spreadsheetml.sheet\r\n\r\n'.encode("utf-8"),
            path.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
        req = urllib.request.Request(
            API.format(token=self.token, method="sendDocument"), data=body,
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
            method="POST")
        with self.opener.open(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))

    def say(self, chat_id: int, text: str):
        for part in split(to_html(text)):
            try:
                self.call("sendMessage", chat_id=chat_id, text=part, parse_mode="HTML",
                          disable_web_page_preview=True)
            except urllib.error.HTTPError:
                # разметка не прошла — отправляем простым текстом
                self.call("sendMessage", chat_id=chat_id,
                          text=re.sub(r"<[^>]+>", "", html.unescape(part))[:4000])

    # ---------------------------------------------------------------- доступ
    def access(self, user: dict):
        from gear.models import TelegramAccess
        name = " ".join(x for x in (user.get("first_name"), user.get("last_name")) if x)
        obj, created = TelegramAccess.objects.get_or_create(
            tg_id=user["id"], bot=self.profile,
            defaults={"full_name": name, "username": user.get("username") or ""})
        if not created and (obj.full_name != name
                            or obj.username != (user.get("username") or "")):
            obj.full_name, obj.username = name, user.get("username") or ""
            obj.save(update_fields=["full_name", "username"])
        return obj, created

    def notify_admin(self, obj):
        admin_id = (os.getenv("TELEGRAM_ADMIN_ID") or "").strip()
        if not admin_id.lstrip("-").isdigit():
            return
        try:
            self.call("sendMessage", chat_id=int(admin_id), text=(
                f"Новая заявка: {NAMES[self.profile]}\n{obj.full_name} "
                f"{'@' + obj.username if obj.username else ''}\nID {obj.tg_id}\n"
                "Доступ — в админке: «Помощник в Telegram: доступ»."))
        except Exception:
            pass

    # ---------------------------------------------------------------- диалог
    def handle(self, msg: dict):
        chat, user = msg.get("chat") or {}, msg.get("from") or {}
        chat_id, text = chat.get("id"), (msg.get("text") or "").strip()
        if chat.get("type") != "private":
            if text.startswith("/"):
                self.say(chat_id, "Я отвечаю только в личных сообщениях.")
            return
        if user.get("is_bot") or not text:
            return
        obj, created = self.access(user)
        if created:
            self.notify_admin(obj)
        if not obj.is_allowed:
            self.say(chat_id, "Заявка на доступ отправлена. Как только её подтвердят, "
                              "я начну отвечать." if created else
                              "Доступ пока не подтверждён. Напишите Дарье.")
            return
        if text in ("/start", "/help"):
            self.say(chat_id, f"Здравствуйте! Я {NAMES[self.profile]}. Спрашивайте обычными "
                              "словами и указывайте период. Любой расчёт пришлю файлом — "
                              "напишите «пришли в Excel».\n/new — начать разговор заново.")
            return
        if text == "/new":
            self.history.pop(chat_id, None)
            self.say(chat_id, "Начинаем заново. Что посчитать?")
            return

        from gear.app.daily_sales.assistant.excel import file_path
        from gear.app.daily_sales.assistant.llm import AssistantError, ask

        seen, turns = self.history.get(chat_id, (0, []))
        if time.time() - seen > HISTORY_TTL:
            turns = []
        turns = turns + [{"role": "user", "content": text}]
        try:
            self.call("sendChatAction", chat_id=chat_id, action="typing")
        except Exception:
            pass
        try:
            res = ask(turns, self.profile)
        except AssistantError as e:
            self.say(chat_id, f"Не получилось ответить: {e}")
            return
        except Exception as e:
            self.say(chat_id, "Не получилось ответить — попробуйте переформулировать вопрос.")
            print(f"[bot {self.profile}] ошибка: {type(e).__name__}: {e}", flush=True)
            return
        answer = res.get("text") or "(пустой ответ)"
        self.say(chat_id, answer)
        for f in res.get("files") or []:
            p = file_path(f.get("id", ""))
            if p:
                try:
                    self.send_document(chat_id, p, f.get("name") or p.name.split("__", 1)[-1])
                except Exception as e:
                    self.say(chat_id, f"Файл сформирован, но отправить не удалось: {e}")
        turns.append({"role": "assistant", "content": answer})
        self.history[chat_id] = (time.time(), turns[-HISTORY_TURNS * 2:])
        type(obj).objects.filter(pk=obj.pk).update(
            requests=obj.requests + 1, last_seen=timezone.now())

    def run(self):
        me = self.call("getMe")["result"]
        print(f"[bot {self.profile}] запущен: @{me.get('username')}", flush=True)
        offset = None
        while True:
            try:
                params = {"timeout": 25, "allowed_updates": ["message"]}
                if offset is not None:
                    params["offset"] = offset
                updates = self.call("getUpdates", timeout=40, **params).get("result", [])
            except Exception as e:
                print(f"[bot {self.profile}] нет связи с Telegram: {e}", flush=True)
                time.sleep(5)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                if "message" not in u:
                    continue
                close_old_connections()
                try:
                    self.handle(u["message"])
                except Exception as e:
                    print(f"[bot {self.profile}] {type(e).__name__}: {e}", flush=True)


# -------------------------------------------------------------------- текст
def _table(lines: list[str]) -> str:
    """Таблица Markdown → моноширинный блок с выровненными колонками."""
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in r)]
    if not rows:
        return ""
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    w = [max(len(r[i]) for r in rows) for i in range(n)]
    num = lambda c: bool(re.fullmatch(r"[−\-+]?[\d\s.,]+%?", c or "x"))
    out = []
    for k, r in enumerate(rows):
        out.append("  ".join(c.rjust(w[i]) if num(c) and k else c.ljust(w[i])
                             for i, c in enumerate(r)).rstrip())
        if k == 0:
            out.append("  ".join("─" * x for x in w))
    return "<pre>" + html.escape("\n".join(out)) + "</pre>"


def to_html(text: str) -> str:
    """Markdown помощника → разметка Telegram (жирный, курсив, таблицы)."""
    out, table = [], []
    for ln in (text or "").split("\n"):
        if ln.strip().startswith("|") and ln.strip().endswith("|"):
            table.append(ln)
            continue
        if table:
            out.append(_table(table))
            table = []
        s = html.escape(ln)
        s = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"^\s*[-*]\s+", "• ", s)
        out.append(s)
    if table:
        out.append(_table(table))
    return "\n".join(out).strip()


def split(text: str) -> list[str]:
    """Режем длинный ответ по абзацам, не разрывая таблицы."""
    if len(text) <= LIMIT:
        return [text] if text else []
    parts, cur = [], ""
    for block in re.split(r"(<pre>.*?</pre>)", text, flags=re.S):
        pieces = [block] if block.startswith("<pre>") else block.split("\n\n")
        for p in pieces:
            if len(cur) + len(p) + 2 > LIMIT and cur:
                parts.append(cur.strip())
                cur = ""
            while len(p) > LIMIT:                       # очень длинный блок — по строкам
                cut = p.rfind("\n", 0, LIMIT)
                cut = cut if cut > 0 else LIMIT
                chunk, p = p[:cut], p[cut:]
                if chunk.startswith("<pre>") and not chunk.endswith("</pre>"):
                    chunk, p = chunk + "</pre>", "<pre>" + p
                parts.append(chunk)
            cur += p + "\n\n"
    if cur.strip():
        parts.append(cur.strip())
    return parts


class Command(BaseCommand):
    help = "ИИ-помощник в Telegram (--profile sales | finance)"

    def add_arguments(self, parser):
        parser.add_argument("--profile", choices=["sales", "finance"], required=True)

    def handle(self, *args, **opts):
        profile = opts["profile"]
        token = (os.getenv(f"TELEGRAM_BOT_TOKEN_{profile.upper()}") or "").strip()
        if not token:
            raise CommandError(f"В .env нет TELEGRAM_BOT_TOKEN_{profile.upper()}")
        try:
            Bot(token, profile).run()
        except KeyboardInterrupt:
            pass
