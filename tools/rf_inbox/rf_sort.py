"""
Раскладка папки выписок российских банков:

    БАНК / ВАЛЮТА СЧЁТ / ГГГГ / ММ. Месяц / ГГГГ-ММ-ДД_ГГГГ-ММ-ДД.расширение

Закрытые счета — так же, внутри «00 ЗАКРЫТЫЕ СЧЕТА». Банк, счёт и период берутся
из содержимого (txt 1С, xlsx, html, текст PDF), PDF без текста — у txt с тем же
именем, иначе из имени файла и папки. Точные копии — в «_ДУБЛИ», нераспознанные —
в «_НЕ РАЗОБРАНО». Каждое перемещение пишется в «_журнал раскладки.csv».
Файлы не удаляются; опустевшие папки убираются. Уже разложенное повторно не трогается.

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

CLOSED = "00 ЗАКРЫТЫЕ СЧЕТА"
DUPS, UNKNOWN = "_ДУБЛИ", "_НЕ РАЗОБРАНО"
JOURNAL = "_журнал раскладки.csv"
OTHER = "ПРОЧЕЕ"
SKIP_EXT = {".command", ".app"}
MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август",
          "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# признак в тексте, имени файла или папке → банк
BANKS = [(re.compile(rx, re.I), short) for rx, short in [
    (r"альф|alfa", "АЛЬФА-БАНК"),
    (r"втб|vtb", "ВТБ"),
    (r"отп|otp", "ОТП БАНК"),
    (r"т-банк|тбанк|тинькоф|tinkoff|(^|[\s_\-])тб([\s_\-.]|$)", "Т-БАНК"),
    (r"банк казани|казан|(^|[\s_\-])бк([\s_\-.]|$)", "БАНК КАЗАНИ"),
    (r"вайлдбер|wildberr|вб банк|(^|[\s_\-])вб([\s_\-.]|$)|bankfaktura", "ВБ БАНК"),
    (r"хлынов|(^|[\s_\-])бх([\s_\-.]|$)", "ХЛЫНОВ"),
    (r"бжф|бланк|жилфин", "БЖФ"),
    (r"экспо", "ЭКСПОБАНК"),
    (r"морск", "МОРСКОЙ БАНК"),
    (r"совком", "СОВКОМБАНК"),
    (r"сбер", "СБЕРБАНК"),
]]
SHORTS = {s for _, s in BANKS}
CURRENCY = {"810": "RUB", "643": "RUB", "156": "CNY", "978": "EUR", "840": "USD",
            "051": "AMD", "398": "KZT", "933": "BYN", "417": "KGS", "784": "AED"}
CUR_WORDS = [(re.compile(r"юан|cny", re.I), "CNY"), (re.compile(r"доллар|usd", re.I), "USD"),
             (re.compile(r"евро|eur", re.I), "EUR"), (re.compile(r"драм|amd", re.I), "AMD"),
             (re.compile(r"рубл|rub", re.I), "RUB")]

ACC = re.compile(r"(?<!\d)(40[5-8]\d{17})(?!\d)")
D = r"(\d{2})[./](\d{2})[./](\d{4})"
PERIOD = re.compile(rf"(?:с|за период|период[:\s]*)\s*{D}\s*(?:г\.?)?\s*(?:по|-|—|–|до)\s*{D}", re.I)
OUR = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:_(\d{4})-(\d{2})-(\d{2}))?")


@dataclass
class Info:
    bank: str | None = None
    account: str | None = None
    cur: str | None = None
    d1: date | None = None
    d2: date | None = None
    how: str = ""


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def mk(y, m, d) -> date | None:
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def bank_of(text: str) -> str | None:
    t = nfc(text or "")
    return next((s for rx, s in BANKS if rx.search(t)), None)


def cur_of(text: str) -> str | None:
    t = nfc(text or "")
    return next((c for rx, c in CUR_WORDS if rx.search(t)), None)


def stem_key(p: Path) -> tuple:
    return (p.parent, re.sub(r"[^0-9a-zа-яё]", "", nfc(p.stem).casefold()))


# ---------- чтение ----------

JXA = ('ObjC.import("PDFKit");function run(a){var d=$.PDFDocument.alloc.initWithURL('
       '$.NSURL.fileURLWithPath(a[0]));if(!d||d.isNil())return "";var s=d.string;'
       'return s&&!s.isNil()?ObjC.unwrap(s):"";}')


def pdf_text(p: Path) -> str:
    """Текст PDF средствами macOS (PDFKit), без сторонних библиотек."""
    if sys.platform != "darwin":
        return ""
    try:
        return subprocess.run(["osascript", "-l", "JavaScript", "-e", JXA, str(p)],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def body(p: Path) -> str:
    ext = p.suffix.lower()
    try:
        if ext == ".pdf":
            return pdf_text(p)
        if ext in (".xlsx", ".xlsm"):
            with zipfile.ZipFile(p) as z:
                return " ".join(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore"))
                                for n in z.namelist()
                                if n.endswith("sharedStrings.xml") or re.match(r"xl/worksheets/sheet\d+\.xml", n))
        if ext in (".html", ".htm", ".xml", ".csv"):
            return re.sub(r"<[^>]+>", " ", p.read_bytes().decode("utf-8", "ignore"))
        if ext == ".xls":
            import xlrd
            wb = xlrd.open_workbook(str(p), on_demand=True)
            return "\n".join(" ".join(map(str, sh.row_values(r)))
                             for sh in wb.sheets()[:3] for r in range(min(sh.nrows, 400)))
    except Exception:
        return ""
    return ""


def read_1c(p: Path) -> Info | None:
    raw = p.read_bytes()
    if b"1CClientBankExchange" not in raw[:300]:
        return None
    t = raw.decode("cp1251", "replace")
    g = lambda k: [v.strip() for v in re.findall(rf"^{k}=(.*)$", t, re.M) if v.strip()]
    accs = list(dict.fromkeys(g("РасчСчет")))
    st = [mk(*reversed(v.split("."))) for v in g("ДатаНачала") if v.count(".") == 2]
    en = [mk(*reversed(v.split("."))) for v in g("ДатаКонца") if v.count(".") == 2]
    st, en = [x for x in st if x], [x for x in en if x]
    sender = (g("Отправитель") or [""])[0]
    return Info(bank_of(sender), accs[0] if accs else None, None,
                min(st) if st else None, max(en) if en else None, "1С")


def dates(text: str) -> tuple[date | None, date | None]:
    m = PERIOD.search(text)
    if m:
        return mk(*reversed(m.groups()[:3])), mk(*reversed(m.groups()[3:]))
    ds = sorted(x for x in (mk(*reversed(g)) for g in re.findall(D, text)) if x and 2015 <= x.year <= 2035)
    return (ds[0], ds[-1]) if ds else (None, None)


def name_dates(name: str) -> tuple[date | None, date | None]:
    m = OUR.match(name)
    if m:
        a = mk(*m.groups()[:3])
        return a, (mk(*m.groups()[3:]) if m.group(4) else a)
    m = re.search(r"(20\d{2})[\s._-]?(\d{2})(?:[\s._-]?(\d{2}))?(?!\d)", name)
    if m:
        a = mk(m.group(1), m.group(2), m.group(3) or "01")
        return a, a
    return None, None


# ---------- известные счета ----------

def known(root: Path) -> dict[str, tuple[str, bool]]:
    """Счёт → (банк, закрыт) по уже разложенным txt 1С."""
    votes: dict[str, Counter] = defaultdict(Counter)
    for p in root.rglob("*.txt"):
        rel = p.relative_to(root)
        if any(x.startswith(("_", ".")) for x in rel.parts[:-1]):
            continue
        i = read_1c(p)
        if not i or not i.account:
            continue
        bank = bank_of(" ".join(rel.parts[:-1])) or i.bank
        if bank:
            votes[i.account][(bank, rel.parts[0] == CLOSED)] += 1
    return {a: c.most_common(1)[0][0] for a, c in votes.items()}


# ---------- раскладка ----------

def pick(found: list[str], accs: dict, bank: str | None) -> str | None:
    """Из найденных счетов: свой счёт этого банка, иначе неизвестный, иначе любой свой."""
    found = list(dict.fromkeys(found))
    if bank:
        same = [a for a in found if accs.get(a, ("",))[0] == bank]
        if same:
            return same[0]
        alien = {a for a in found if a in accs}            # счета других банков (карточка 51 и т. п.)
        rest = [a for a in found if a not in alien]
        if rest:
            return rest[0]
        return None
    ours = [a for a in found if a in accs]
    return (ours or found or [None])[0]


def identify(p: Path, rel: Path, accs: dict) -> Info:
    folders = " ".join(rel.parts[:-1])
    i = read_1c(p) if p.suffix.lower() == ".txt" else None
    if i is None:
        i = Info()
        n1, n2 = name_dates(p.name)
        found = ACC.findall(p.name)
        text = ""
        if not found or not n1:
            text = body(p)
            found = found or ACC.findall(text)
        i.account = pick(found, accs, bank_of(folders) or bank_of(p.name) or bank_of(text[:600]))
        if OUR.match(p.name):
            i.d1, i.d2, i.how = n1, n2, "имя"
        elif text:
            i.d1, i.d2 = dates(text)
            i.how = "содержимое"
        i.bank = bank_of(text[:600])
        if not i.d1:
            i.d1, i.d2 = n1, n2
            i.how = i.how or "имя файла"
    if i.account in accs:
        i.bank = accs[i.account][0]
    i.bank = i.bank or bank_of(folders) or bank_of(p.name)
    i.cur = CURRENCY.get(i.account[5:8], i.account[5:8]) if i.account else (cur_of(folders) or cur_of(p.name))
    if i.bank and not i.account:                       # «счёт 370» в имени папки или файла
        hint = re.findall(r"(?:сч[её]т|№)\s*(\d{3,})|_(\d{3})(?:[\s_(]|$)", folders + " " + nfc(p.stem))
        tails = [x for t in hint for x in t if x]
        hit = [a for a, (b, _) in accs.items() if b == i.bank and any(a.endswith(t) for t in tails)]
        if len(hit) == 1:
            i.account = hit[0]
            i.cur = CURRENCY.get(i.account[5:8])
    if i.bank and not i.account:                       # единственный счёт банка в нужной валюте
        same = [a for a, (b, _) in accs.items() if b == i.bank and (not i.cur or CURRENCY.get(a[5:8]) == i.cur)]
        if len(same) == 1:
            i.account, i.cur = same[0], CURRENCY.get(same[0][5:8])
    return i


def target(root: Path, p: Path, i: Info, accs: dict, rel: Path) -> Path:
    if not i.bank:
        return root / UNKNOWN / p.name
    closed = accs.get(i.account, (None, rel.parts[0] == CLOSED))[1] if i.account else rel.parts[0] == CLOSED
    base = (root / CLOSED if closed else root) / i.bank
    acc_dir = f"{i.cur} {i.account}" if i.account else (i.cur or OTHER)
    folder = base / acc_dir
    if not i.d1:
        return folder / OTHER / p.name
    span = f"{i.d1:%Y-%m-%d}" if i.d1 == i.d2 or not i.d2 else f"{i.d1:%Y-%m-%d}_{i.d2:%Y-%m-%d}"
    return folder / f"{i.d1:%Y}" / f"{i.d1:%m}. {MONTHS[i.d1.month - 1]}" / f"{span}{note(p.name)}{p.suffix.lower()}"


NOTES = [("карточк", "карточка"), ("реестр", "реестр"), ("закры", "закрытие"), ("справк", "справка"),
         ("остат", "остатки")]


def note(name: str) -> str:
    low = nfc(name).casefold()
    words = list(dict.fromkeys(w for k, w in NOTES if k in low))
    return (" " + " ".join(words)) if words else ""


ACC_DIR = re.compile(r"^([A-Z]{3}( \d{20})?|" + OTHER + ")$")


def placed(parts: tuple) -> bool:
    if parts and parts[0] == CLOSED:
        parts = parts[1:]
    return len(parts) >= 3 and parts[0] in SHORTS and ACC_DIR.match(parts[1]) is not None


def skip(rel: Path) -> bool:
    n = rel.name
    return (n.startswith((".", "~$")) or n in (JOURNAL, "Icon\r", "Icon") or rel.suffix.lower() in SKIP_EXT
            or rel.parts[0] == DUPS or placed(rel.parts))


def make_dirs(root: Path, folder: Path) -> list[tuple[Path, Path]]:
    """mkdir с исправлением регистра: на Mac «Втб» и «ВТБ» — одна папка. Возвращает переименования."""
    renamed = []
    cur = root
    for part in folder.relative_to(root).parts:
        want = cur / part
        if cur.is_dir():
            twin = next((c for c in cur.iterdir() if c.name.casefold() == part.casefold() and c.name != part), None)
            if twin is not None:
                tmp = cur / f".{part}.tmp"
                twin.rename(tmp)
                tmp.rename(want)
                renamed.append((twin, want))
        want.mkdir(exist_ok=True)
        cur = want
    return renamed


def remap(p: Path, moves: list[tuple[Path, Path]]) -> Path:
    for old, new in moves:
        try:
            p = new / p.relative_to(old)
        except ValueError:
            pass
    return p


def sort_folder(root: Path, apply: bool, log=print) -> Counter:
    files = sorted(p for p in root.rglob("*") if p.is_file() and not skip(p.relative_to(root)))
    stats = Counter({"файлов": len(files)})
    if not files:
        log("Новых файлов нет.")
        return stats
    accs = known(root)
    infos = {p: identify(p, p.relative_to(root), accs) for p in files}
    # PDF и пр. без счёта/периода — у txt с тем же именем в той же папке
    by_stem = defaultdict(list)
    for p in files:
        by_stem[stem_key(p)].append(p)
    for p, i in infos.items():
        if i.account and i.d1 and i.how not in ("имя файла",):
            continue
        twin = next((q for q in by_stem[stem_key(p)] if q != p and infos[q].how == "1С" and infos[q].account), None)
        if twin:
            t = infos[twin]
            infos[p] = Info(t.bank, t.account, t.cur, t.d1, t.d2, "пара txt")

    taken: dict[Path, str] = {}
    rows = []
    moves: list[tuple[Path, Path]] = []
    for orig in files:
        rel, i = orig.relative_to(root), infos[orig]
        p = remap(orig, moves)                         # папку могли переименовать (регистр)
        dst = target(root, orig, i, accs, rel)
        digest = sha1(p)
        if dst == p:
            stats["на месте"] += 1
            taken[dst] = digest
            continue
        why, stem, ext, n = i.how, dst.stem, dst.suffix, 2
        while True:
            owner = taken.get(dst) or (sha1(dst) if dst.exists() else None)
            if owner is None:
                break
            if owner == digest:
                why = "дубль: " + str(dst.relative_to(root))
                dst, k = root / DUPS / rel.name, 2
                while dst.exists() or dst in taken:
                    dst = (root / DUPS / rel.name).with_name(f"{rel.stem} ({k}){rel.suffix}")
                    k += 1
                break
            dst = dst.with_name(f"{stem} ({n}){ext}")
            n += 1
        taken[dst] = digest
        top = dst.relative_to(root).parts[0]
        stats["дубли" if top == DUPS else "не разобрано" if top == UNKNOWN else "разложено"] += 1
        rows.append((str(rel), str(dst.relative_to(root)), why))
        log(f"  {rel}  →  {dst.relative_to(root)}   [{why}]")
        if apply:
            moves += make_dirs(root, dst.parent)
            remap(p, moves).rename(dst)

    if apply and rows:
        j = root / JOURNAL
        new = not j.exists()
        with j.open("a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            if new:
                w.writerow(["когда", "было", "стало", "как определено"])
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            w.writerows([now, *r] for r in rows)
    if apply and rows:
        stats["пустых папок убрано"] = remove_empty(root)
    log("Итог: " + ", ".join(f"{k} {v}" for k, v in stats.items())
        + ("" if apply else "  — пробный прогон, файлы не перемещались"))
    return stats


def remove_empty(root: Path) -> int:
    """Папки, опустевшие после раскладки (служебный .DS_Store не в счёт). Файлы не удаляются."""
    n = 0
    for d in sorted((x for x in root.rglob("*") if x.is_dir()), key=lambda x: len(x.parts), reverse=True):
        rest = [c for c in d.iterdir() if c.name != ".DS_Store"]
        if rest:
            continue
        try:
            for c in d.iterdir():
                c.unlink()
            d.rmdir()
            n += 1
        except OSError:
            pass
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Раскладка выписок российских банков")
    ap.add_argument("--root", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).expanduser()
    if not root.is_dir():
        print(f"Нет папки: {root}")
        return 1
    print(f"Папка: {root}")
    sort_folder(root, apply=not a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
