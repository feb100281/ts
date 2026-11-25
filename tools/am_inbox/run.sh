#!/bin/bash
# Раскладка и отправка файлов Армении. Вызывается кнопкой с рабочего стола.

TS="$(cd "$(dirname "$0")/../.." && pwd)"
ROOT="$HOME/Desktop/ТРЕНДСЕТТЕР/10 Армения"
ST="$ROOT/01 Банковские выписки"
SA="$ROOT/02 Продажи"

PY="$TS/venv/bin/python"
[ -x "$PY" ] || PY="$TS/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

echo "Армения: раскладка и загрузка"
echo
"$PY" "$TS/tools/am_inbox/am_sort.py" --statements "$ST" --sales "$SA"
echo
"$PY" "$TS/tools/am_inbox/am_upload.py" --statements "$ST" --sales "$SA" --env "$TS/.env"
