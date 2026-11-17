"""
Раскладка входящих выписок российских банков.

Файлы кладутся в корень папки «01 Банковские выписки» (как есть, с любым именем).
Скрипт находит счёт и период в содержимом и раскладывает:

    <Папка счёта> / ГГГГ / ММ. Месяц / ГГГГ-ММ-ДД_ГГГГ-ММ-ДД <Банк>.<расширение>

Папка счёта определяется по номеру счёта: соответствие счёт → папка собирается
из уже разложенных выписок 1С (txt). Новый счёт — папка «Новый счёт … — валюта».
PDF без текста берёт счёт и период у txt-выписки с тем же именем из той же загрузки,
иначе — банк и дату из имени файла.

Точные копии — в «_ДУБЛИ», нераспознанные — в «_НЕ РАЗОБРАНО».
Новая версия того же периода заменяет старую, старая уходит в «_АРХИВ ВЕРСИЙ».
Каждое перемещение пишется в «_журнал раскладки.csv». Файлы не удаляются;
уже разложенные папки не трогаются.

Запуск:
    python rf_sort.py --root <папка выписок> [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

DUPS, UNKNOWN, ARCHIVE = "_ДУБЛИ", "_НЕ РАЗОБРАНО", "_АРХИВ ВЕРСИЙ"
JOURNAL = "_журнал раскладки.csv"
SKIP_EXT = {".command", ".app", ".ds_store"}
MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август",
          "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
CURRENCY = {"810": "рубли", "643": "рубли", "156": "юани", "840": "доллары", "978": "евро",
            "051": "армянские драмы", "398": "тенге", "933": "бел. рубли"}

# Метки банка в имени файла → папка (для PDF без текста и без парной txt)
NAME_TAGS = [
    (re.compile(r"альф", re.I), "Альфа-Банк"),
    (re.compile(r"втб.*(юан|cny)", re.I), "ВТБ — юани (счёт 63)"),
    (re.compile(r"втб", re.I), "ВТБ — рубли"),
    (re.compile(r"отп", re.I), "ОТП-Банк"),
    (re.compile(r"(тб|т-банк|тбанк|тинькоф).*(юан|cny)", re.I), "Т-Банк — юани"),
    (re.compile(r"(^|[\s_\-])(тб|т-банк|тбанк|тинькоф)", re.I), "Т-Банк — рубли"),
    (re.compile(r"(^|[\s_\-])бк([\s_\-.]|$)|казан", re.I), "Банк Казани — рубли"),
    (re.compile(r"(^|[\s_\-])вб([\s_\-.]|$)|wb|вайлдбер", re.I), "ВБ банк"),
]

ACC_RE = re.compile(r"(?<!\d)(40[5-8]\d{17})(?!\d)")
DATE_RE = r"(\d{2})[./](\d{2})[./](\d{4})"
PERIOD_RE = re.compile(rf"(?:с|за период|период[:\s]*|period)\s*{DATE_RE}\s*(?:г\.?)?\s*(?:по|-|—|–|до)\s*{DATE_RE}", re.I)


@dataclass
class Info:
    account: str | None
    d1: date | None
    d2: date | None
    folder: str | None = None       # папка по метке имени (без счёта)
    via: str = ""


# ---------- общее ----------

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def sha1(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def d(dd, mm, yy) -> date | None:
    try:
        return date(int(yy), int(mm), int(dd))
    except ValueError:
        return None


def stem_key(p: Path) -> str:
    return re.sub(r"[^0-9a-zа-яё]", "", nfc(p.stem).casefold())


def read_text(p: Path) -> str:
    ext = p.suffix.lower()
    try:
        if ext == ".txt":
            raw = p.read_bytes()
            for enc in ("cp1251", "utf-8"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    pass
            return raw.decode("cp1251", "ignore")
        if ext in (".html", ".htm", ".xml", ".csv"):
            raw = p.read_bytes()
            t = raw.decode("utf-8", "ignore")
            if "�" in t[:2000]:
                t = raw.decode("cp1251", "ignore")
            return re.sub(r"<[^>]+>", " ", t)
        if ext in (".xlsx", ".xlsm"):
            return xlsx_text(p)
        if ext == ".xls":
            import xlrd
            wb = xlrd.open_workbook(str(p), on_demand=True)
            out = []
            for sh in wb.sheets()[:3]:
                for r in range(min(sh.nrows, 400)):
                    out.append(" ".join(str(v) for v in sh.row_values(r)))
            return "\n".join(out)
        if ext == ".pdf":
            return pdf_text(p)
    except Exception:
        return ""
    return ""


def xlsx_text(p: Path) -> str:
    out = []
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            if n.startswith("xl/sharedStrings") or (n.startswith("xl/worksheets/sheet") and n.endswith(".xml")):
                out.append(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore")))
    return "\n".join(out)


JXA = ('ObjC.import("PDFKit");function run(a){var d=$.PDFDocument.alloc.initWithURL('
       '$.NSURL.fileURLWithPath(a[0]));if(!d||d.isNil())return "";var s=d.string;'
       'return s&&!s.isNil()?ObjC.unwrap(s):"";}')


def pdf_text(p: Path) -> str:
    """Текст PDF средствами macOS (PDFKit), без сторонних библиотек."""
    if sys.platform != "darwin":
        return ""
    try:
        r = subprocess.run(["osascript", "-l", "JavaScript", "-e", JXA, str(p)],
                           capture_output=True, text=True, timeout=60)
        return r.stdout
    except Exception:
        return ""


def identify(p: Path) -> Info:
    t = read_text(p)
    acc = d1 = d2 = None
    if "1CClientBankExchange" in t[:200]:
        g = lambda k: (re.search(rf"^{k}=(.*)$", t, re.M) or [None, ""])[1].strip()
        acc = g("РасчСчет") or None
        m1, m2 = re.match(DATE_RE, g("ДатаНачала")), re.match(DATE_RE, g("ДатаКонца"))
        d1, d2 = (d(*m1.groups()) if m1 else None), (d(*m2.groups()) if m2 else None)
        return Info(acc, d1, d2, via="1С")
    accs = Counter(ACC_RE.findall(t))
    if accs:
        acc = accs.most_common(1)[0][0]
    m = PERIOD_RE.search(t)
    if m:
        d1, d2 = d(*m.groups()[:3]), d(*m.groups()[3:])
    elif acc:                                   # нет явного периода — по датам операций
        ds = sorted(x for x in (d(*g) for g in re.findall(DATE_RE, t)) if x and 2015 <= x.year <= 2035)
        if ds:
            d1, d2 = ds[0], ds[-1]
    return Info(acc, d1, d2, via="содержимое" if acc else "")


def name_info(p: Path) -> Info:
    """Банк и дата из имени файла: «2026_03_09 АЛЬФА.pdf»."""
    n = nfc(p.stem)
    folder = next((f for rx, f in NAME_TAGS if rx.search(n)), None)
    m = re.search(r"(20\d{2})[\s._-]?(\d{2})(?:[\s._-]?(\d{2}))?", n)
    dt = None
    if m:
        dt = d(m.group(3) or "01", m.group(2), m.group(1))
    return Info(None, dt, dt, folder=folder, via="имя файла")


# ---------- соответствие счёт → папка ----------

def is_service(rel: Path) -> bool:
    return any(x.startswith(("_", ".")) for x in rel.parts[:-1])


def account_map(root: Path) -> dict[str, str]:
    """Счёт → папка счёта по уже разложенным txt-выпискам 1С (по большинству файлов)."""
    votes: dict[str, Counter] = defaultdict(Counter)
    for p in root.rglob("*.txt"):
        rel = p.relative_to(root)
        if len(rel.parts) < 3 or is_service(rel):
            continue
        try:
            head = p.read_bytes()[:3000].decode("cp1251", "ignore")
        except OSError:
            continue
        m = re.search(r"^РасчСчет=(\d+)", head, re.M)
        if not m:
            continue
        # папка счёта: всё до уровня года
        parts = list(rel.parts[:-1])
        cut = next((i for i, x in enumerate(parts) if re.fullmatch(r"20\d{2}", x)), len(parts))
        votes[m.group(1)][str(Path(*parts[:cut]))] += 1
    return {a: c.most_common(1)[0][0] for a, c in votes.items()}


def new_folder(acc: str) -> str:
    return f"Новый счёт …{acc[-4:]} — {CURRENCY.get(acc[5:8], 'валюта ' + acc[5:8])}"


def tag(folder: str) -> str:
    base = Path(folder).name
    return re.sub(r"\s+", " ", base.replace("—", " ").replace("(", "").replace(")", "")).strip()


def target(root: Path, folder: str, d1: date, d2: date | None, src: Path, keep_name: bool) -> Path:
    month = root / folder / f"{d1:%Y}" / f"{d1:%m}. {MONTHS[d1.month - 1]}"
    if keep_name:
        return month / src.name
    end = d2 or d1
    return month / f"{d1:%Y-%m-%d}_{end:%Y-%m-%d} {tag(folder)}{src.suffix.lower()}"


def free_name(p: Path) -> Path:
    if not p.exists():
        return p
    for i in range(2, 1000):
        c = p.with_name(f"{p.stem} ({i}){p.suffix}")
        if not c.exists():
            return c
    raise RuntimeError(p)


# ---------- раскладка ----------

class Sorter:
    def __init__(self, root: Path, apply: bool, log=print):
        self.root, self.apply, self.log = root, apply, log
        self.journal: list[list[str]] = []
        self.stats = Counter()

    def move(self, src: Path, dst: Path, action: str):
        self.log(f"  {action}: {src.relative_to(self.root)} → {dst.relative_to(self.root)}")
        self.journal.append([datetime.now().isoformat(timespec="seconds"), action,
                             str(src.relative_to(self.root)), str(dst.relative_to(self.root))])
        if self.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)

    def incoming(self) -> list[Path]:
        out = []
        for base in (self.root, self.root / UNKNOWN):
            if base.is_dir():
                out += [p for p in base.iterdir() if p.is_file() and not p.name.startswith((".", "~$"))
                        and p.name not in (JOURNAL, "Icon\r", "Icon") and p.suffix.lower() not in SKIP_EXT]
        return sorted(out)

    def run(self):
        self.log(f"Папка: {self.root}" + ("" if self.apply else "   [ТОЛЬКО ПЛАН, файлы не двигаются]"))
        files = self.incoming()
        if not files:
            self.log("  Новых файлов нет.")
            return self.stats
        accmap = account_map(self.root)
        infos = {p: identify(p) for p in files}
        # PDF и прочие без счёта/периода — берём у парного файла той же загрузки
        by_stem = defaultdict(list)
        for p, i in infos.items():
            by_stem[stem_key(p)].append(p)
        for p, i in infos.items():
            if i.account and i.d1:
                continue
            twin = next((q for q in by_stem[stem_key(p)] if q != p and infos[q].account and infos[q].d1), None)
            if twin:
                t = infos[twin]
                infos[p] = Info(i.account or t.account, i.d1 or t.d1, i.d2 or t.d2, via=f"пара {twin.suffix}")

        planned: dict[str, Path] = {}
        for p in files:
            i = infos[p]
            keep = False
            if i.account and i.d1:
                folder = accmap.get(i.account) or new_folder(i.account)
                if i.account not in accmap:
                    self.log(f"  ! Новый счёт {i.account} — папка «{folder}», переименуйте её при желании")
                    accmap[i.account] = folder
            else:
                n = name_info(p)
                if not (n.folder and n.d1):
                    if p.parent != self.root / UNKNOWN:
                        self.move(p, free_name(self.root / UNKNOWN / p.name), "не разобрано")
                    self.stats["не разобрано"] += 1
                    continue
                folder, i, keep = n.folder, n, True
            dst = target(self.root, folder, i.d1, i.d2, p, keep)
            digest = sha1(p)
            if dst.parent.is_dir() and any(q.is_file() and q != p and q.stat().st_size == p.stat().st_size
                                           and sha1(q) == digest for q in dst.parent.iterdir()):
                self.move(p, free_name(self.root / DUPS / p.name), "дубль")      # уже лежит под другим именем
                self.stats["дубли"] += 1
                continue
            key = nfc(str(dst)).casefold()
            other = planned.get(key) or (dst if dst.exists() else None)
            if other is not None:
                if sha1(other) == sha1(p):
                    self.move(p, free_name(self.root / DUPS / p.name), "дубль")
                    self.stats["дубли"] += 1
                    continue
                stamp = datetime.fromtimestamp(other.stat().st_mtime).strftime("%Y-%m-%d %H%M")
                arch = self.root / ARCHIVE / dst.relative_to(self.root)
                arch = free_name(arch.with_name(f"{arch.stem} (версия {stamp}){arch.suffix}"))
                if other.exists() or self.apply:
                    self.move(other, arch, "старая версия в архив")
                self.move(p, dst, "новая версия")
                self.stats["новые версии"] += 1
            else:
                self.move(p, dst, f"разложен ({i.via})" if i.via else "разложен")
                self.stats["разложено"] += 1
            planned[key] = dst if self.apply else p

        if self.apply and self.journal:
            j = self.root / JOURNAL
            new = not j.exists()
            with j.open("a", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                if new:
                    w.writerow(["когда", "действие", "откуда", "куда"])
                w.writerows(self.journal)
        self.log("  Итог: " + (", ".join(f"{k} {v}" for k, v in self.stats.items()) or "—"))
        return self.stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Раскладка выписок российских банков")
    ap.add_argument("--root", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).expanduser()
    if not root.is_dir():
        print(f"Нет папки: {root}")
        return 1
    Sorter(root, apply=not a.dry_run).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
