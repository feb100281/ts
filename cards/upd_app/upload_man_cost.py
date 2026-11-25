# cards/upd_app/upload_man_cost.py

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from conns import connect_db


def _to_decimal(value) -> Decimal | None:
    """
    Приводит себестоимость к Decimal:

        2 010,45
        2010.45
        2010,45

    Результат округляется до 2 знаков.
    """

    if value is None:
        return None

    text = (
        str(value)
        .strip()
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    if not text:
        return None

    try:
        return Decimal(text).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    except InvalidOperation:
        return None


def _channel(v):
    """Канал из шаблона: ВБ / Розница / Не распределено. Пустая ячейка — не менять."""
    from .parse_upd import channel_of
    return channel_of(v) if _norm(v) else None


def _norm(v) -> str:
    return " ".join(str(v or "").split()).strip().lower()


def read_man_cost_excel(
    excel_bytes: bytes,
) -> list[dict]:
    """
    Читает шаблон себестоимости (лист «УПД»). Колонки ищутся по шапке:
    ID, Позиция, Артикул, Размер, Себестоимость (за ед.).
    Подходят и старые шаблоны (ID в A, себестоимость в L).
    Пустая себестоимость — строка пропускается.
    """
    import io
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(excel_bytes), read_only=True, data_only=True)
    ws = wb["УПД"] if "УПД" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))

    head, cols = None, {}
    for n, r in enumerate(rows[:60]):
        cells = [_norm(v) for v in r]
        if cells and cells[0] == "id" and any("себестоимость" in c for c in cells):
            head = n
            for j, c in enumerate(cells):
                if c == "id":
                    cols.setdefault("id", j)
                elif c == "позиция":
                    cols.setdefault("pos", j)
                elif c.startswith("артикул"):
                    cols.setdefault("sa", j)
                elif c == "размер":
                    cols.setdefault("size", j)
                elif c == "канал":
                    cols.setdefault("channel", j)
                elif c.startswith("себестоимость") and "сумма" not in c:
                    cols.setdefault("cost", j)
            break
    if head is None or "cost" not in cols:
        raise ValueError("Не нашла шапку с колонками «ID» и «Себестоимость» на листе «УПД».")

    get = lambda r, k: r[cols[k]] if k in cols and cols[k] < len(r) else None
    result, seen, empty = [], set(), 0
    for r in rows[head + 1:]:
        try:
            row_id = int(str(get(r, "id")).strip())
        except (TypeError, ValueError):
            continue                                   # итоги и пустые строки
        if row_id in seen:
            raise ValueError(f"В Excel повторяется ID {row_id}.")
        seen.add(row_id)
        cost = _to_decimal(get(r, "cost"))
        channel = _channel(get(r, "channel")) if "channel" in cols else None
        if cost is None:
            empty += 1
            if channel is None:
                continue
        pos = get(r, "pos")
        result.append({
            "channel": channel,
            "id": row_id,
            "pos": int(pos) if isinstance(pos, (int, float)) else None,
            "sa": _norm(get(r, "sa")),
            "size": _norm(get(r, "size")),
            "man_cost_per_unit": cost,
        })

    if not result:
        raise ValueError("В файле не заполнены ни себестоимость, ни канал.")
    return result, empty


def upload_man_cost(
    upd_id,
    excel_bytes: bytes,
) -> dict:
    """
    Себестоимость в строки открытого УПД. Строка ищется по ID, а если УПД
    перезагружали и ID сменились — по позиции, артикулу и размеру.
    Строки, не найденные ни так, ни так, — ошибка, ничего не сохраняется.
    """
    upd_id = int(upd_id)
    rows, empty = read_man_cost_excel(excel_bytes)

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, upd_pos, upd_sa_name, upd_size, upd_amount_vatless, upd_qty
                FROM public.upd_income_lines
                WHERE upd_document_id = %s
                """,
                (upd_id,),
            )
            lines = cur.fetchall()
            by_id = {int(l[0]): l for l in lines}
            by_pos = {(l[1], _norm(l[2]), _norm(l[3])): l for l in lines}

            updates, missing, by_key = [], [], 0
            for r in rows:
                line = by_id.get(r["id"])
                if line is None:
                    line = by_pos.get((r["pos"], r["sa"], r["size"]))
                    by_key += line is not None
                if line is None:
                    missing.append(r["id"])
                    continue
                updates.append((r["man_cost_per_unit"], line[0], upd_id, line, r["channel"]))

            if missing:
                preview = ", ".join(map(str, missing[:10])) + (", …" if len(missing) > 10 else "")
                raise ValueError(
                    "Excel не соответствует открытому УПД. "
                    f"Не найдены строки с ID: {preview}. Изменения не сохранены."
                )

            cur.executemany(
                """
                UPDATE public.upd_income_lines
                SET man_cost_per_unit = COALESCE(%s, man_cost_per_unit),
                    channel = COALESCE(%s, channel)
                WHERE id = %s AND upd_document_id = %s
                """,
                [(u[0], u[4], u[1], u[2]) for u in updates],
            )
        conn.commit()

    priced = [u for u in updates if u[0] is not None]
    cost = sum((u[0] * Decimal(str(u[3][5] or 0)) for u in priced), Decimal("0"))
    base = sum((Decimal(str(u[3][4] or 0)) for u in priced), Decimal("0"))
    return {
        "updated": len(priced),
        "channels": sum(1 for u in updates if u[4] is not None),
        "by_key": by_key,
        "empty": empty,
        "total_cost": cost.quantize(Decimal("0.01")),
        "base": base.quantize(Decimal("0.01")),
        "markup": (cost / base - 1) if base else None,
    }
