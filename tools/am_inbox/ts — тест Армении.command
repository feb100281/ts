#!/bin/bash
# ts на ТЕСТОВОЙ копии базы (ts_test): миграции, загрузка выписок Армении, админка в браузере.
# Рабочая база ts_db не используется.

TS="$HOME/Documents/Projects/ts"
ST="$HOME/Desktop/ТРЕНДСЕТТЕР/10 Армения/01 Банковские выписки"
SA="$HOME/Desktop/ТРЕНДСЕТТЕР/10 Армения/02 Продажи"
PORT=8001
export DB_NAME=ts_test                      # главное: только тестовая база

clear
cd "$TS" || exit 1
source venv/bin/activate || exit 1

if ! nc -z 127.0.0.1 5433 2>/dev/null; then
    echo "Нет туннеля к базе (порт 5433). Откройте его в отдельном окне:"
    echo "  ssh -N -L 5433:localhost:5432 daria@82.202.197.94"
    read -n 1 -s -r -p "Нажмите любую клавишу…"; exit 1
fi

DB=$(python manage.py shell -c "from django.db import connection; print(connection.settings_dict['NAME'])" 2>/dev/null | tail -1)
if [ "$DB" != "ts_test" ]; then
    echo "Стоп: подключение не к ts_test, а к «$DB». Ничего не делаю."
    read -n 1 -s -r -p "Нажмите любую клавишу…"; exit 1
fi
echo "База: $DB (тестовая)"
echo "------------------------------------------------------------"
python manage.py migrate || { read -n 1 -s -r -p "Миграции не прошли — пришлите вывод выше."; exit 1; }
echo "------------------------------------------------------------"
python manage.py am_load "$ST" "$SA"
echo "------------------------------------------------------------"
python manage.py dump_views "$TS/tools/am_inbox/views_dump.sql"
echo "------------------------------------------------------------"
( sleep 3; open "http://127.0.0.1:$PORT/admin/treasury/bankstatements/" ) &
echo "Админка: http://127.0.0.1:$PORT/admin/   (остановить — закрыть окно)"
python manage.py runserver $PORT
