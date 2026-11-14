"""Прогон расчёта главной книги (как на сервере) на тестовой базе ts_test через туннель.

Берёт серверные скрипты из utils/etl/server, пути расчётов /opt/wb_jobs/… подменяет
на локальные. Работает только с ts_test.
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "utils" / "etl" / "server"
sys.path.insert(0, str(SERVER))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
os.environ["DB_NAME"] = "ts_test"

import ba_etl  # noqa: E402
import engine  # noqa: E402
import gl_etl  # noqa: E402

_load = engine.load_function


def load_local(path, func_name="main"):
    return _load(str(path).replace("/opt/wb_jobs/", f"{SERVER}/"), func_name)


engine.load_function = load_local

_accounts = ba_etl.fletch_accounts
ba_etl.fletch_accounts = lambda conn: [a for a in _accounts(conn) if a["acc_id"] is not None]

_connect = gl_etl.connect_db


def connect_checked():
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        db = cur.fetchone()[0]
    if db != "ts_test":
        conn.close()
        raise SystemExit(f"Стоп: подключение к «{db}», а не к ts_test")
    return conn


gl_etl.connect_db = connect_checked

if "--ru-only" in sys.argv:                       # контрольный расчёт: только счета с балансовым счётом
    import inspect
    src = inspect.getsource(ba_etl.insert_normizized)
    old = "ON t.ba_id = b.id"
    if src.count(old) != 1:
        raise SystemExit("не нашла место для фильтра в insert_normizized")
    exec(src.replace(old, old + " AND b.bs_acc_id IS NOT NULL"), ba_etl.__dict__)

if __name__ == "__main__":
    t = time.time()
    print("Расчёт главной книги на ts_test…", flush=True)
    gl_etl.main()
    print(f"Готово за {time.time() - t:.0f} с", flush=True)
