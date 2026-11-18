#!/bin/bash
# Сотрудники Армении на сервере. Вызывается кнопкой «02».

TS="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$TS/venv/bin/python"
[ -x "$PY" ] || PY="$TS/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

echo "Армения: сотрудники"
echo
cd "$TS/tools/am_inbox" && "$PY" am_staff_call.py --env "$TS/.env"
