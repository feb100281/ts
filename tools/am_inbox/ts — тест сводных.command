#!/bin/bash
# Книга со сводными по компаниям на ТЕСТОВОЙ базе ts_test (аналитическая база — копия с сервера).
TS="$HOME/Documents/Projects/ts"
OUT="$HOME/Desktop/Пакеты — тест"
DATE="${1:-2026-10-31}"
export DB_NAME=ts_test
export DUCKDB_PATH="$TS/analytics/analytics_test.duckdb"
clear
cd "$TS" || exit 1
source venv/bin/activate || exit 1
if ! nc -z 127.0.0.1 5433 2>/dev/null; then
    echo "Нет туннеля к базе (порт 5433). Откройте его в отдельном окне:"
    echo "  ssh -N -L 5433:localhost:5432 daria@82.202.197.94"
    read -n 1 -s -r -p "Нажмите любую клавишу…"; exit 1
fi
[ -f "$DUCKDB_PATH" ] || { echo "Нет копии аналитической базы — сначала «ts — тест пакета»"; read -n 1 -s -r; exit 1; }
mkdir -p "$OUT"
echo "Варианты «Компания» в окне пакета:"
python manage.py shell -c "from gear.management.commands.sql.scope import options; [print('  ', v, '—', t) for v, t in options()]" 2>&1 | tail -8
for C in all "Армения|AMD" ru; do
    echo "Сводные: $C"
    python manage.py shell -c "
from gear.management.commands.mp import build_pivots_workbook
print(build_pivots_workbook('$DATE', out_path='$OUT/pivots_${DATE}_${C//|/_}.xlsx', company='$C'))
" 2>&1 | tail -3
done
read -n 1 -s -r -p "Готово. Напишите в чат «готово»."
