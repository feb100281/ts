#!/bin/bash
# Предварительный отчёт: Армения (ДДС, продажи, остатки) и консолидация ДДС с РФ. База ts_test.

TS="$HOME/Documents/Projects/ts"
OUT="$HOME/Desktop/Армения — предварительный отчёт.xlsx"
export DB_NAME=ts_test

clear
cd "$TS" || exit 1
source venv/bin/activate || exit 1

if ! nc -z 127.0.0.1 5433 2>/dev/null; then
    echo "Нет туннеля к базе (порт 5433). Откройте его в отдельном окне:"
    echo "  ssh -N -L 5433:localhost:5432 daria@82.202.197.94"
    read -n 1 -s -r -p "Нажмите любую клавишу…"; exit 1
fi

FROM=$(python manage.py shell -c "
from datetime import timedelta, date
from django.db.models import Max
from macro.models import CurrencyRate
d = CurrencyRate.objects.filter(currency='AMD').aggregate(m=Max('date'))['m']
print((d + timedelta(days=1)) if d and d >= date(2026, 8, 1) else '2026-08-25')
" 2>/dev/null | tail -1)
TODAY=$(date +%F)
if [[ "$FROM" < "$TODAY" || "$FROM" == "$TODAY" ]]; then
    echo "Курсы ЦБ РФ с $FROM по $TODAY…"
    python manage.py load_currency_rates --from "$FROM" --to "$TODAY" --currencies AMD,USD,EUR,KZT > /dev/null
fi
echo "Строю отчёт…"
python manage.py am_preview "$OUT" && open "$OUT"
read -n 1 -s -r -p "Готово. Нажмите любую клавишу, чтобы закрыть окно."
