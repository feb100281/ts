#!/bin/bash
# Управленческий пакет по компаниям на ТЕСТОВОЙ базе ts_test.
# Свежая аналитическая база берётся копией с сервера (рабочая не трогается).

TS="$HOME/Documents/Projects/ts"
SERVER="daria@82.202.197.94"
OUT="$HOME/Desktop/Пакеты — тест"
DATE="${1:-2026-10-31}"
export DB_NAME=ts_test

clear
cd "$TS" || exit 1
source venv/bin/activate || exit 1

if ! nc -z 127.0.0.1 5433 2>/dev/null; then
    echo "Нет туннеля к базе (порт 5433). Откройте его в отдельном окне:"
    echo "  ssh -N -L 5433:localhost:5432 $SERVER"
    read -n 1 -s -r -p "Нажмите любую клавишу…"; exit 1
fi
DB=$(python manage.py shell -c "from django.db import connection; print(connection.settings_dict['NAME'])" 2>/dev/null | tail -1)
[ "$DB" != "ts_test" ] && { echo "Стоп: база «$DB», не ts_test"; read -n 1 -s -r; exit 1; }

LOCAL="$TS/analytics/analytics_test.duckdb"
if [ ! -f "$LOCAL" ] || [ -n "$(find "$LOCAL" -mtime +1 2>/dev/null)" ]; then
    echo "Ищу аналитическую базу на сервере…"
    REMOTE=$(ssh "$SERVER" "ls -t /opt/*/analytics/analytics.duckdb /home/*/*/analytics/analytics.duckdb /srv/*/analytics/analytics.duckdb /var/www/*/analytics/analytics.duckdb 2>/dev/null | head -1")
    if [ -z "$REMOTE" ]; then
        echo "Не нашла analytics.duckdb на сервере — пришлите мне этот текст."
        read -n 1 -s -r; exit 1
    fi
    echo "Копирую $REMOTE …"
    mkdir -p "$TS/analytics"
    scp -O "$SERVER:$REMOTE" "$LOCAL" || { echo "Копирование не удалось"; read -n 1 -s -r; exit 1; }
fi
export DUCKDB_PATH="$LOCAL"

python manage.py migrate > /dev/null || { read -n 1 -s -r -p "Миграции не прошли."; exit 1; }
mkdir -p "$OUT"
for C in ru am_amd am_rub all; do
    echo "------------------------------------------------------------"
    echo "Пакет: $C на $DATE"
    python manage.py mp "$DATE" --company "$C" --out "$OUT/manpack_${DATE}_$C.xlsx" 2>&1 | tail -4
done
echo "------------------------------------------------------------"
open "$OUT"
read -n 1 -s -r -p "Готово. Напишите в чат «готово» и пришлите, если были ошибки."
