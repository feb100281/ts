#!/usr/bin/env python3

#-----------------
# Скрипт обновляет курсовые разницы по валютным счетам
# записывет курсовые разницы в PL
# записывает баланс по счетам
#-----------------

import os
from datetime import datetime, timedelta, timezone
import psycopg

BA_NAMESPACE = '21111111-1111-1111-1111-111111111111'
FX_NAMESPACE = '22111111-1111-1111-1111-111111111111'

# --------------------
# Helpers
# --------------------
def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is not set")
    return v

# def connect_db():
#     return psycopg.connect(
#         dbname=get_env("ts_db"), #DB_NAME
#         user=get_env("ts_user"), #DB_USER
#         password=get_env("Dec8108079"), #DB_PASSWORD
#         host=get_env("127.0.0.1"), #DB_HOST
#         port=get_env("5433"), #DB_PORT
#         connect_timeout=10,
#     )


def connect_db():
    return psycopg.connect(
        dbname="ts_db",  # DB_NAME
        user="ts_user",  # DB_USER
        password="Dec8108079",  # DB_PASSWORD
        host="127.0.0.1",  # DB_HOST
        port="5433",  # DB_PORT
        connect_timeout=10,
    )

SHCEMA = "gl"


