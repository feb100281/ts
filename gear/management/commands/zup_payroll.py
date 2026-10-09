# gear/management/commands/zup_payroll.py
"""Начисления по зарплате из 1С:ЗУП → parquet для мэн пака.

Источник: папка с подпапками YYYY-MM, в каждой два отчёта ЗУП:
  «Ведомость*.xlsx» — расчётная ведомость Т-51 (начислено, НДФЛ, удержания);
  «Взносы*.xlsx»    — «Проверка расчёта взносов» (страховые взносы по сотрудникам).

Результат (перезаписывается целиком при каждом запуске):
  data/zup/payroll.parquet        — строка на сотрудника и должность за месяц;
  data/zup/contributions.parquet  — строка на сотрудника, раздел взносов и месяц дохода.

Запуск:
  python manage.py zup_payroll
  python manage.py zup_payroll --src "/путь/к/папке" --month 2026-09
  python manage.py zup_payroll --push      # и отправить data/zup на сервер (rsync)
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

DEFAULT_SRC = "/Users/daria/Desktop/ТРЕНДСЕТТЕР/02 Бух данные/09. Зарплата начисления ЗУП"
DEFAULT_REMOTE = "daria@82.202.197.94:~/ts/data/zup/"
MONTH_DIR = re.compile(r"^(\d{4})-(\d{2})$")
MONTHS = {"январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "июл": 7,
          "август": 8, "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12}

# Т-51: номера граф формы → поле
T51 = {1: "row_no", 2: "tab_no", 3: "name_short", 4: "position", 5: "rate",
       8: "accrued_time", 9: "accrued_piece", 10: "accrued_other", 11: "other_income",
       12: "accrued_total", 13: "ndfl", 14: "withheld_other", 15: "withheld_total",
       16: "debt_org", 17: "debt_emp", 18: "to_pay"}
MONEY = ["rate", "accrued_time", "accrued_piece", "accrued_other", "other_income",
         "accrued_total", "ndfl", "withheld_other", "withheld_total", "debt_org",
         "debt_emp", "to_pay"]


def norm_name(s) -> str:
    """ФИО для сравнения: верхний регистр, Ё→Е, одиночные пробелы."""
    s = str(s or "").upper().replace("Ё", "Е")
    return re.sub(r"\s+", " ", s).strip()


def short_key(full: str) -> str:
    """«АЙВАЗЯН ВАЛЕРИЙ ВИКТОРОВИЧ» / «Айвазян В. В.» → «АЙВАЗЯН В В»."""
    parts = norm_name(full).replace(".", " ").split()
    if not parts:
        return ""
    return " ".join([parts[0]] + [p[0] for p in parts[1:3]])


def _num(v) -> float:
    if v in (None, ""):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _rows(path: Path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.worksheets[0]
    for r in ws.iter_rows(values_only=True):
        yield list(r)
    wb.close()


# ---------------------------------------------------------------- ведомость
def parse_vedomost(path: Path) -> tuple[list[dict], dict, list[str]]:
    """Строки сотрудников, итог по ведомости из файла, предупреждения."""
    rows = list(_rows(path))
    warn: list[str] = []
    cols: dict[int, int] = {}
    for r in rows:                                   # строка с номерами граф 1…18
        nums = {i: str(v).strip() for i, v in enumerate(r) if v not in (None, "")}
        seq = [v for v in nums.values()]
        if seq[:4] == ["1", "2", "3", "4"] and "18" in seq:
            cols = {int(v): i for i, v in nums.items() if v.isdigit()}
            break
    if not cols:
        raise CommandError(f"{path.name}: не нашла строку с номерами граф Т-51")

    out, total = [], {}
    for r in rows:
        get = lambda n: r[cols[n]] if n in cols and cols[n] < len(r) else None
        first = get(1)
        if any(isinstance(v, str) and "Итого по ведомости" in v for v in r):
            total = {T51[n]: _num(get(n)) for n in T51 if T51[n] in MONEY}
            continue
        if first is None or not str(first).strip().isdigit() or not get(3):
            continue
        if str(get(3)).strip() == "3":                   # повтор строки номеров граф
            continue
        rec = {T51[n]: get(n) for n in T51}
        for k in MONEY:
            rec[k] = _num(rec[k])
        rec["row_no"] = int(str(rec["row_no"]).strip())
        rec["tab_no"] = str(rec["tab_no"] or "").strip()
        rec["name_short"] = re.sub(r"\s+", " ", str(rec["name_short"])).strip()
        rec["position"] = str(rec["position"] or "").strip()
        out.append(rec)
    if not total:
        warn.append(f"{path.name}: нет строки «Итого по ведомости» — сверка итогов пропущена")
    else:
        got = round(sum(x["accrued_total"] for x in out), 2)
        if abs(got - total["accrued_total"]) > 0.05:
            warn.append(f"{path.name}: сумма начислений по строкам {got:,.2f} ≠ итогу "
                        f"{total['accrued_total']:,.2f}")
    return out, total, warn


def ved_period(path: Path) -> tuple[date, date] | None:
    """Отчётный период «с … по …» из шапки ведомости."""
    found = []
    for r in list(_rows(path))[:20]:
        for v in r:
            if isinstance(v, str) and re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", v.strip()):
                d, m, y = map(int, v.strip().split("."))
                found.append(date(y, m, d))
            elif hasattr(v, "year") and hasattr(v, "month"):
                found.append(date(v.year, v.month, v.day))
    return (found[-2], found[-1]) if len(found) >= 3 else None


# ---------------------------------------------------------------- взносы
def _month_from_text(s) -> date | None:
    if hasattr(s, "year"):
        return date(s.year, s.month, 1)
    m = re.match(r"\s*([А-Яа-яЁё]+)\s+(\d{4})", str(s or ""))
    if not m:
        return None
    w = m.group(1).lower()
    for k, n in sorted(MONTHS.items(), key=lambda x: -len(x[0])):
        if w.startswith(k):
            return date(int(m.group(2)), n, 1)
    return None


def parse_vznosy(path: Path) -> tuple[list[dict], list[str]]:
    """Взносы по сотрудникам: раздел, месяц дохода, база, сумма."""
    rows = list(_rows(path))
    out, warn = [], []
    section, hdr = None, None
    for r in rows:
        cells = [(i, v) for i, v in enumerate(r) if v not in (None, "")]
        if not cells:
            continue
        i0, v0 = cells[0]
        t0 = str(v0).strip()
        if t0 == "Сотрудник":                            # шапка таблицы раздела
            hdr = {"name": i0, "month": None, "base": None, "amt": []}
            for i, v in cells:
                h = str(v).strip().lower()
                if h.startswith("месяц получения"):
                    hdr["month"] = i
                elif h.startswith("облагаемая база"):
                    hdr["base"] = i
                elif h.startswith("взносы") and "расчет" not in h and "расчёт" not in h:
                    hdr["amt"].append(i)
            continue
        if t0 == "Итого":
            if hdr and hdr["amt"]:
                file_tot = round(sum(_num(r[i]) for i in hdr["amt"] if i < len(r)), 2)
                got = round(sum(x["amount"] for x in out if x["section"] == section), 2)
                if abs(file_tot - got) > 0.05:
                    warn.append(f"{path.name}: «{section}» — сумма по строкам {got:,.2f} ≠ "
                                f"итогу {file_tot:,.2f}")
            hdr = None
            continue
        if hdr is None:
            if len(cells) == 1 and i0 == 0 and not t0.startswith(("Период", "Организация")):
                section = t0                             # заголовок раздела
            continue
        if i0 != hdr["name"]:
            continue
        amt = sum(_num(r[i]) for i in hdr["amt"] if i < len(r))
        out.append({
            "section": section or "",
            "full_name": re.sub(r"\s+", " ", t0),
            "income_month": _month_from_text(r[hdr["month"]]) if hdr["month"] is not None else None,
            "base": _num(r[hdr["base"]]) if hdr["base"] is not None else 0.0,
            "amount": round(amt, 2),
        })
    return out, warn


# ---------------------------------------------------------------- команда
class Command(BaseCommand):
    help = "Начисления зарплаты и взносы из ЗУП → data/zup/*.parquet"

    def add_arguments(self, parser):
        parser.add_argument("--src", default=os.getenv("ZUP_DIR", DEFAULT_SRC),
                            help="Папка с подпапками YYYY-MM")
        parser.add_argument("--month", help="Проверить только один месяц YYYY-MM (без записи)")
        parser.add_argument("--out", default=str(Path(settings.BASE_DIR) / "data" / "zup"))
        parser.add_argument("--push", action="store_true",
                            help="После записи отправить папку на сервер через rsync")
        parser.add_argument("--remote", default=os.getenv("ZUP_REMOTE", DEFAULT_REMOTE))

    def handle(self, *args, **o):
        import pandas as pd
        src = Path(o["src"]).expanduser()
        if not src.is_dir():
            raise CommandError(f"Нет папки: {src}")
        dirs = sorted(p for p in src.iterdir() if p.is_dir() and MONTH_DIR.match(p.name))
        if not dirs:
            raise CommandError(f"В {src} нет подпапок вида YYYY-MM")
        only = o.get("month")                 # читаем все месяцы: сверке нужен прошлый
        if only and only not in {p.name for p in dirs}:
            raise CommandError(f"Нет подпапки {only}")

        pay, con, warns = [], [], []
        for d in dirs:
            y, m = map(int, MONTH_DIR.match(d.name).groups())
            period = date(y, m, 1)
            files = {f.name.lower(): f for f in d.iterdir()
                     if f.suffix.lower() == ".xlsx" and not f.name.startswith(("~$", "."))}
            ved = next((f for n, f in files.items() if n.startswith("ведомость")), None)
            vzn = next((f for n, f in files.items() if n.startswith("взнос")), None)
            if not ved or not vzn:
                warns.append(f"{d.name}: нет файла {'«Ведомость»' if not ved else '«Взносы»'} — "
                             "месяц пропущен, в мэн паке останется кассовый метод")
                continue
            p = ved_period(ved)
            if p and (p[0].year, p[0].month) != (y, m):
                warns.append(f"{d.name}: в ведомости период {p[0]:%d.%m.%Y}–{p[1]:%d.%m.%Y}, "
                             "а папка другого месяца")
            rows, _, w1 = parse_vedomost(ved)
            vz, w2 = parse_vznosy(vzn)
            warns += w1 + w2

            full_by_key: dict[str, set] = {}
            for x in vz:
                full_by_key.setdefault(short_key(x["full_name"]), set()).add(norm_name(x["full_name"]))
            for r in rows:
                cand = full_by_key.get(short_key(r["name_short"]), set())
                r["full_name"] = next(iter(cand)) if len(cand) == 1 else None
                if len(cand) > 1:
                    warns.append(f"{d.name}: «{r['name_short']}» — несколько ФИО во взносах: "
                                 + ", ".join(sorted(cand)))
                elif not cand and r["accrued_total"]:
                    warns.append(f"{d.name}: «{r['name_short']}» нет во взносах — полное ФИО "
                                 "не определено")
                r.update(period=period, source=ved.name)
                pay.append(r)
            for x in vz:
                x.update(period=period, full_name=norm_name(x["full_name"]), source=vzn.name)
                if x["amount"]:                          # нулевые разделы (ОМС, ОСС…) не храним
                    con.append(x)
            acc = sum(r["accrued_total"] for r in rows)
            nd = sum(r["ndfl"] for r in rows)
            cc = sum(x["amount"] for x in vz)
            if only and d.name != only:
                continue
            self.stdout.write(f"{d.name}: сотрудников {len({r['name_short'] for r in rows})}, "
                              f"начислено {acc:,.2f}, НДФЛ {nd:,.2f}, взносы {cc:,.2f}"
                              .replace(",", " "))

        new = self._new_employees(pay, con)
        warns += self._cash_not_in_zup(pay, con, only)
        if only:
            warns = [w for w in warns if not re.match(r"\d{4}-\d{2}", w) or w.startswith(only)]
        for w in warns:
            self.stdout.write(self.style.WARNING("⚠ " + w))
        if new:
            msg = ("НОВЫЕ СОТРУДНИКИ — нет среди контрагентов:\n  " + "\n  ".join(new))
            self.stdout.write(self.style.ERROR(msg))
            self._notify(msg)
        if o.get("month"):
            self.stdout.write("Проверка одного месяца — файлы не записаны.")
            return

        out = Path(o["out"])
        out.mkdir(parents=True, exist_ok=True)
        dp = pd.DataFrame(pay)
        dc = pd.DataFrame(con)
        for df in (dp, dc):
            df["period"] = pd.to_datetime(df["period"]).dt.date
        if "income_month" in dc:
            dc["income_month"] = pd.to_datetime(dc["income_month"]).dt.date
        for name, df in (("payroll", dp), ("contributions", dc)):
            tmp = out / f"{name}.parquet.tmp"
            df.to_parquet(tmp, index=False)
            tmp.replace(out / f"{name}.parquet")
        self.stdout.write(self.style.SUCCESS(
            f"Готово: {out}/payroll.parquet ({len(dp)} строк), "
            f"contributions.parquet ({len(dc)} строк)"))
        if o.get("push"):
            import subprocess
            cmd = ["rsync", "-av", f"{out}/payroll.parquet", f"{out}/contributions.parquet",
                   o["remote"]]
            self.stdout.write("→ " + " ".join(cmd))
            if subprocess.call(cmd) != 0:
                raise CommandError("rsync не прошёл — файлы на сервер не отправлены")
            self.stdout.write(self.style.SUCCESS("Отправлено на сервер."))

    @staticmethod
    def _new_employees(pay, con) -> list[str]:
        """ФИО из файлов, которых нет среди контрагентов (сравнение без учёта регистра)."""
        try:
            from counterparties.models import Counterparty
            known = {norm_name(n) for n in Counterparty.objects.values_list("name", flat=True)}
        except Exception as e:
            return [f"(не удалось проверить по базе контрагентов: {type(e).__name__}: {e})"]
        names = {x["full_name"] for x in con} | {r["full_name"] for r in pay if r.get("full_name")}
        return sorted(n for n in names if n and n not in known)

    @staticmethod
    def _cash_not_in_zup(pay, con, only=None) -> list[str]:
        """Оплата труда по банку (550100) тем, кого нет в ЗУП за этот или прошлый месяц."""
        try:
            from django.db import connection
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT DATE_TRUNC('month', date_from)::date, cp_name, SUM(amount)
                    FROM public.pl_for_csv
                    WHERE account_name LIKE '610000%%' AND cost_item LIKE '550100%%'
                    GROUP BY 1, 2""")
                rows = cur.fetchall()
        except Exception as e:
            return [f"Сверка с оплатой по банку не выполнена: {type(e).__name__}: {e}"]
        zup: dict[date, set] = {}
        for r in pay:
            if r.get("full_name"):
                zup.setdefault(r["period"], set()).add(r["full_name"])
        for x in con:
            zup.setdefault(x["period"], set()).add(x["full_name"])
        out = []
        for m, cp, amt in sorted(rows, key=lambda r: (r[0], str(r[1]))):
            m = date(m.year, m.month, 1)
            if m not in zup or (only and f"{m:%Y-%m}" != only):
                continue                                 # месяц без ЗУП — кассовый метод
            prev = date(m.year - (m.month == 1), (m.month - 2) % 12 + 1, 1)
            name = norm_name(cp)
            if name and name not in zup[m] | zup.get(prev, set()):
                out.append(f"{m:%Y-%m}: оплата труда по банку «{cp}» ({abs(float(amt)):,.0f} ₽), "
                           "а в ЗУП за этот и прошлый месяц сотрудника нет".replace(",", " "))
        return out

    @staticmethod
    def _notify(text: str):
        """Дублируем в Telegram администратору, если бот настроен."""
        token = (os.getenv("TELEGRAM_BOT_TOKEN_FINANCE") or "").strip()
        admin = (os.getenv("TELEGRAM_ADMIN_ID") or "").strip()
        if not token or not admin.lstrip("-").isdigit():
            return
        try:
            import json
            import urllib.request
            data = json.dumps({"chat_id": int(admin), "text": "ЗУП: " + text}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                         data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception:
            pass
