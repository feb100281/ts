"""
Отбор «только компании группы Трендсеттер РФ» в скриптах ETL на сервере (/opt/wb_jobs).

    python patch_etl_gate.py /opt/wb_jobs/*.py

Ищет присоединение счетов к операциям выписок (ON t.ba_id = b.id) и добавляет JOIN по компании.
Перед правкой сохраняет копию <файл>.bak_<дата>. Повторный запуск ничего не меняет.
"""

import re
import shutil
import sys
from datetime import date
from pathlib import Path

MARK = "только компании группы РФ"
PATTERN = re.compile(r"^([ \t]*)ON t\.ba_id = b\.id[ \t]*$", re.M)


def gate(indent: str) -> str:
    return (f"{indent}ON t.ba_id = b.id\n"
            f"{indent}JOIN public.corporate_owners o                              -- {MARK}\n"
            f"{indent}ON o.id = b.corporate_id AND o.report_group = 'Трендсеттер РФ'")


def patch(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if "treasury_cfdata" not in text or not PATTERN.search(text):
        return "не касается выписок — пропущен"
    if MARK in text:
        return "уже исправлен"
    new, n = PATTERN.subn(lambda m: gate(m.group(1)), text)
    backup = path.with_name(f"{path.name}.bak_{date.today():%Y%m%d}")
    shutil.copy2(path, backup)
    path.write_text(new, encoding="utf-8")
    return f"исправлено мест: {n}, копия: {backup.name}"


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_file() and p.suffix == ".py":
            print(f"{p.name}: {patch(p)}")
