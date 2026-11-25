#!/bin/bash
# Выгрузка справочников для разноски Армении (только чтение рабочей базы).
TS="$HOME/Documents/Projects/ts"
clear
cd "$TS" || exit 1
source venv/bin/activate 2>/dev/null || source .venv/bin/activate || exit 1
if ! nc -z 127.0.0.1 5433 2>/dev/null; then
    echo "Нет туннеля к базе (порт 5433). Откройте его в отдельном окне:"
    echo "  ssh -N -L 5433:localhost:5432 daria@82.202.197.94"
    read -n 1 -s -r -p "Нажмите любую клавишу…"; exit 1
fi
python manage.py am_ref "$TS/tools/am_inbox/am_ref.txt"
read -n 1 -s -r -p "Готово. Напишите в чат «готово»."
