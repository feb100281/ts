"""Разбор файлов УПД в строки для загрузки: parquet, xml (ФНС), xls/xlsx (счёт-фактура)."""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from tempfile import NamedTemporaryFile

FIELDS = ("brand", "upd_sa_name", "upd_title", "upd_size", "upd_unit", "upd_qty",
          "upd_price_vatless", "upd_amount_vatless", "upd_vat_rate", "upd_vat_amount",
          "upd_amount_vatadd", "man_cost_per_unit")


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    try:
        return float(s) if s else None
    except ValueError:
        return None


def vat_rate(v):
    """'20%' → 20; 0.2 → 20; 'без НДС' → 0."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str) and re.search(r"без", v, re.I):
        return 0.0
    r = num(str(v).replace("%", ""))
    if r is not None and 0 < r < 1:
        r = round(r * 100, 2)
    return r


def text(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return s or None


# --- parquet ---

def read_parquet(data: bytes) -> list[dict]:
    import duckdb
    with NamedTemporaryFile(suffix=".parquet") as tmp:
        tmp.write(data)
        tmp.flush()
        with duckdb.connect() as con:
            rows = con.execute("SELECT * FROM read_parquet(?)", [tmp.name]).fetchall()
            cols = [x[0] for x in con.description]
    return [dict(zip(cols, r)) for r in rows]


# --- xml УПД (формат ФНС) ---

def read_xml(data: bytes) -> list[dict]:
    root = ET.fromstring(data)
    out = []
    for item in root.iter("СведТов"):
        code = None
        add = item.find("ДопСведТов")
        if add is not None:
            code = add.get("КодТов")
        sa, size = (code.split(" - ", 1) + [None])[:2] if code else (None, None)
        vat = None
        tax = item.find("СумНал")
        if tax is not None:
            t = tax.find("СумНал")
            vat = num(t.text) if t is not None else (0.0 if tax.find("БезНДС") is not None else None)
        title = item.get("НаимТов")
        out.append({
            "upd_sa_name": text(sa),
            "upd_title": title.split("(", 1)[0].strip() if title else None,
            "upd_size": text(size),
            "upd_unit": item.get("НаимЕдИзм"),
            "upd_qty": num(item.get("КолТов")),
            "upd_price_vatless": num(item.get("ЦенаТов")),
            "upd_amount_vatless": num(item.get("СтТовБезНДС")),
            "upd_vat_rate": vat_rate(item.get("НалСт")),
            "upd_vat_amount": vat,
            "upd_amount_vatadd": num(item.get("СтТовУчНал")),
        })
    if not out:
        raise ValueError("В xml нет товарных строк (СведТов)")
    return out


# --- xls/xlsx: печатная форма счёта-фактуры ---

COLS = [  # (поле, признак в шапке) — порядок важен: более точные признаки раньше
    ("title", r"наименование"),
    ("art", r"^артикул"),
    ("number", r"^номер$|модель"),
    ("color", r"^цвет"),
    ("size", r"^размер"),
    ("unit", r"единица|ед\.? ?изм"),
    ("qty", r"^коли"),
    ("price", r"^цена"),
    ("vatless", r"без налога"),
    ("rate", r"налоговая ставка|ставка"),
    ("vat", r"сумма налога"),
    ("vatadd", r"с налогом"),
]


def _norm(v) -> str:
    return re.sub(r"[\s\-]+", " ", str(v or "")).strip().lower().replace("- ", "")


def _header(rows):
    for i, row in enumerate(rows[:60]):
        cells = [_norm(v).replace(" ", "") if "коли" in _norm(v).replace(" ", "") else _norm(v) for v in row]
        if any("наименование" in c for c in cells) and any("без налога" in c for c in cells):
            cols = {}
            for key, pat in COLS:
                for j, c in enumerate(cells):
                    if j not in cols.values() and c and re.search(pat, c):
                        cols[key] = j
                        break
            return i, cols
    raise ValueError("Не нашла шапку таблицы (Наименование … без налога)")


def _sheet(sheets: dict):
    for name in sheets:
        if re.search(r"сч[её]т.?фактур|упд", name, re.I):
            return name
    return next(iter(sheets))


def read_excel(data: bytes, filename: str) -> list[dict]:
    import pandas as pd
    engine = "xlrd" if filename.lower().endswith(".xls") else "openpyxl"
    book = pd.ExcelFile(io.BytesIO(data), engine=engine)
    name = _sheet({s: None for s in book.sheet_names})
    df = book.parse(name, header=None, dtype=object)
    rows = df.where(df.notna(), None).values.tolist()
    h, c = _header(rows)
    get = lambda r, k: r[c[k]] if k in c else None
    out = []
    for r in rows[h + 1:]:
        if num(r[0]) is None or not get(r, "title"):        # только нумерованные товарные строки
            continue
        title = text(get(r, "title"))
        sa = text(get(r, "number")) or text(get(r, "art"))
        out.append({
            "_pos": int(num(r[0])),
            "brand": title.split()[-1] if title and len(title.split()) > 1 else None,
            "upd_sa_name": sa,
            "upd_title": title,
            "upd_size": text(get(r, "size")),
            "upd_unit": text(get(r, "unit")),
            "upd_qty": num(get(r, "qty")),
            "upd_price_vatless": num(get(r, "price")),
            "upd_amount_vatless": num(get(r, "vatless")),
            "upd_vat_rate": vat_rate(get(r, "rate")),
            "upd_vat_amount": num(get(r, "vat")),
            "upd_amount_vatadd": num(get(r, "vatadd")),
        })
    if not out:
        raise ValueError(f"На листе «{name}» нет товарных строк")
    _apply_channels(book, out)
    for r in out:
        r.pop("_pos", None)
    return out


# --- «Рабочий щит»: канал продаж и отгрузка по номеру строки ---

def channel_of(v):
    s = _norm(v)
    if not s:
        return "none"
    if re.search(r"вб|wb|wildberr|вайлд", s):
        return "wb"
    if re.search(r"ритейл|розниц|retail|магазин", s):
        return "retail"
    return "none"


def _apply_channels(book, rows):
    """Если в файле есть лист с колонкой «Канал продаж» — канал по каждой строке; пустой → не распределено."""
    sheet = next((n for n in book.sheet_names if re.search(r"рабоч", n, re.I)), None)
    if not sheet:
        return
    data = book.parse(sheet, header=None, dtype=object)
    data = data.where(data.notna(), None).values.tolist()
    for h, row in enumerate(data[:30]):
        cells = [_norm(v) for v in row]
        ch = next((j for j, c in enumerate(cells) if "канал" in c), None)
        if ch is None:
            continue
        sh = next((j for j, c in enumerate(cells) if "отгруз" in c), None)
        nb = next((j for j, c in enumerate(cells) if re.fullmatch(r"(номер|модель)", c)), None)
        qt = next((j for j, c in enumerate(cells) if c.replace(" ", "").startswith(("коли", "кодич"))), None)
        marks = {}
        for r in data[h + 1:]:
            pos = num(r[0])
            if pos is None or (qt is not None and not num(r[qt])):
                continue
            marks[int(pos)] = (channel_of(r[ch]),
                               (_norm(r[sh]) in ("да", "yes", "1")) if sh is not None and _norm(r[sh]) else None,
                               text(r[nb]) if nb is not None else None)
        for r in rows:
            m = marks.get(r["_pos"])
            if m and (m[2] is None or m[2] == r["upd_sa_name"]):   # сверка по артикулу
                r["channel"], r["shipped"] = m[0], m[1]
            else:
                r["channel"] = "none"
        return


def read_file(data: bytes, filename: str) -> list[dict]:
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    if ext == "parquet":
        return read_parquet(data)
    if ext == "xml":
        return read_xml(data)
    if ext in ("xls", "xlsx", "xlsm"):
        return read_excel(data, filename)
    raise ValueError("Поддерживаются файлы .parquet, .xml, .xls, .xlsx")
