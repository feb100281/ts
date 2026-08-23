# gear/app/daily_sales/pricing_strategy/state.py
"""
СЕРВЕРНЫЙ КЭШ РАСЧЁТА.

Зачем он нужен.

Раньше весь результат анализа целиком лежал в dcc.Store,
то есть в браузере. На реальном ассортименте это:

    ~3 000 артикулов
    × до 90 дней истории       = ~250 000 строк
    + 17 сценариев на артикул  = ~50 000 строк

В JSON это десятки мегабайт. Store отдаёт своё содержимое
серверу при КАЖДОМ обращении callback-а, у которого он
указан в State. Нажатие кнопки «Скачать» превращалось в
пересылку этих десятков мегабайт туда и обратно — запрос
успевал отвалиться по таймауту, и снаружи это выглядело
как «кнопка не работает».

Теперь в браузере остаётся только то, что нужно для
отрисовки таблиц, а история и сценарии живут в памяти
процесса. Store хранит ключ.

Ограничения, о которых честно стоит помнить:

    — кэш живёт в памяти процесса. Перезапуск сервера или
      второй воркер = промах по ключу. Поэтому callback-и
      обязаны корректно обрабатывать промах и просить
      построить анализ заново, а не падать;
    — держим только несколько последних расчётов, иначе
      память утечёт;
    — это не хранилище данных, а именно кэш одного экрана.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict


# Сколько расчётов держим одновременно.
# Три — это «мой текущий, мой предыдущий и коллеги рядом».
MAX_ENTRIES = 3


_LOCK = threading.Lock()

_CACHE: "OrderedDict[str, dict]" = OrderedDict()


def put(payload: dict) -> str:
    """Кладёт расчёт в кэш и возвращает ключ."""

    key = uuid.uuid4().hex

    with _LOCK:
        _CACHE[key] = payload

        while len(_CACHE) > MAX_ENTRIES:
            _CACHE.popitem(last=False)

    return key


def get(key):
    """Достаёт расчёт по ключу. None, если его уже нет."""

    if not key:
        return None

    with _LOCK:
        payload = _CACHE.get(key)

        if payload is not None:
            # Освежаем позицию: активный расчёт не должен
            # вытесняться просто потому, что он старый.
            _CACHE.move_to_end(key)

        return payload


def drop(key) -> None:
    with _LOCK:
        _CACHE.pop(key, None)


def clear() -> None:
    with _LOCK:
        _CACHE.clear()
