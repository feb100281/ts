#!/bin/bash
# Кнопка: раскладка выписок российских банков по папкам.
clear
TS="$HOME/Documents/Projects/ts"
PY="$TS/venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"
"$PY" "$TS/tools/rf_inbox/rf_sort.py" --root "$HOME/Desktop/ТРЕНДСЕТТЕР/01 Банковские выписки"
echo
read -n 1 -s -r -p "Готово. Нажмите любую клавишу, чтобы закрыть окно."
echo
