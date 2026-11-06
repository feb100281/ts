# gear/management/commands/zup_payroll_2025.py
"""Зарплата за 2025 год → parquet для мэн пака (разовая загрузка).

За 2025 бухгалтерия прислала другой набор файлов, чем с 2026:
  «Ведомость 2025.docx»   — расчётные ведомости Т-51 за все месяцы в одном Word;
  «Взносы 2025-MM.xlsx»   — взносы по месяцам (январь — «Анализ взносов в фонды»,
                             без разбивки по сотрудникам).

Результат: data/zup/payroll_2025.parquet и data/zup/contributions_2025.parquet —
в том же формате, что у zup_payroll, мэн пак читает оба набора.

  python manage.py zup_payroll_2025 --check     # только проверить
  python manage.py zup_payroll_2025 --push      # записать и отправить на сервер
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from .zup_payroll import (DEFAULT_REMOTE, MONEY, T51, Command as ZupCommand, _num, norm_name,
                          parse_vznosy, short_key)

DEFAULT_SRC = "/Users/daria/Desktop/ТРЕНДСЕТТЕР/02 Бух данные/09. Зарплата начисления ЗУП/2025"


def _cells(row) -> list[str]:
    """Ячейки строки Word-таблицы без повторов объединённых ячеек."""
    seen, out = [], []
    for c in row.cells:
        if any(c._tc is s for s in seen):
            continue
        seen.append(c._tc)
        out.append(c.text.strip())
    return out


def parse_docx(path: Path) -> tuple[dict, list[str]]:
    """{месяц: [строки сотрудников]} из Word с ведомостями Т-51; предупреждения."""
    import docx
    doc = docx.Document(str(path))
    out, warn, period = {}, [], None
    for t in doc.tables:
        rows = [_cells(r) for r in t.rows]
        dates = [d for r in rows[:25] for v in r for d in re.findall(r"\d{2}\.\d{2}\.\d{4}", v)]
        if len(dates) >= 4:                          # шапка: дата составления, период с … по
            dd, mm, yy = map(int, dates[-2].split("."))
            period = date(yy, mm, 1)
            continue
        if not any(r[:4] == ["1", "2", "3", "4"] for r in rows):
            continue
        if period is None:
            warn.append(f"{path.name}: таблица ведомости без периода — пропущена")
            continue
        recs, total = [], None
        for r in rows:
            if any("Итого по ведомости" in v for v in r):
                k = next(i for i, v in enumerate(r) if "Итого по ведомости" in v)
                vals = r[k + 1:k + 12]
                total = {T51[n]: _num(v) for n, v in zip(range(8, 19), vals) if n in T51}
                continue
            if len(r) != 18 or not r[0].isdigit() or not r[2] or r[2] == "3":
                continue
            rec = {T51[n]: r[n - 1] for n in T51}
            for k2 in MONEY:
                rec[k2] = _num(rec[k2])
            rec["row_no"] = int(rec["row_no"])
            rec["name_short"] = re.sub(r"\s+", " ", rec["name_short"]).strip()
            recs.append(rec)
        got = round(sum(x["accrued_total"] for x in recs), 2)
        if total and abs(got - total["accrued_total"]) > 0.05:
            warn.append(f"{period:%Y-%m}: начислено по строкам {got:,.2f} ≠ итогу "
                        f"{total['accrued_total']:,.2f}")
        if total and abs(sum(x["ndfl"] for x in recs) - total["ndfl"]) > 0.05:
            warn.append(f"{period:%Y-%m}: НДФЛ по строкам ≠ итогу ведомости")
        out.setdefault(period, []).extend(recs)
        period = None
    return out, warn


class Command(BaseCommand):
    help = "Зарплата за 2025 (Word-ведомость + взносы по месяцам) → data/zup/*_2025.parquet"

    def add_arguments(self, parser):
        parser.add_argument("--src", default=os.getenv("ZUP_2025_DIR", DEFAULT_SRC))
        parser.add_argument("--check", action="store_true", help="Только проверить, не записывать")
        parser.add_argument("--push", action="store_true", help="Отправить на сервер (rsync)")
        parser.add_argument("--remote", default=os.getenv("ZUP_REMOTE", DEFAULT_REMOTE))
        parser.add_argument("--out", default=str(Path(settings.BASE_DIR) / "data" / "zup"))

    def handle(self, *args, **o):
        import pandas as pd
        src = Path(o["src"]).expanduser()
        import unicodedata
        nm = lambda f: unicodedata.normalize("NFC", f.name).lower()
        if not src.is_dir():
            raise CommandError(f"Нет папки: {src}")
        ved = next((f for f in sorted(src.rglob("*.docx"))
                    if nm(f).startswith("ведомость") and not f.name.startswith("~$")), None)
        if not ved:
            found = ", ".join(sorted(f.name for f in src.rglob("*") if f.is_file())[:10]) or "пусто"
            raise CommandError(f"В {src} нет «Ведомость*.docx» (в папке: {found}). "
                               "Укажите папку: --src \"/путь/к/папке\"")
        months, warns = parse_docx(ved)

        vz_by_month = {}
        for f in sorted(src.rglob("*.xlsx")):
            m = re.search(r"(\d{4})-(\d{2})", f.name)
            if nm(f).startswith("взнос") and m and not f.name.startswith("~$"):
                rows, w = parse_vznosy(f)
                vz_by_month[date(int(m.group(1)), int(m.group(2)), 1)] = (rows, f.name)
                warns += w

        # полные ФИО: сначала из взносов того же месяца, иначе из любого месяца года
        year_keys: dict[str, set] = {}
        for rows, _ in vz_by_month.values():
            for x in rows:
                if x["full_name"]:
                    year_keys.setdefault(short_key(x["full_name"]), set()).add(norm_name(x["full_name"]))

        pay, con = [], []
        for period in sorted(months):
            rows = months[period]
            vz, vname = vz_by_month.get(period, ([], None))
            if vname is None:
                warns.append(f"{period:%Y-%m}: нет файла взносов — взносы за месяц не попадут")
            month_keys: dict[str, set] = {}
            for x in vz:
                if x["full_name"]:
                    month_keys.setdefault(short_key(x["full_name"]), set()).add(norm_name(x["full_name"]))
            for r in rows:
                k = short_key(r["name_short"])
                cand = month_keys.get(k) or year_keys.get(k, set())
                r["full_name"] = next(iter(cand)) if len(cand) == 1 else None
                if len(cand) > 1:
                    warns.append(f"{period:%Y-%m}: «{r['name_short']}» — несколько ФИО: "
                                 + ", ".join(sorted(cand)))
                elif not cand and r["accrued_total"]:
                    warns.append(f"{period:%Y-%m}: «{r['name_short']}» — полное ФИО не найдено")
                r.update(period=period, source=ved.name)
                pay.append(r)
            for x in vz:
                x.update(period=period, full_name=norm_name(x["full_name"]) or None, source=vname)
                if x["amount"]:
                    con.append(x)
            self.stdout.write(
                f"{period:%Y-%m}: строк {len(rows)}, начислено "
                f"{sum(r['accrued_total'] for r in rows):,.2f}, НДФЛ "
                f"{sum(r['ndfl'] for r in rows):,.2f}, взносы "
                f"{sum(x['amount'] for x in vz):,.2f}".replace(",", " "))
        for m in sorted(set(vz_by_month) - set(months)):
            warns.append(f"{m:%Y-%m}: взносы есть, а ведомости за месяц в Word нет")

        new = ZupCommand._new_employees(pay, con)
        warns += ZupCommand._cash_not_in_zup(pay, con)
        for w in warns:
            self.stdout.write(self.style.WARNING("⚠ " + w))
        if new:
            msg = "НОВЫЕ СОТРУДНИКИ (2025) — нет среди контрагентов:\n  " + "\n  ".join(new)
            self.stdout.write(self.style.ERROR(msg))
            ZupCommand._notify(msg)
        if o.get("check"):
            self.stdout.write("Проверка — файлы не записаны.")
            return

        out = Path(o["out"])
        out.mkdir(parents=True, exist_ok=True)
        files = []
        for name, data in (("payroll_2025", pay), ("contributions_2025", con)):
            df = pd.DataFrame(data)
            for c in ("period", "income_month"):
                if c in df:
                    df[c] = pd.to_datetime(df[c]).dt.date
            tmp = out / f"{name}.parquet.tmp"
            df.to_parquet(tmp, index=False)
            tmp.replace(out / f"{name}.parquet")
            files.append(str(out / f"{name}.parquet"))
        self.stdout.write(self.style.SUCCESS(f"Готово: {', '.join(files)}"))
        if o.get("push"):
            import subprocess
            cmd = ["rsync", "-av", *files, o["remote"]]
            self.stdout.write("→ " + " ".join(cmd))
            if subprocess.call(cmd) != 0:
                raise CommandError("rsync не прошёл — файлы на сервер не отправлены")
            self.stdout.write(self.style.SUCCESS("Отправлено на сервер."))
