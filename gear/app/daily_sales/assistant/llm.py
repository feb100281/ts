# gear/app/daily_sales/assistant/llm.py
"""Вызов Claude API без внешних пакетов (urllib) + цикл инструментов."""
from __future__ import annotations

import json
from datetime import date
import re
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from .prompt import system_prompt
from .tools import allowed, call_tool, tools_for

log = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-5"
MAX_TOOL_ROUNDS = 8
MAX_TOKENS = 2000
HTTP_TIMEOUT = 90
CACHE_TTL = "1h"             # сколько Claude помнит инструкцию: "1h" или "5m"
_cache_ttl = [CACHE_TTL]     # сбрасывается в "5m", если API не принял часовой кэш

# $ за 1 млн токенов (вход, выход) — для оценки стоимости ответа
PRICES = {
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


class AssistantError(Exception):
    pass


def _model() -> str:
    return os.getenv("ASSISTANT_MODEL", DEFAULT_MODEL)


def _opener():
    """Подключение к API: напрямую, через HTTP-прокси или через SOCKS5.

    ANTHROPIC_PROXY=http://user:pass@host:port   — HTTP(S)-прокси
    ANTHROPIC_PROXY=socks5://127.0.0.1:1080      — SOCKS5, например ssh -D 1080
    """
    proxy = (os.getenv("ANTHROPIC_PROXY") or "").strip()
    if not proxy:
        return urllib.request.build_opener()
    if proxy.startswith("socks"):
        try:
            import socks
            from sockshandler import SocksiPyHandler
        except ImportError as e:
            raise AssistantError(
                "Для SOCKS-прокси нужен пакет PySocks: pip install pysocks") from e
        u = urllib.parse.urlparse(proxy)
        return urllib.request.build_opener(SocksiPyHandler(
            socks.SOCKS5, u.hostname or "127.0.0.1", u.port or 1080,
            rdns=True, username=u.username, password=u.password))
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"https": proxy, "http": proxy}))


def _post(payload: dict) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise AssistantError(
            "Не задан ключ ANTHROPIC_API_KEY в .env — добавьте его и "
            "перезапустите дашборд.")
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    opener = _opener()
    try:
        with opener.open(req, timeout=HTTP_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:500]
        if e.code == 403:
            raise AssistantError(
                "Claude API недоступен из текущего региона (403). Включите VPN "
                "на компьютере или задайте ANTHROPIC_PROXY в .env и перезапустите "
                "дашборд.") from e
        if e.code == 401:
            raise AssistantError("Ключ ANTHROPIC_API_KEY не принят (401) — "
                                 "проверьте, что он вставлен полностью.") from e
        raise AssistantError(f"Claude API ответил {e.code}: {body}") from e
    except urllib.error.URLError as e:
        hint = (" Проверьте, что туннель запущен: ssh -D 1080 -N …"
                if (os.getenv("ANTHROPIC_PROXY") or "").startswith("socks") else "")
        raise AssistantError(f"Нет связи с Claude API: {e.reason}.{hint}") from e


_FIG = re.compile(r"\d[\d\s .,]*\s?(₽|руб|тыс|млн|млрд|шт\b|%)|\|\s*[−-]?\d", re.I)


def _cache_control() -> dict:
    cc = {"type": "ephemeral"}
    if _cache_ttl[0] == "1h":
        cc["ttl"] = "1h"
    return cc


def _has_figures(text: str) -> bool:
    """В тексте есть суммы, штуки, проценты или таблица с числами."""
    return bool(_FIG.search(text or ""))


_YEAR_HINT = re.compile(r"20\d\d|год|\bлет\b|\d+\s*месяц|за\s+вс[её]\s+время|позапрошл", re.I)
_ISO = re.compile(r"^(20\d\d)-(\d\d)")


def _stale_year(args: dict, asked: str) -> int | None:
    """Год в параметрах инструмента старше 12 месяцев, хотя в диалоге год не называли."""
    if _YEAR_HINT.search(asked or ""):
        return None
    t = date.today()
    for v in (args or {}).values():
        m = _ISO.match(v) if isinstance(v, str) else None
        if m and (t.year - int(m[1])) * 12 + t.month - int(m[2]) > 12:
            return int(m[1])
    return None


def ask(history: list[dict], profile: str = "sales", on_step=None) -> dict:
    """history: [{"role": "user"|"assistant", "content": str}, ...]

    Возвращает {"text", "sql": [..], "usage": {...}, "cost_usd"}.
    """
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    usage = {"input": 0, "output": 0, "cache_read": 0, "write_extra": 0.0}
    sql_log: list[str] = []
    files: list[dict] = []
    question = next((m["content"] for m in reversed(history)
                     if m["role"] == "user"), "")
    asked = " ".join(m["content"] for m in history
                     if m["role"] == "user" and isinstance(m["content"], str))
    model = _model()

    tools_called = 0        # сколько раз за этот ответ помощник обращался к данным
    forced = False          # повторный запрос с обязательным вызовом инструмента

    for _ in range(MAX_TOOL_ROUNDS + 2):
        payload = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": system_prompt(profile),
                        "cache_control": _cache_control()}],
            "tools": tools_for(profile),
            "messages": messages,
        }
        if forced and tools_called == 0:
            payload["tool_choice"] = {"type": "any"}
        try:
            resp = _post(payload)
        except AssistantError as e:
            if _cache_ttl[0] == "5m" or "ttl" not in str(e).lower():
                raise
            print("[assistant] часовой кэш не принят — работаем с 5 минутами", flush=True)
            _cache_ttl[0] = "5m"
            payload["system"][0]["cache_control"] = _cache_control()
            resp = _post(payload)
        u = resp.get("usage", {})
        written = u.get("cache_creation_input_tokens", 0)
        usage["input"] += u.get("input_tokens", 0) + written
        # запись в кэш дороже обычного входа: ×2 на час, ×1,25 на 5 минут
        usage["write_extra"] += written * (1.0 if _cache_ttl[0] == "1h" else 0.25)
        usage["cache_read"] += u.get("cache_read_input_tokens", 0)
        usage["output"] += u.get("output_tokens", 0)

        content = resp.get("content", [])
        messages.append({"role": "assistant", "content": content})

        tool_uses = [b for b in content if b.get("type") == "tool_use"]
        if resp.get("stop_reason") != "tool_use" or not tool_uses:
            text = "\n\n".join(b["text"] for b in content if b.get("type") == "text")
            # цифры без обращения к данным — выдумка: заставляем вызвать инструмент
            if tools_called == 0 and not forced and _has_figures(text):
                print("[assistant] ответ с цифрами без инструмента — повтор с обязательным "
                      "вызовом", flush=True)
                forced = True
                messages.pop()                       # выдуманный ответ в диалог не идёт
                messages.append({"role": "assistant", "content": "Сейчас посмотрю по данным."})
                messages.append({"role": "user", "content":
                                 "Вызови подходящий инструмент и ответь только по его "
                                 "результату. Если данных нет — так и скажи."})
                continue
            break
        tools_called += len(tool_uses)

        results = []
        for b in tool_uses:
            if on_step:                                  # индикатор работы (Telegram)
                try:
                    on_step(b["name"])
                except Exception:
                    pass
            if b["name"] == "run_sql":
                sql_log.append(b["input"].get("sql", ""))
                print("[assistant] SQL:\n" + sql_log[-1], flush=True)
            if not allowed(profile, b["name"]):
                out, is_err = "Инструмент недоступен в этом помощнике.", True
            elif b["name"] == "export_excel":
                try:
                    from .excel import export
                    args = dict(b.get("input", {}))
                    if profile != "finance":
                        args.pop("pl", None)
                    out, info = export(args, question)
                    files.append(info)
                    is_err = False
                except Exception as e:
                    log.exception("export_excel")
                    out, is_err = f"Ошибка выгрузки: {e}"[:2000], True
            elif b["name"] != "run_sql" and _stale_year(b.get("input", {}), asked):
                y = _stale_year(b.get("input", {}), asked)
                out, is_err = (f"Год в вопросе не назван, значит нужен текущий — "
                               f"{date.today().year}, а запрошен {y}. Повтори вызов с датами "
                               f"{date.today().year} года (месяц, который ещё не наступил, — "
                               "последний прошедший)."), True
            else:
                out, is_err = call_tool(b["name"], b.get("input", {}))
            log.info("assistant tool %s err=%s", b["name"], is_err)
            # в консоль: что вызвал помощник и начало ответа инструмента — для сверки
            print(f"[assistant] {b['name']} {b.get('input', {})}\n"
                  f"{str(out)[:1500]}\n[assistant] --- конец ответа инструмента", flush=True)
            results.append({"type": "tool_result", "tool_use_id": b["id"],
                            "content": out, "is_error": is_err})
        messages.append({"role": "user", "content": results})
    else:
        text = "Не успел уложиться в лимит шагов — уточните вопрос."

    pin, pout = PRICES.get(model, (None, None))
    cost = None
    if pin is not None:
        cost = ((usage["input"] + usage["write_extra"]) * pin + usage["cache_read"] * pin * 0.1
                + usage["output"] * pout) / 1_000_000
    return {"text": text or "(пустой ответ)", "sql": sql_log, "files": files,
            "usage": usage, "cost_usd": cost}
