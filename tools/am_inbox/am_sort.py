"""
Раскладка входящих файлов Армении.

Выписки:  БАНК / ВАЛЮТА СЧЁТ / ГОД / ГГГГ-ММ-ДД_ГГГГ-ММ-ДД.расширение
Продажи:  ГОД / ГГГГ-ММ Продажи и возвраты.xlsx

Банк, счёт и период берутся из содержимого файла, имя файла не важно.
Точные копии — в «_ДУБЛИ», нераспознанные — в «_НЕ РАЗОБРАНО».
Новая версия того же периода заменяет старую, старая уходит в «_АРХИВ ВЕРСИЙ».
Каждое перемещение пишется в «_журнал раскладки.csv». Файлы не удаляются.

Запуск:
    python am_sort.py --statements <папка выписок> --sales <папка продаж> [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

DUPS = "_ДУБЛИ"
UNKNOWN = "_НЕ РАЗОБРАНО"
ARCHIVE = "_АРХИВ ВЕРСИЙ"
JOURNAL = "_журнал раскладки.csv"
SALES_NAME = "Продажи и возвраты"

# Код банка = первые три цифры счёта
BANK_CODES = {
    "103": "ЦБ АРМЕНИИ", "900": "ЦБ АРМЕНИИ",
    "115": "АМИО БАНК",
    "118": "АЙДИ БАНК",
    "151": "АРАРАТБАНК",
    "157": "АМЕРИАБАНК",
    "160": "ВТБ-АРМЕНИЯ", "161": "ВТБ-АРМЕНИЯ",
    "163": "АРМЭКОНОМБАНК",
    "166": "ЭВОКАБАНК",
    "193": "КОНВЕРС БАНК",
    "205": "ИНЕКОБАНК",
    "214": "БИБЛОС БАНК",
    "217": "АРДШИНБАНК", "218": "АРДШИНБАНК", "247": "АРДШИНБАНК", "248": "АРДШИНБАНК",
    "220": "АКБА БАНК",
    "223": "АРЦАХБАНК",
    "241": "ЮНИБАНК",
}

# Название банка в шапке выписки «Банк-клиент»
BANK_NAMES = [
    (re.compile(r"ԱյԴի|ԱՅԴԻ|ID\s*Bank|Անելիք", re.I), "АЙДИ БАНК"),
    (re.compile(r"Արդշին", re.I), "АРДШИНБАНК"),
    (re.compile(r"ՎՏԲ|VTB", re.I), "ВТБ-АРМЕНИЯ"),
    (re.compile(r"Ամերիա|Ameria", re.I), "АМЕРИАБАНК"),
    (re.compile(r"Ակբա|ԱԿԲԱ|ACBA", re.I), "АКБА БАНК"),
    (re.compile(r"Ինեկո|Ineco", re.I), "ИНЕКОБАНК"),
    (re.compile(r"Կոնվերս|Converse", re.I), "КОНВЕРС БАНК"),
    (re.compile(r"Էվոկա|Evoca", re.I), "ЭВОКАБАНК"),
    (re.compile(r"Արարատ|Ararat", re.I), "АРАРАТБАНК"),
    (re.compile(r"Յունի|Unibank", re.I), "ЮНИБАНК"),
    (re.compile(r"Հայէկոնոմ|Armeconom", re.I), "АРМЭКОНОМБАНК"),
    (re.compile(r"Ամիո|Amio|Հայբիզնես|Armbusiness", re.I), "АМИО БАНК"),
]

CURRENCIES = {"AMD", "USD", "EUR", "RUB", "GBP", "CHF", "CNY", "GEL", "AED", "KZT"}


# ============================================================
# Общее
# ============================================================

# ArmSCII-8: старая 8-битная армянская кодировка. В файле она видна как латиница с умляутами.
_ARMSCII = {0xA2: "և", 0xA3: "։", 0xA4: ")", 0xA5: "(", 0xA6: "»", 0xA7: "«",
            0xA8: "—", 0xA9: ".", 0xAA: "՝", 0xAB: ",", 0xAC: "-", 0xAD: "֊",
            0xAE: "…", 0xAF: "՜", 0xB0: "՛", 0xB1: "՞", 0xFE: "՚"}
for _i in range(38):                                     # Ա/ա … Ֆ/ֆ парами с 0xB2
    _ARMSCII[0xB2 + 2 * _i] = chr(0x0531 + _i)
    _ARMSCII[0xB3 + 2 * _i] = chr(0x0561 + _i)
_ARMSCII_TABLE = {k: v for k, v in _ARMSCII.items()}


def fix_armscii(text):
    """Строку в ArmSCII-8, прочитанную как Latin-1, вернуть армянскими буквами. Нормальный текст — как есть."""
    if not isinstance(text, str) or not text:
        return text
    if any("Ա" <= ch <= "և" for ch in text):  # уже армянский юникод
        return text
    if not any("¢" <= ch <= "þ" for ch in text):
        return text
    return "".join(_ARMSCII_TABLE.get(ord(ch), ch) for ch in text)


def nfc(text: str) -> str:
    """macOS хранит имена в NFD — сравниваем в NFC."""
    return unicodedata.normalize("NFC", text)


def same_path(a: Path, b: Path) -> bool:
    return nfc(str(a)).casefold() == nfc(str(b)).casefold()


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_date(text) -> date | None:
    """01/10/2026, 01.10.2026, 01/10/26, 01.10.2026 10:19:10, серийный номер Excel."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(text))
    s = str(text).strip()
    if re.fullmatch(r"\d+(\.\d+)?", s) and float(s) > 20000:
        return date(1899, 12, 30) + timedelta(days=int(float(s)))
    m = re.match(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", s)
    if not m:
        return None
    d, mth, y = (int(x) for x in m.groups())
    if y < 100:
        y += 2000
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def bank_by_account(account: str | None) -> str | None:
    return BANK_CODES.get((account or "")[:3])


def bank_by_name(text: str) -> str | None:
    for rx, name in BANK_NAMES:
        if rx.search(text or ""):
            return name
    return None


# ============================================================
# Чтение xlsx без сторонних библиотек
# ============================================================

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


class Xlsx:
    def __init__(self, path: Path):
        self.z = zipfile.ZipFile(path)
        self.shared = self._shared_strings()
        self.sheets = self._sheet_map()

    def _shared_strings(self) -> list[str]:
        try:
            root = ET.fromstring(self.z.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        return ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
                for si in root.findall("m:si", NS)]

    def _sheet_map(self) -> dict[str, str]:
        wb = ET.fromstring(self.z.read("xl/workbook.xml"))
        rels = ET.fromstring(self.z.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        out = {}
        for sh in wb.find("m:sheets", NS):
            target = targets[sh.get(f"{{{REL_NS}}}id")].lstrip("/")
            out[sh.get("name")] = target if target.startswith("xl/") else "xl/" + target
        return out

    def rows(self, sheet: str | None = None, limit: int | None = None):
        """Строки листа как списки значений (строки или числа)."""
        name = sheet if sheet is not None else next(iter(self.sheets))
        with self.z.open(self.sheets[name]) as f:
            count = 0
            for _, el in ET.iterparse(f):
                if el.tag != f"{{{NS['m']}}}row":
                    continue
                row: list = []
                for c in el.findall("m:c", NS):
                    idx = _col_index(c.get("r")) if c.get("r") else len(row)
                    while len(row) < idx:
                        row.append(None)
                    row.append(self._value(c))
                el.clear()
                yield row
                count += 1
                if limit and count >= limit:
                    return

    def _value(self, c):
        t = c.get("t")
        if t == "inlineStr":
            return "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
        v = c.find("m:v", NS)
        if v is None or v.text is None:
            return None
        if t == "s":
            return self.shared[int(v.text)]
        if t in ("str", "b", "e"):
            return v.text
        try:
            num = float(v.text)
            return int(num) if num.is_integer() else num
        except ValueError:
            return v.text


def spreadsheetml_rows(path: Path, limit: int = 40) -> list[list[str]]:
    """Выписка «Банк-клиент»: XML Spreadsheet 2003 с расширением .xls."""
    raw = path.read_bytes()[:400_000]
    m = re.search(rb'encoding="([^"]+)"', raw[:200])
    enc = m.group(1).decode() if m else "utf-8"
    try:
        text = raw.decode(enc, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    out = []
    for row in re.findall(r"<Row\b.*?</Row>", text, re.S)[:limit]:
        cells = [fix_armscii(re.sub(r"<[^>]+>", "", c).replace("&quot;", '"').replace("&amp;", "&").strip())
                 for c in re.findall(r"<Data\b[^>]*>(.*?)</Data>", row, re.S)]
        out.append(cells)
    return out


# ============================================================
# Распознавание
# ============================================================

@dataclass
class Info:
    kind: str                      # statement | sales
    bank: str | None = None
    account: str | None = None
    currency: str | None = None
    d1: date | None = None
    d2: date | None = None
    note: str = ""


def read_ameria(path: Path) -> Info | None:
    """AccountStatement.xlsx: период, счёт и валюта в первых строках."""
    try:
        x = Xlsx(path)
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        return None
    head = {}
    for row in x.rows(limit=12):
        if row and row[0]:
            head[str(row[0]).strip()] = [v for v in row[1:] if v not in (None, "")]
    start = head.get("Ժամանակահատվածի սկիզբ")
    end = head.get("Ժամանակահատվածի վերջ")
    acc = head.get("Հաշիվ N")
    cur = head.get("Արժույթ")
    if not (start and end and acc):
        return None
    account = re.sub(r"\D", "", str(acc[0]))
    return Info("statement", bank=bank_by_account(account), account=account,
                currency=str(cur[0]).strip().upper() if cur else None,
                d1=parse_date(start[0]), d2=parse_date(end[0]))


def read_bank_client(path: Path, rows: list[list[str]] | None = None) -> Info | None:
    """Տեղեկանք из «Банк-клиент» (АйДи, Ардшин, ВТБ-Армения и др.): .xls (XML) или пересохранённый .xlsx."""
    if rows is None:
        head = path.read_bytes()[:2000]
        if b"<?xml" not in head and b"<Workbook" not in head:
            return None
        rows = spreadsheetml_rows(path)
    flat = [c for r in rows[:15] for c in r if c]
    if not any("Տեղեկանք" in c for c in flat):
        return None
    info = Info("statement")
    for c in flat:
        if info.d1 is None:
            m = re.search(r"(\d{2}/\d{2}/\d{2,4})\s*-\s*(\d{2}/\d{2}/\d{2,4})", c)
            if m:
                info.d1, info.d2 = parse_date(m.group(1)), parse_date(m.group(2))
        if c.startswith("Բանկ:"):
            info.bank = bank_by_name(c)
        if c.startswith("Հաշվի համարը:"):
            m = re.search(r"(\d{10,20})\s*([A-Z]{3})?", c)
            if m:
                info.account, info.currency = m.group(1), m.group(2)
    if not info.account:
        return None
    info.bank = bank_by_account(info.account) or info.bank
    return info


def read_sales(path: Path) -> Info | None:
    """Выгрузка продаж и возвратов из 1С УТ: листы «продажи» и «возвраты»."""
    try:
        x = Xlsx(path)
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        return None
    sheets = {nfc(k).strip().casefold(): k for k in x.sheets}
    sales = sheets.get("продажи")
    if not sales:
        return None
    rows = x.rows(sales)
    header = [str(v or "").strip() for v in next(rows, [])]
    if "Дата продажи" not in header:
        return None
    col = header.index("Дата продажи")
    days = [d for r in rows if len(r) > col and (d := parse_date(r[col]))]
    if not days:
        return None
    months = {(d.year, d.month) for d in days}
    note = "" if len(months) == 1 else "несколько месяцев"
    return Info("sales", d1=min(days), d2=max(days), note=note)


def by_parser(path: Path) -> Info | None:
    """Русские версии выписок и прочие форматы — через общий разборщик загрузки."""
    try:
        import importlib.util
        src = Path(__file__).resolve().parents[2] / "utils" / "bsparsers" / "am" / "parser.py"
        spec = importlib.util.spec_from_file_location("am_parser", src)
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("am_parser", mod)
        spec.loader.exec_module(mod)
        st = mod.parse_statement(path)
    except Exception:
        return None
    if not st.account or not st.start:
        return None
    return Info("statement", bank=st.bank, account=st.account, currency=(st.currency or "").upper() or None,
                d1=st.start, d2=st.finish)


def identify(path: Path, kind: str) -> Info | None:
    info = _identify(path, kind)
    if info is not None and info.kind == "statement" and not info.currency:
        alt = by_parser(path)
        info.currency = alt.currency if alt else None
    if info is None and kind != "sales" and path.suffix.lower() in (".xlsx", ".xlsm", ".xls", ".xml"):
        info = by_parser(path)
    return info


def _identify(path: Path, kind: str) -> Info | None:
    ext = path.suffix.lower()
    if kind == "sales":
        return read_sales(path) if ext in (".xlsx", ".xlsm") else None
    if ext in (".xlsx", ".xlsm"):
        info = read_ameria(path)
        if info is None:                                   # «Банк-клиент», пересохранённый в xlsx
            try:
                rows = [[fix_armscii(str(v)) if v is not None else "" for v in r] for r in Xlsx(path).rows(limit=15)]
            except (zipfile.BadZipFile, KeyError, ET.ParseError):
                return None
            info = read_bank_client(path, rows)
        return info
    if ext in (".xls", ".xml"):
        return read_bank_client(path)
    return None


def target_for(root: Path, info: Info, ext: str) -> Path:
    if info.kind == "sales":
        y, m = info.d1.year, info.d1.month
        name = f"{y}-{m:02d} {SALES_NAME}"
        if info.note:
            name = f"{info.d1:%Y-%m-%d}_{info.d2:%Y-%m-%d} {SALES_NAME}"
        return root / str(y) / f"{name}{ext}"
    bank = info.bank or "БАНК НЕ ОПРЕДЕЛЁН"
    cur = info.currency if info.currency in CURRENCIES else (info.currency or "???")
    return (root / bank / f"{cur} {info.account}" / str(info.d1.year)
            / f"{info.d1:%Y-%m-%d}_{info.d2:%Y-%m-%d}{ext}")


# ============================================================
# Раскладка
# ============================================================

def is_service(rel: Path) -> bool:
    """Служебные папки не разбираем. «_НЕ РАЗОБРАНО» — проверяем заново при каждом запуске."""
    parts = rel.parts[:-1]
    if parts and parts[0] == UNKNOWN and len(parts) == 1:
        return False
    return any(p.startswith("_") or p.startswith(".") for p in parts)


def is_junk(path: Path) -> bool:
    n = path.name
    return n.startswith(".") or n.startswith("~$") or n.startswith(".~lock") or n == JOURNAL


def remove_empty(root: Path) -> int:
    """Опустевшие после раскладки папки (кроме служебных «_…»). Файлы не удаляются."""
    n = 0
    dirs = [d for d in root.rglob("*") if d.is_dir() and not is_service(d.relative_to(root) / "x")]
    for d in sorted(dirs, key=lambda x: len(x.parts), reverse=True):
        try:
            if any(c.name != ".DS_Store" for c in d.iterdir()):
                continue
            for c in d.iterdir():
                c.unlink()
            d.rmdir()
            n += 1
        except OSError:
            pass
    return n


def free_name(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 1000):
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
    raise RuntimeError(f"не подобрать имя для {path}")


class Sorter:
    def __init__(self, root: Path, kind: str, apply: bool, log=print):
        self.root, self.kind, self.apply, self.log = root, kind, apply, log
        self.stats = {"на месте": 0, "разложено": 0, "дубли": 0, "новые версии": 0, "не разобрано": 0}
        self.journal: list[list[str]] = []

    def _move(self, src: Path, dst: Path, action: str):
        rel_src, rel_dst = src.relative_to(self.root), dst.relative_to(self.root)
        self.log(f"  {action}: {rel_src} → {rel_dst}")
        self.journal.append([datetime.now().isoformat(timespec="seconds"), action, str(rel_src), str(rel_dst)])
        if self.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)

    def run(self):
        self.log(f"Папка: {self.root}" + ("" if self.apply else "   [ТОЛЬКО ПЛАН, файлы не двигаются]"))
        files = sorted(p for p in self.root.rglob("*")
                       if p.is_file() and not is_junk(p) and not is_service(p.relative_to(self.root)))
        planned: dict[str, Path] = {}          # nfc-путь назначения → исходник (в рамках прогона)
        archive = self.root / ARCHIVE
        known = {sha1(p) for p in archive.rglob("*") if p.is_file() and not is_junk(p)} if archive.is_dir() else set()
        # Первый проход: что уже стоит на своих местах
        items = []
        placed: set[str] = set()               # хеши файлов на своих местах
        for path in files:
            digest, info = sha1(path), identify(path, self.kind)
            ok = info is not None and info.d1 is not None
            if ok and same_path(path, target_for(self.root, info, path.suffix.lower())):
                placed.add(digest)
                self.stats["на месте"] += 1
            else:
                items.append((path, digest, info))

        # Второй проход: новые файлы
        for path, digest, info in items:
            if digest in known or digest in placed:
                self._move(path, free_name(self.root / DUPS / path.name), "дубль")
                self.stats["дубли"] += 1
                continue
            placed.add(digest)
            if info is None or info.d1 is None:
                if path.parent == self.root / UNKNOWN:     # уже там — оставить
                    self.stats["не разобрано"] += 1
                    continue
                dst = free_name(self.root / UNKNOWN / path.name)
                self._move(path, dst, "не разобрано")
                self.stats["не разобрано"] += 1
                continue

            dst = target_for(self.root, info, path.suffix.lower())
            key = nfc(str(dst)).casefold()
            # где физически лежит файл, уже занявший это место (в плане — ещё на старом месте)
            other = planned[key] if (not self.apply and key in planned) else (dst if dst.exists() else None)
            if other is not None:
                if sha1(other) == sha1(path):
                    self._move(path, free_name(self.root / DUPS / path.name), "дубль")
                    self.stats["дубли"] += 1
                    continue
                self.stats["новые версии"] += 1
                arch_base = self.root / ARCHIVE / dst.relative_to(self.root)
                path_mtime, other_mtime = path.stat().st_mtime, other.stat().st_mtime
                if path_mtime >= other_mtime:          # новее — встаёт на место, старая в архив
                    stamp = datetime.fromtimestamp(other_mtime).strftime("%Y-%m-%d %H%M")
                    arch = free_name(arch_base.with_name(f"{arch_base.stem} (версия {stamp}){arch_base.suffix}"))
                    self._move(other, arch, "старая версия в архив")
                    self._move(path, dst, "новая версия")
                    planned[key] = dst if self.apply else path
                else:                                  # старее — сразу в архив
                    stamp = datetime.fromtimestamp(path_mtime).strftime("%Y-%m-%d %H%M")
                    arch = free_name(arch_base.with_name(f"{arch_base.stem} (версия {stamp}){arch_base.suffix}"))
                    self._move(path, arch, "старая версия в архив")
                continue

            note = f" ({info.note})" if info.note else ""
            self._move(path, dst, "разложен" + note)
            planned[key] = dst if self.apply else path
            self.stats["разложено"] += 1

        if self.apply:
            self.stats["пустых папок убрано"] = remove_empty(self.root)
        if self.apply and self.journal:
            jpath = self.root / JOURNAL
            new = not jpath.exists()
            with jpath.open("a", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                if new:
                    w.writerow(["когда", "действие", "откуда", "куда"])
                w.writerows(self.journal)
        self.log("  Итог: " + ", ".join(f"{k} {v}" for k, v in self.stats.items()))
        return self.stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Раскладка выписок и продаж Армении")
    ap.add_argument("--statements", type=Path, help="папка банковских выписок")
    ap.add_argument("--sales", type=Path, help="папка продаж")
    ap.add_argument("--dry-run", action="store_true", help="только показать план")
    args = ap.parse_args(argv)

    ok = True
    for kind, folder, title in (("statement", args.statements, "ВЫПИСКИ"), ("sales", args.sales, "ПРОДАЖИ")):
        if folder is None:
            continue
        print("=" * 60)
        print(title)
        if not folder.is_dir():
            print(f"  ! папка не найдена: {folder}")
            ok = False
            continue
        Sorter(folder.expanduser().resolve(), kind, apply=not args.dry_run).run()
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
