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
отрисовки таблиц, а история и сценарии живут на сервере.
Store хранит ключ.

Раньше кэш был обычным dict-ом в памяти процесса. Проблема:
Django-сервер в режиме разработки перезапускает рабочий
процесс при КАЖДОМ сохранении .py-файла (autoreload), а в
проде обычно поднято несколько worker-процессов gunicorn —
у каждого своя память. В обоих случаях запрос, который
кладёт расчёт в кэш, и запрос, который его потом читает
(клик по строке), очень легко оказываются в разных
процессах — и кэш промахивается почти при каждом клике,
а не только «после перезапуска».

Поэтому кэш хранится на диске, в SQLite-файле рядом с этим
модулем. Файл общий для всех процессов на одной машине
(reloader и его дочерний процесс, все worker-ы gunicorn),
поэтому:

    — сохранение файла и автоперезапуск dev-сервера больше
      не роняют текущий расчёт;
    — несколько worker-процессов в проде видят один и тот же
      кэш, а не каждый свой;
    — при этом это по-прежнему именно кэш одного экрана, а
      не хранилище данных: держим только несколько последних
      расчётов и не даём никаких гарантий сохранности после
      перезапуска ОС/контейнера или ручной очистки файла.

Callback-и всё равно обязаны корректно обрабатывать промах
(get() вернул None) и просить построить анализ заново, а не
падать — полностью исключить промах (гонка на запись,
удалённый файл кэша, параллельный перезапуск) нельзя.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path


# Сколько расчётов держим одновременно.
# Три — это «мой текущий, мой предыдущий и коллеги рядом».
MAX_ENTRIES = 3

# Файл кэша лежит рядом с модулем, а не во временной папке
# ОС: во временной папке его иногда чистят между
# перезапусками контейнера, а нам как раз важно пережить
# перезапуск процесса.
_CACHE_DIR = Path(__file__).resolve().parent / "_cache"
_CACHE_PATH = _CACHE_DIR / "pricing_strategy_cache.sqlite3"

_LOCK = threading.Lock()

_local = threading.local()


def _connection() -> sqlite3.Connection:
    """
    Соединение с БД кэша, одно на поток.

    sqlite3.Connection нельзя свободно передавать между
    потоками, а Dash/Django могут обслуживать запросы в
    разных потоках одного процесса — поэтому держим
    соединение в threading.local, а не одно на модуль.
    """

    conn = getattr(_local, "conn", None)

    if conn is not None:
        return conn

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        _CACHE_PATH,
        timeout=30,
        isolation_level=None,
    )

    # WAL пускает параллельные чтения, пока идёт запись —
    # без этого клик мог бы ждать, пока другой процесс
    # кладёт в кэш свежий расчёт.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            touched_at REAL NOT NULL
        )
        """
    )

    _local.conn = conn

    return conn


def put(payload: dict) -> str:
    """Кладёт расчёт в кэш и возвращает ключ."""

    key = uuid.uuid4().hex
    body = json.dumps(payload)

    with _LOCK:
        conn = _connection()

        conn.execute(
            "INSERT INTO cache (key, payload, touched_at) "
            "VALUES (?, ?, ?)",
            (key, body, time.time()),
        )

        conn.execute(
            """
            DELETE FROM cache
            WHERE key NOT IN (
                SELECT key FROM cache
                ORDER BY touched_at DESC
                LIMIT ?
            )
            """,
            (MAX_ENTRIES,),
        )

    return key


def get(key):
    """Достаёт расчёт по ключу. None, если его уже нет."""

    if not key:
        return None

    with _LOCK:
        conn = _connection()

        row = conn.execute(
            "SELECT payload FROM cache WHERE key = ?",
            (key,),
        ).fetchone()

        if row is None:
            return None

        # Освежаем позицию: активный расчёт не должен
        # вытесняться просто потому, что он старый.
        conn.execute(
            "UPDATE cache SET touched_at = ? WHERE key = ?",
            (time.time(), key),
        )

    return json.loads(row[0])


def drop(key) -> None:
    if not key:
        return

    with _LOCK:
        _connection().execute(
            "DELETE FROM cache WHERE key = ?",
            (key,),
        )


def clear() -> None:
    with _LOCK:
        _connection().execute("DELETE FROM cache")
