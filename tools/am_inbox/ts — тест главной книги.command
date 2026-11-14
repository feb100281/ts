#!/bin/bash
# Главная книга на ТЕСТОВОЙ базе ts_test: расчёт до и после заведения армянских счетов, сверка.

TS="$HOME/Documents/Projects/ts"
D="$TS/tools/am_inbox"
export DB_NAME=ts_test

clear
cd "$TS" || exit 1
source venv/bin/activate || exit 1

if ! nc -z 127.0.0.1 5433 2>/dev/null; then
    echo "Нет туннеля к базе (порт 5433). Откройте его в отдельном окне:"
    echo "  ssh -N -L 5433:localhost:5432 daria@82.202.197.94"
    read -n 1 -s -r -p "Нажмите любую клавишу…"; exit 1
fi
DB=$(python manage.py shell -c "from django.db import connection; print(connection.settings_dict['NAME'])" 2>/dev/null | tail -1)
[ "$DB" != "ts_test" ] && { echo "Стоп: база «$DB», не ts_test"; read -n 1 -s -r; exit 1; }

python manage.py migrate || { read -n 1 -s -r -p "Миграции не прошли — пришлите вывод выше."; exit 1; }
echo "------------------------------------------------------------"
echo "1/2 Счета и статьи для Армении"
python manage.py am_coa 2>&1 | tee "$D/gl_coa.log"
echo "------------------------------------------------------------"
echo "2/2 Расчёт главной книги"
python "$D/gl_test.py" 2>&1 | grep -v "read_sql\|депозиты разнесены\|^good$\|^OK$\|^ok$\|cash loans" | tee "$D/gl_run_2.log"
python manage.py gl_probe "$D/gl_probe_2.txt"
echo "------------------------------------------------------------"
read -n 1 -s -r -p "Готово. Напишите в чат «готово». Нажмите любую клавишу, чтобы закрыть окно."
