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
import threading
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
DIGEST_HOURS = (7, 12)        # МСК: сводку продаж шлём с 7:00, повтор раз в час до 12:00
QUIET = ((23, 20), (23, 57))  # МСК: ночная загрузка данных, вопросы не принимаем
NAMES = {"sales": "помощник по продажам", "finance": "финансовый помощник"}

ABOUT = {
    "sales": "Продажи на Wildberries: отчёты по кнопкам за любой период — продажи, остатки, "
             "бренды, категории, расходы WB, реклама. Excel сразу.",
    "finance": "Финансы компании: прибыль, деньги, займы, договоры, прогноз. "
               "Отвечаю по данным компании и присылаю Excel.",
}
DESCRIPTION = {
    "sales": "Помощник по продажам на Wildberries.\n\nКнопки внизу — готовые отчёты за любой "
             "период: продажи, остатки, бренды, категории, расходы WB, реклама, топ карточек. "
             "Цифры, график и Excel сразу.\n\nНестандартный вопрос — напишите своими словами, "
             "ответит ИИ.\n\nДоступ — только для сотрудников, по подтверждению.",
    "finance": "Финансовый ИИ-помощник.\n\nСпросите обычными словами: прибыль и точка "
               "безубыточности, деньги на счетах, движение денег, займы, договоры, "
               "прогноз. Любой расчёт пришлю файлом Excel.\n\nДоступ — только для "
               "сотрудников, по подтверждению.",
}
MENU = {"examples": "Примеры вопросов", "new": "Новый разговор", "help": "Как пользоваться"}
# (подпись кнопки, вопрос помощнику)
EXAMPLES = {
    "sales": [("Продажи за вчера", "Продажи и возвраты за вчера как на сайте WB"),
              ("Топ-10 брендов", "Топ-10 брендов за прошлую неделю"),
              # маржа отключена до утверждения методики:
              # ("Что в убытке", "Какие бренды продаются в убыток в этом месяце?"),
              # ("Маржа в Excel", "Маржинальность по категориям за прошлый месяц — в Excel"),
              ("Остатки товаров", "Сколько товара на остатках по брендам?"),
              ("Возвраты в Excel", "Возвраты по брендам за прошлую неделю — в Excel")],
    "finance": [("Деньги на счетах", "Сколько денег на счетах?"),
                ("Прибыль и ТБУ", "Чистая прибыль и ТБУ за последние 3 месяца"),
                ("Поступления от WB", "Сколько пришло от WB в этом месяце?"),
                ("Займы и сроки", "Сколько мы должны по займам и когда гасить?")],
}
# что показывать, пока помощник работает с данными
STEPS = {
    "pl_report": "Считаю прибыль и убытки",
    "margin_report": "Считаю маржу",
    "wb_sales": "Смотрю продажи Wildberries",
    "cards_check": "Проверяю карточки товаров",
    "stocks_report": "Смотрю остатки товара",
    "incidents_report": "Смотрю происшествия на складах",
    "fbs_orders_report": "Смотрю заказы FBS",
    "cash_report": "Смотрю остатки на счетах",
    "cf_report": "Смотрю движение денег",
    "wb_payouts_report": "Смотрю поступления от Wildberries",
    "interest_report": "Считаю проценты по займам",
    "loans_report": "Смотрю займы и кредиты",
    "fx_report": "Смотрю курсы валют",
    "upd_report": "Смотрю приходы товара",
    "month_conclusions": "Собираю выводы за месяц",
    "scenario_report": "Считаю сценарий и точку безубыточности",
    "profit_vs_cash_report": "Сравниваю прибыль и деньги",
    "contracts_ending_report": "Смотрю сроки договоров",
    "counterparty_info": "Смотрю данные по контрагенту",
    "new_counterparties_report": "Ищу новых контрагентов",
    "export_excel": "Готовлю файл Excel",
}
STEP_DEFAULT = "Смотрю данные"
HELP = {
    "sales": "<b>Как пользоваться</b>\n"
             "• Пишите обычными словами и указывайте период: «вчера», «прошлая неделя», "
             "«с 1 по 15 октября».\n"
             "• Продажи считаю <b>как на сайте WB</b> — с НДС, как в кабинете: до СПП, "
             "после СПП и к перечислению.\n"
             "• Нужен файл — добавьте «пришли в Excel».\n"
             "• Уточняйте по ходу: «а по брендам?», «распиши по артикулам».\n"
             "• Кнопки внизу: примеры вопросов и «Новый разговор» — когда меняете тему.\n\n"
             "Важные цифры сверяйте с дашбордом. Если я ошибся — напишите Дарье.",
    "finance": "<b>Как пользоваться</b>\n"
               "• Пишите обычными словами и указывайте период или дату.\n"
               "• Прибыль считается по начислению (P&amp;L), деньги — по факту оплаты. "
               "Я всегда пишу, по какой базе отвечаю.\n"
               "• Нужен файл — добавьте «пришли в Excel».\n"
               "• Уточняйте по ходу: «а почему?», «по каким контрагентам?».\n"
               "• Кнопки внизу: примеры вопросов и «Новый разговор» — когда меняете тему.\n\n"
               "Важные цифры сверяйте с дашбордом. Если я ошибся — напишите Дарье.",
}


def quiet_now() -> bool:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    t = datetime.now(ZoneInfo("Europe/Moscow"))
    return QUIET[0] <= (t.hour, t.minute) < QUIET[1]


def keyboard(profile: str) -> dict:
    """Постоянное меню под полем ввода. У бота продаж — готовые отчёты по кнопкам."""
    if profile == "sales":
        from gear.app.daily_sales.assistant import menu
        return menu.keyboard()
    return {"keyboard": [[{"text": MENU["examples"]}, {"text": MENU["new"]}],
                         [{"text": MENU["help"]}]],
            "resize_keyboard": True, "is_persistent": True,
            "input_field_placeholder": "Напишите вопрос…"}


def examples_kb(profile: str) -> dict:
    """Примеры вопросов кнопками под сообщением, по две в ряд."""
    btn = [{"text": label, "callback_data": f"ex:{i}"}
           for i, (label, _) in enumerate(EXAMPLES[profile])]
    return {"inline_keyboard": [btn[i:i + 2] for i in range(0, len(btn), 2)]}


ANSWER_KB = {"inline_keyboard": [[{"text": "Прислать в Excel", "callback_data": "xl"},
                                  {"text": "Новый разговор", "callback_data": "new"}]]}


class Bot:
    def __init__(self, token: str, profile: str):
        self.token, self.profile = token, profile
        self.history: dict[int, tuple[float, list]] = {}
        self.digest_done, self.digest_try = "", 0.0     # сводка: дата отправки, время попытки
        self.purged = 0.0                        # когда последний раз чистили журнал
        self.menu_shown: set[int] = set()        # кому уже показали нижнее меню
        self.menu_rep: dict[int, str] = {}       # какой отчёт открыт: даты текстом идут в него
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

    def call(self, method: str, _wait=40, **params):
        req = urllib.request.Request(
            API.format(token=self.token, method=method),
            data=json.dumps(params).encode("utf-8"),
            headers={"content-type": "application/json"}, method="POST")
        with self.opener.open(req, timeout=_wait) as r:
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

    def send_photo(self, chat_id: int, photo, caption: str = "", silent: bool = False,
                   markup: dict | None = None):
        """photo — PNG (bytes) или file_id уже загруженной картинки. Возвращает file_id."""
        fields = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML",
                  "disable_notification": "true" if silent else "false"}
        if markup:
            fields["reply_markup"] = json.dumps(markup, ensure_ascii=False)
        if isinstance(photo, str):
            res = self.call("sendPhoto", photo=photo, **{
                k: (markup if k == "reply_markup" else v) for k, v in fields.items()})
        else:
            boundary = uuid.uuid4().hex
            body = b"".join(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
                .encode("utf-8") for k, v in fields.items()) + (
                f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; '
                f'filename="chart.png"\r\nContent-Type: image/png\r\n\r\n').encode() \
                + photo + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(
                API.format(token=self.token, method="sendPhoto"), data=body,
                headers={"content-type": f"multipart/form-data; boundary={boundary}"},
                method="POST")
            with self.opener.open(req, timeout=120) as r:
                res = json.loads(r.read().decode("utf-8"))
        sizes = (res.get("result") or {}).get("photo") or []
        return sizes[-1]["file_id"] if sizes else None

    def send_file(self, chat_id: int, data: bytes, name: str, mime: str, caption: str = ""):
        """Файл из памяти (Excel, PDF)."""
        boundary = uuid.uuid4().hex
        head = "".join(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
            for k, v in (("chat_id", chat_id), ("caption", caption), ("parse_mode", "HTML")) if v)
        body = head.encode("utf-8") + (
            f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
            f'filename="{name}"\r\nContent-Type: {mime}\r\n\r\n').encode("utf-8") \
            + data + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            API.format(token=self.token, method="sendDocument"), data=body,
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
            method="POST")
        with self.opener.open(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))

    def edit(self, chat_id: int, message_id: int | None, text: str, markup: dict | None = None):
        """Правим сообщение с кнопками; не вышло — шлём новое."""
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True}
        if markup:
            params["reply_markup"] = markup
        try:
            if message_id:
                self.call("editMessageText", message_id=message_id, **params)
                return message_id
        except urllib.error.HTTPError as e:
            if "not modified" in (e.read() or b"").decode("utf-8", "ignore"):
                return message_id
        except Exception:
            pass
        try:
            return self.call("sendMessage", **params)["result"]["message_id"]
        except Exception:
            return None

    # ---------------------------------------------------------------- отчёты по кнопкам
    def on_menu(self, cq: dict):
        """Кнопки отчётов: выбор периода, календарь, отчёт, файлы. Без ИИ."""
        from gear.app.daily_sales.assistant import menu
        try:
            self.call("answerCallbackQuery", callback_query_id=cq["id"])
        except Exception:
            pass
        msg = cq.get("message") or {}
        chat_id, mid = (msg.get("chat") or {}).get("id"), msg.get("message_id")
        parts = (cq.get("data") or "").split(":")
        op = parts[1] if len(parts) > 1 else ""
        rep = parts[2] if len(parts) > 2 else ""
        if not chat_id or op == "n" or rep not in menu.REPORTS:
            return
        obj, _ = self.access(cq.get("from") or {})
        if not obj.is_allowed:
            return
        if quiet_now():
            self.say(chat_id, "Сейчас обновляются данные — с {0:02d}:{1:02d} до {2:02d}:{3:02d} "
                              "по Москве отчёты недоступны.".format(*QUIET[0], *QUIET[1]))
            return
        hi, lo = menu.loaded(), menu.DATA_START
        self.menu_rep[chat_id] = rep
        if op == "o":
            self.edit(chat_id, mid, menu.ask_text(rep), menu.period_kb(rep))
        elif op == "p" and len(parts) > 3:
            a, b = menu.preset(parts[3], hi)
            self.menu_report(chat_id, mid, obj, rep, a, b)
        elif op in ("c", "d") and len(parts) > 3:
            if op == "d":
                start, ym = menu.from_ymd(parts[3]), parts[3][:6]
            else:
                start = menu.from_ymd(parts[4]) if len(parts) > 4 and parts[4] not in ("", "0") \
                    else None
                ym = parts[3] or f"{hi:%Y%m}"
            text = menu.ask_text(rep).split("\n")[0] + (
                f"\nНачало: <b>{start:%d.%m.%Y}</b>. Теперь нажмите <b>последний день</b>."
                if start else "\nНажмите <b>первый день</b> периода.")
            self.edit(chat_id, mid, text,
                      menu.calendar_kb(rep, int(ym[:4]), int(ym[4:6]), start, lo, hi))
        elif op == "e" and len(parts) > 4:
            a, b = sorted((menu.from_ymd(parts[3]), menu.from_ymd(parts[4])))
            self.menu_report(chat_id, mid, obj, rep, a, b)
        elif op == "f" and len(parts) > 5:
            self.menu_file(chat_id, obj, rep, parts[3], menu.from_ymd(parts[4]),
                           menu.from_ymd(parts[5]))

    def menu_file(self, chat_id: int, obj, rep: str, code: str, a, b, quiet: bool = False):
        from gear.app.daily_sales.assistant import menu
        note = None if quiet else self.status(chat_id, "Готовлю файл")
        try:
            self.call("sendChatAction", chat_id=chat_id, action="upload_document")
        except Exception:
            pass
        try:
            f = menu.file(rep, code, a, b)
            self.drop(chat_id, note)
            if not f:
                self.say(chat_id, "За этот период данных для файла нет.")
                return
            self.send_file(chat_id, f[1], f[0], f[2])
        except Exception as e:
            self.drop(chat_id, note)
            print(f"[bot sales] файл {rep}/{code}: {type(e).__name__}: {e}", flush=True)
            self.say(chat_id, "Файл собрать не получилось — попробуйте позже или другой период.")

    def menu_report(self, chat_id: int, mid, obj, rep: str, a, b):
        from gear.app.daily_sales.assistant import menu
        started = time.time()
        label = f"{menu.REPORTS[rep]} · {menu.span(a, b)}"
        mid = self.edit(chat_id, mid, f"<b>{html.escape(label)}</b>\n<i>Считаю…</i>")
        stop = threading.Event()
        threading.Thread(target=self.typing, args=(chat_id, stop), daemon=True).start()
        try:
            res = menu.build(rep, a, b)
        except Exception as e:
            stop.set()
            print(f"[bot sales] отчёт {rep}: {type(e).__name__}: {e}", flush=True)
            self.edit(chat_id, mid, f"<b>{html.escape(label)}</b>\nНе получилось посчитать — "
                                    "попробуйте позже.", menu.period_kb(rep))
            self.log(obj, f"[кнопка] {label}", started)
            return
        stop.set()
        if not res:
            self.edit(chat_id, mid, f"<b>{html.escape(label)}</b>\nЗа этот период данных нет. "
                                    "Выберите другой:", menu.period_kb(rep))
            return
        self.drop(chat_id, mid)
        text, kb = res["text"], res["kb"]
        plain = re.sub(r"<[^>]+>", "", html.unescape(text))
        sent = False
        if res.get("photo"):
            try:
                cap = text if len(plain) <= 1000 else ""
                self.send_photo(chat_id, res["photo"], cap, markup=kb if cap else None)
                sent = bool(cap)
            except Exception as e:
                print(f"[bot sales] картинка {rep}: {type(e).__name__}: {e}", flush=True)
        if not sent:
            self.say(chat_id, text, kb, raw=True)
        auto = res.get("auto") or []
        for code in ([auto] if isinstance(auto, str) else auto):
            self.menu_file(chat_id, obj, rep, code, a, b, quiet=True)
        self.log(obj, f"[кнопка] {label}", started, {"files": [1] if auto else []})
        type(obj).objects.filter(pk=obj.pk).update(
            requests=obj.requests + 1, last_seen=timezone.now())

    def send_blocks(self, chat_id: int, blocks: list[dict]):
        """Сводка: картинка с подписью, затем следующая. Звук — только у первого сообщения."""
        for k, b in enumerate(blocks):
            silent, sent = k > 0, False
            plain = re.sub(r"<[^>]+>", "", html.unescape(b["text"]))
            if b.get("photo"):
                try:
                    cap = b["text"] if len(plain) <= 1000 else ""
                    fid = self.send_photo(chat_id, b["photo"], cap, silent)
                    if fid:
                        b["photo"] = fid                 # дальше шлём без повторной загрузки
                    sent = bool(cap)
                    silent = True
                except Exception as e:
                    print(f"[bot {self.profile}] картинка сводки: {type(e).__name__}: {e}",
                          flush=True)
            if not sent:
                self.say(chat_id, b["text"], raw=True, silent=silent)
            time.sleep(0.15)

    def say(self, chat_id: int, text: str, markup: dict | None = None, raw: bool = False,
            silent: bool = False):
        parts = split(text if raw else to_html(text))
        for k, part in enumerate(parts):
            extra = {"reply_markup": markup} if markup and k == len(parts) - 1 else {}
            if silent:
                extra["disable_notification"] = True
            try:
                self.call("sendMessage", chat_id=chat_id, text=part, parse_mode="HTML",
                          disable_web_page_preview=True, **extra)
            except urllib.error.HTTPError:
                # разметка не прошла — отправляем простым текстом
                self.call("sendMessage", chat_id=chat_id,
                          text=re.sub(r"<[^>]+>", "", html.unescape(part))[:4000])

    def setup(self):
        """Меню команд и описание бота — задаются при каждом запуске."""
        for method, params in (
            ("deleteMyCommands", {}),                       # управление — кнопками
            ("setChatMenuButton", {"menu_button": {"type": "default"}}),
            ("setMyDescription", {"description": DESCRIPTION[self.profile]}),
            ("setMyShortDescription", {"short_description": ABOUT[self.profile]}),
        ):
            try:
                self.call(method, **params)
            except Exception as e:
                print(f"[bot {self.profile}] {method}: {e}", flush=True)

    def status(self, chat_id: int, text: str, message_id: int | None = None):
        """Строка «что сейчас делаю»: создаём, затем правим на каждом шаге."""
        body = f"<i>{html.escape(text)}…</i>"
        try:
            if message_id:
                self.call("editMessageText", chat_id=chat_id, message_id=message_id,
                          text=body, parse_mode="HTML")
                return message_id
            return self.call("sendMessage", chat_id=chat_id, text=body,
                             parse_mode="HTML")["result"]["message_id"]
        except Exception:
            return message_id

    def drop(self, chat_id: int, message_id: int | None):
        if message_id:
            try:
                self.call("deleteMessage", chat_id=chat_id, message_id=message_id)
            except Exception:
                pass

    def on_button(self, cq: dict):
        """Нажатие кнопки под сообщением → тот же путь, что и обычный вопрос."""
        try:
            self.call("answerCallbackQuery", callback_query_id=cq["id"])
        except Exception:
            pass
        chat = (cq.get("message") or {}).get("chat") or {}
        data = cq.get("data") or ""
        if self.profile == "sales" and data.startswith("mn:"):
            return self.on_menu(cq)
        if self.profile == "sales" and data == "ex:0" and chat.get("id") \
                and self.send_digest(chat["id"], cq.get("from") or {}):
            return
        if data.startswith("ex:") and data[3:].isdigit():
            ex = EXAMPLES[self.profile]
            text = ex[int(data[3:]) % len(ex)][1]
        else:
            text = {"xl": "Пришли это в Excel", "new": MENU["new"]}.get(data)
        if not chat.get("id") or not text:
            return
        if text != MENU["new"]:
            self.say(chat["id"], f"<b>Вопрос:</b> {html.escape(text)}", raw=True)
        self.handle({"chat": chat, "from": cq.get("from") or {}, "text": text})

    def log(self, obj, text: str, started: float, res: dict | None = None):
        """Журнал вопросов: без ответа бота; старше KEEP_DAYS — удаляем раз в сутки."""
        from datetime import timedelta
        from gear.models import TelegramQuestion
        try:
            TelegramQuestion.objects.create(
                access=obj, bot=self.profile, text=text[:4000],
                seconds=round(time.time() - started, 1),
                cost_usd=(res or {}).get("cost_usd"),
                has_file=bool((res or {}).get("files")), is_error=res is None)
            if time.time() - self.purged > 24 * 3600:
                self.purged = time.time()
                TelegramQuestion.objects.filter(asked_at__lt=timezone.now() - timedelta(
                    days=TelegramQuestion.KEEP_DAYS)).delete()
        except Exception as e:
            print(f"[bot {self.profile}] журнал: {type(e).__name__}: {e}", flush=True)

    # ---------------------------------------------------------------- сводка
    @staticmethod
    def _digest_mark():
        from pathlib import Path
        from django.conf import settings
        return Path(settings.BASE_DIR) / "data" / ".sales_digest_sent"

    def send_digest(self, chat_id: int, user: dict) -> bool:
        """Кнопка «Продажи за вчера»: та же сводка, что в рассылке, без обращения к Claude."""
        try:
            obj, _ = self.access(user)
            if not obj.is_allowed or quiet_now():
                return False                             # ответит обычный путь
            from gear.app.daily_sales.assistant import digest
            day = digest.loaded_date()
            parts = digest.blocks(day, day) if day else []
            if not parts:
                return False
            self.send_blocks(chat_id, parts)
            return True
        except Exception as e:
            print(f"[bot sales] сводка по кнопке: {type(e).__name__}: {e}", flush=True)
            return False

    def digest_tick(self):
        """Раз в день рассылаем сводку продаж; данных нет — пробуем снова через час."""
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        if self.profile != "sales":
            return
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        today = now.date().isoformat()
        if not DIGEST_HOURS[0] <= now.hour < DIGEST_HOURS[1] or self.digest_done == today:
            return
        if time.time() - self.digest_try < 3600:
            return
        mark = self._digest_mark()
        if mark.with_name(".sales_digest_off").exists():     # рассылка выключена вручную
            return
        try:
            if mark.exists() and mark.read_text().strip() == today:
                self.digest_done = today
                return
        except OSError:
            pass
        self.digest_try = time.time()
        from gear.app.daily_sales.assistant import digest, digest_period
        from gear.models import TelegramAccess
        day = now.date() - timedelta(days=1)
        loaded = digest.loaded_date()
        parts = digest_period.morning(now.date(), day, loaded)   # пн — неделя, 1-го — месяц
        if not parts:
            print(f"[bot sales] сводка: продаж за {day:%d.%m.%Y} ещё нет (в базе по "
                  f"{loaded or '—'}), повтор через час", flush=True)
            if now.hour == DIGEST_HOURS[1] - 1:              # последняя попытка дня
                admin = (os.getenv("TELEGRAM_ADMIN_ID") or "").strip()
                if admin.lstrip("-").isdigit():
                    self.say(int(admin), f"Сводка продаж за {day:%d.%m.%Y} не отправлена: "
                                         "данные так и не загрузились.", raw=True)
            return
        sent = 0
        for a in TelegramAccess.objects.filter(bot="sales", is_allowed=True):
            try:
                self.send_blocks(a.tg_id, parts)
                sent += 1
            except Exception as e:
                print(f"[bot sales] сводка → {a.tg_id}: {e}", flush=True)
            time.sleep(0.1)
        self.digest_done = today
        try:
            mark.write_text(today)
        except OSError as e:
            print(f"[bot sales] сводка: метка не записана: {e}", flush=True)
        print(f"[bot sales] сводка за {day:%d.%m.%Y} отправлена: {sent}", flush=True)

    def typing(self, chat_id: int, stop):
        """Показываем «печатает…», пока считается ответ."""
        while not stop.is_set():
            try:
                self.call("sendChatAction", chat_id=chat_id, action="typing")
            except Exception:
                pass
            stop.wait(4)

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
        first = (user.get("first_name") or "").strip()
        hello = f"Здравствуйте, {html.escape(first)}!" if first else "Здравствуйте!"
        if not obj.is_allowed:
            self.say(chat_id, (
                f"{hello} Я {NAMES[self.profile]} компании.\n\n"
                "Заявка на доступ отправлена. Как только её подтвердят, я напишу вам сам."
                if created or text == "/start" else
                "Доступ пока не подтверждён. Если ждёте давно — напишите Дарье."), raw=True)
            return
        text = {v: "/" + k for k, v in MENU.items()}.get(text, text)
        if self.profile == "sales":
            from gear.app.daily_sales.assistant import menu
            if text == menu.BTN_AI:
                self.menu_rep.pop(chat_id, None)     # дальше текст — вопрос ИИ, а не даты отчёта
                self.say(chat_id, menu.AI_TEXT, keyboard(self.profile), raw=True)
                return
            text = {menu.BTN_HELP: "/help"}.get(text, text)
            if text in menu.BY_TEXT:                 # отчёт по кнопке — без ИИ
                self.menu_shown.add(chat_id)
                rep = menu.BY_TEXT[text]
                self.menu_rep[chat_id] = rep
                self.say(chat_id, menu.ask_text(rep), menu.period_kb(rep), raw=True)
                return
            rng = menu.parse_range(text, menu.loaded()) if chat_id in self.menu_rep else None
            if rng and obj.is_allowed and not quiet_now():   # даты текстом — в открытый отчёт
                self.menu_report(chat_id, None, obj, self.menu_rep[chat_id], *rng)
                return
        if chat_id not in self.menu_shown and text != "/start":
            self.menu_shown.add(chat_id)         # после обновления бота меню ставим сами
            self.say(chat_id, "Меню — на кнопках внизу.", keyboard(self.profile), raw=True)
        if text == "/start":
            self.say(chat_id, (
                f"{hello} Я <b>{NAMES[self.profile]}</b>.\n\n{html.escape(ABOUT[self.profile])}"
                "\n\nНапишите вопрос обычными словами — или начните с примера:"),
                examples_kb(self.profile), raw=True)
            self.say(chat_id, "Меню — на кнопках внизу.", keyboard(self.profile), raw=True)
            self.menu_shown.add(chat_id)
            return
        if text == "/help":
            if self.profile == "sales":
                from gear.app.daily_sales.assistant import menu
                self.say(chat_id, menu.HELP, keyboard(self.profile), raw=True)
                return
            self.say(chat_id, HELP[self.profile], keyboard(self.profile), raw=True)
            return
        if text == "/examples":
            self.say(chat_id, "<b>Примеры вопросов</b>\nНажмите кнопку или напишите "
                              "своими словами.", examples_kb(self.profile), raw=True)
            return
        if text == "/new":
            self.history.pop(chat_id, None)
            self.say(chat_id, "Начинаем заново. Что посчитать?", examples_kb(self.profile))
            return
        if text.startswith("/"):
            self.say(chat_id, "Такой команды нет. Напишите вопрос обычными словами.",
                     keyboard(self.profile))
            return

        if quiet_now():
            self.say(chat_id, "Сейчас обновляются данные — с {0:02d}:{1:02d} до {2:02d}:{3:02d} "
                              "по Москве я не отвечаю на вопросы. Напишите, пожалуйста, "
                              "после {2:02d}:{3:02d}.".format(*QUIET[0], *QUIET[1]))
            return

        from gear.app.daily_sales.assistant.excel import file_path
        from gear.app.daily_sales.assistant.llm import AssistantError, ask

        seen, turns = self.history.get(chat_id, (0, []))
        if time.time() - seen > HISTORY_TTL:
            turns = []
        turns = turns + [{"role": "user", "content": text}]
        started = time.time()
        stop = threading.Event()
        threading.Thread(target=self.typing, args=(chat_id, stop), daemon=True).start()
        note = {"id": self.status(chat_id, "Думаю над вопросом"), "text": ""}

        def step(tool):
            label = STEPS.get(tool, STEP_DEFAULT)
            if label != note["text"]:
                note["text"] = label
                note["id"] = self.status(chat_id, label, note["id"])

        def done():
            stop.set()
            self.drop(chat_id, note["id"])
        try:
            res = ask(turns, self.profile, on_step=step)
        except AssistantError as e:
            done()
            self.say(chat_id, f"Не получилось ответить: {e}")
            self.log(obj, text, started)
            return
        except Exception as e:
            done()
            self.say(chat_id, "Не получилось ответить — попробуйте переформулировать вопрос.")
            print(f"[bot {self.profile}] ошибка: {type(e).__name__}: {e}", flush=True)
            self.log(obj, text, started)
            return
        done()
        self.log(obj, text, started, res)
        answer = res.get("text") or "(пустой ответ)"
        self.say(chat_id, answer, None if res.get("files") else ANSWER_KB)
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
        self.setup()
        print(f"[bot {self.profile}] запущен: @{me.get('username')}", flush=True)
        offset = None
        while True:
            try:
                close_old_connections()
                self.digest_tick()
            except Exception as e:
                print(f"[bot {self.profile}] сводка: {type(e).__name__}: {e}", flush=True)
            try:
                params = {"timeout": 25, "allowed_updates": ["message", "callback_query"]}
                if offset is not None:
                    params["offset"] = offset
                updates = self.call("getUpdates", _wait=40, **params).get("result", [])
            except Exception as e:
                print(f"[bot {self.profile}] нет связи с Telegram: {e}", flush=True)
                time.sleep(5)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                if "message" not in u and "callback_query" not in u:
                    continue
                close_old_connections()
                try:
                    if "message" in u:
                        self.handle(u["message"])
                    else:
                        self.on_button(u["callback_query"])
                except Exception as e:
                    print(f"[bot {self.profile}] {type(e).__name__}: {e}", flush=True)


# -------------------------------------------------------------------- текст
def _table(lines: list[str]) -> str:
    """Таблица Markdown → моноширинный блок с выровненными колонками."""
    clean = lambda c: re.sub(r"\*\*|__|`", "", c).strip()        # в <pre> разметка не работает
    rows = [[clean(c) for c in ln.strip().strip("|").split("|")] for ln in lines]
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
        parser.add_argument("--digest-preview", action="store_true",
                            help="Показать текст сводки продаж и выйти")
        parser.add_argument("--digest-test", action="store_true",
                            help="Отправить сводку с картинками только на TELEGRAM_ADMIN_ID")
        parser.add_argument("--digest-date",
                            help="Дата для предпросмотра YYYY-MM-DD; по умолчанию — "
                                 "последний загруженный день (неделя или месяц)")
        parser.add_argument("--digest-kind", choices=["day", "week", "month"],
                            help="Сводка за день, итоги недели или месяца; по умолчанию — "
                                 "как в сегодняшней рассылке (пн — неделя, 1-го — месяц)")

    @staticmethod
    def _digest_day(opts, loaded):
        """(последний день периода, вид) для --digest-test / --digest-preview."""
        from datetime import date, timedelta
        from gear.app.daily_sales.assistant import digest_period
        kind = opts.get("digest_kind") or digest_period.kinds_for(date.today())[0]
        if opts.get("digest_date"):
            day = date.fromisoformat(opts["digest_date"])
            if kind != "day":
                day = digest_period.period(kind, day)[1]
        else:
            day = loaded or date.today() - timedelta(days=1)
            if kind != "day":
                day = digest_period.last_closed(kind, day)
        if kind != "day" and loaded and day > loaded:
            raise CommandError(f"Период до {day:%d.%m.%Y} ещё не загружен (в базе по {loaded}).")
        return day, kind

    def handle(self, *args, **opts):
        profile = opts["profile"]
        if opts.get("digest_test"):
            from datetime import date, timedelta
            from gear.app.daily_sales.assistant import digest
            admin = (os.getenv("TELEGRAM_ADMIN_ID") or "").strip()
            token = (os.getenv("TELEGRAM_BOT_TOKEN_SALES") or "").strip()
            if not admin.lstrip("-").isdigit() or not token:
                raise CommandError("Нужны TELEGRAM_ADMIN_ID и TELEGRAM_BOT_TOKEN_SALES в .env")
            loaded = digest.loaded_date()
            day, kind = self._digest_day(opts, loaded)
            if kind == "day":
                parts = digest.greet(digest.blocks(day, loaded), date.today(), day)
            else:
                from gear.app.daily_sales.assistant import digest_period
                parts = digest_period.morning(day + timedelta(days=1), day, loaded, [kind])
            if not parts:
                self.stdout.write(f"Продаж за {day:%d.%m.%Y} нет (в базе по {loaded}).")
                return
            Bot(token, "sales").send_blocks(int(admin), parts)
            self.stdout.write(f"Сводка за {day:%d.%m.%Y} отправлена на {admin}: "
                              f"блоков {len(parts)}, с картинкой "
                              f"{sum(1 for b in parts if b.get('photo'))}.")
            return
        if opts.get("digest_preview"):
            from datetime import date, timedelta
            from gear.app.daily_sales.assistant import digest
            loaded = digest.loaded_date()
            day, kind = self._digest_day(opts, loaded)
            self.stdout.write(f"В базе продажи по: {loaded}")
            if kind == "day":
                text = digest.build(day, loaded)
            else:
                from gear.app.daily_sales.assistant import digest_period
                text = digest_period.build(kind, day, loaded) if loaded and loaded >= day else None
            self.stdout.write(text or f"Продаж за {day:%d.%m.%Y} нет.")
            return
        token = (os.getenv(f"TELEGRAM_BOT_TOKEN_{profile.upper()}") or "").strip()
        if not token:
            raise CommandError(f"В .env нет TELEGRAM_BOT_TOKEN_{profile.upper()}")
        try:
            Bot(token, profile).run()
        except KeyboardInterrupt:
            pass
