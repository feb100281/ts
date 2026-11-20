"""
Отбор «только компании группы Трендсеттер РФ» в скриптах ETL на сервере (/opt/wb_jobs).

    python patch_etl_gate.py /opt/wb_jobs/*.py

Правит три места: операции выписок → GL, список счетов для переоценки (из выписок и из gl.v_bank_acounts).
Перед правкой сохраняет копию <файл>.bak_<дата>. Повторный запуск ничего не меняет.
"""

import re
import shutil
import sys
from datetime import date
from pathlib import Path

MARK = "только компании группы РФ"
GROUP = "'Трендсеттер РФ'"

RULES = [
    # операции выписок, присоединённые к счетам как b
    (re.compile(r"^([ \t]*)ON t\.ba_id = b\.id[ \t]*\n(?![ \t]*JOIN public\.corporate_owners)", re.M),
     lambda m: (f"{m.group(1)}ON t.ba_id = b.id\n"
                f"{m.group(1)}JOIN public.corporate_owners o                              -- {MARK}\n"
                f"{m.group(1)}ON o.id = b.corporate_id AND o.report_group = {GROUP}\n")),
    # счета для переоценки, собранные из выписок (счёт как a)
    (re.compile(r"^([ \t]*)ON t\.ba_id = a\.id[ \t]*\n(?![ \t]*JOIN public\.corporate_owners)", re.M),
     lambda m: (f"{m.group(1)}ON t.ba_id = a.id\n"
                f"{m.group(1)}JOIN public.corporate_owners o                              -- {MARK}\n"
                f"{m.group(1)}ON o.id = a.corporate_id AND o.report_group = {GROUP}\n")),
    # счета для переоценки из gl.v_bank_acounts
    (re.compile(r"FROM gl\.v_bank_acounts;"),
     lambda m: (f"FROM gl.v_bank_acounts v                                      -- {MARK}\n"
                f"    WHERE v.ba_id IN (SELECT b.id FROM public.corporate_bankaccount b\n"
                f"                      JOIN public.corporate_owners o ON o.id = b.corporate_id\n"
                f"                      WHERE o.report_group = {GROUP});")),
]


def patch(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if "treasury_cfdata" not in text and "v_bank_acounts" not in text:
        return "не касается выписок — пропущен"
    new, total = text, 0
    for rx, repl in RULES:
        new, n = rx.subn(repl, new)
        total += n
    if not total:
        return "уже исправлен" if MARK in text else "нечего править"
    backup = path.with_name(f"{path.name}.bak_{date.today():%Y%m%d}")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(new, encoding="utf-8")
    return f"исправлено мест: {total}, копия: {backup.name}"


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_file() and p.suffix == ".py":
            print(f"{p.name}: {patch(p)}")
