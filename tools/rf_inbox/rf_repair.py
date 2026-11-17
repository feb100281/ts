"""Исправление раскладки PDF от 17.11.2026: PDF, получившие период по датам внутри файла,
переносятся к своей паре txt (то же исходное имя в той же исходной папке), иначе — по дате из имени.
Работает по «_журнал раскладки.csv». Запуск: python rf_repair.py --root <папка> [--dry-run]"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
import rf_sort as R  # noqa: E402


def key(path: str):
    p = PurePosixPath(path)
    return str(p.parent), re.sub(r"[^0-9a-zа-яё]", "", R.nfc(p.stem).casefold())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).expanduser()
    rows = list(csv.reader((root / R.JOURNAL).open(encoding="utf-8-sig"), delimiter=";"))[1:]
    txt = {key(r[1]): r[2] for r in rows if r[1].lower().endswith(".txt") and r[3] == "1С"}
    moves, log = [], []
    for when, src, dst, how in rows:
        if not src.lower().endswith(".pdf") or how != "содержимое":
            continue
        cur = root / dst
        if not cur.exists():
            continue
        twin = txt.get(key(src))
        acc_dir = lambda x: next((q for q in PurePosixPath(x).parts if re.match(r"[A-Z]{3} \d{20}$", q)), None)
        if twin and acc_dir(twin) != acc_dir(dst):
            twin = None                            # счёт в самом PDF другой — пара перепутана, верим PDF
        if twin:
            new = (root / twin).with_suffix(".pdf")
            why = "пара txt"
        else:
            m = R.OUR.match(cur.name)
            if m and m.group(4):
                span = (R.mk(*m.groups()[3:6]) - R.mk(*m.groups()[:3])).days
                if span <= 45:                     # период по содержимому правдоподобный — оставляем
                    continue
            d1, d2 = R.name_dates(PurePosixPath(src).name)
            parts = PurePosixPath(dst).parts
            cut = next(i for i, x in enumerate(parts) if re.fullmatch(r"\d{4}|ПРОЧЕЕ", x))
            base = root.joinpath(*parts[:cut])
            if d1 is None:
                new, why = base / R.OTHER / PurePosixPath(src).name, "без даты"
            else:
                new = base / f"{d1:%Y}" / f"{d1:%m}. {R.MONTHS[d1.month - 1]}" / \
                    f"{d1:%Y-%m-%d}{R.note(PurePosixPath(src).name)}.pdf"
                why = "дата из имени"
        if new == cur:
            continue
        n = 2
        while new.exists() and new != cur:
            if R.sha1(new) == R.sha1(cur):
                new = R.free_name(root / R.DUPS / cur.name) if hasattr(R, "free_name") else root / R.DUPS / cur.name
                why = "дубль"
                break
            new = new.with_name(f"{new.stem.split(' (')[0]} ({n}){new.suffix}")
            n += 1
        print(f"  {cur.relative_to(root)}  →  {new.relative_to(root)}   [{why}]")
        log.append([datetime.now().strftime("%Y-%m-%d %H:%M"), str(cur.relative_to(root)),
                    str(new.relative_to(root)), "исправление: " + why])
        if not a.dry_run:
            new.parent.mkdir(parents=True, exist_ok=True)
            cur.rename(new)
    if not a.dry_run and log:
        with (root / R.JOURNAL).open("a", encoding="utf-8-sig", newline="") as f:
            csv.writer(f, delimiter=";").writerows(log)
        R.remove_empty(root)
    print(f"Перенесено: {len(log)}" + ("  — пробный прогон" if a.dry_run else ""))


if __name__ == "__main__":
    main()
