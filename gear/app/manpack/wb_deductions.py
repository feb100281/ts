# gear/app/manpack/wb_deductions.py
"""Удержания WB (проверка): что WB удержал из выплат, по обоснованиям.

Финансовые удержания (займы, кредиты, проценты, овердрафт, перевод на баланс заёмщика)
— не расход WB: их надо отразить на договоре займа / кредита. Остальные — справочно.
Источник — wb_dwh.realization_kv (field = 'deduction'). Скрипт только читает базу.
"""
from __future__ import annotations

import io
import re
from datetime import date, timedelta

import pandas as pd

NEW_DAYS = 28                                  # «новое» — впервые за последние 4 недели
FIN_RE = re.compile(r"займ|заём|заем|кредит|процент|овердрафт|финанс|баланс заёмщика|"
                    r"баланс заемщика", re.I)
NUM_RE = re.compile(r"№\s*([\w/\-]+)|(\d{10,})|\b([А-ЯA-Z]{1,4}-\d+/\d+)", re.I)

DED_SQL = """
SELECT date_from::DATE AS d, COALESCE(bonus_type_name, '(без обоснования)') AS btn,
       SUM(value) / 100.0 AS amount, COUNT(*) AS n
FROM pg.wb_dwh.realization_kv
WHERE field = 'deduction' AND date_from::DATE <= ?
GROUP BY 1, 2
HAVING SUM(value) <> 0
"""
# корректировки GL, которыми разнесены удержания: Кт статья 540101 (куда их кладёт WB ETL)
ADJ_SQL = """
SELECT g.id, g.date::DATE AS d, CAST(g.amount AS DOUBLE) AS amount
FROM pg.public.grossbook_gladjustment g
JOIN pg.public.corporate_cfitems s ON s.id = g.cr_subconto_id
WHERE CAST(s.code AS VARCHAR) = '540101' AND g.date <= ?
"""
CTR_SQL = """
SELECT k.id AS cid, k.number,
       COALESCE(NULLIF(TRIM(cp.name), ''), 'Без контрагента') || ' · '
           || COALESCE(ct.title, 'Договор') || ' № ' || COALESCE(k.number, 'б/н')
           || ' · id ' || CAST(k.id AS VARCHAR) AS contract
FROM pg.public.contracts_contracts k
LEFT JOIN pg.public.contracts_contractstitle ct ON ct.id = k.title_id
LEFT JOIN pg.public.counterparties_counterparty cp ON cp.id = k.cp_id
WHERE k.number IS NOT NULL AND TRIM(k.number) <> ''
"""


def kind(btn: str) -> str:
    s = btn.lower()
    if "основного долга" in s:
        return "Тело"
    if "процент" in s:
        return "Проценты"
    if "комисси" in s and FIN_RE.search(s):
        return "Комиссия"
    return "Тело и проценты вместе"


def doc_number(btn: str) -> str:
    m = NUM_RE.search(btn)
    return next((g for g in m.groups() if g), "") if m else ""


def build(report_date: date, con) -> dict:
    ded = con.execute(DED_SQL, [report_date]).df()
    ctr = con.execute(CTR_SQL).df()
    ded["d"] = pd.to_datetime(ded["d"])
    ded["fin"] = ded["btn"].map(lambda s: bool(FIN_RE.search(s)))
    # обоснование без чисел — для сводки: «Штраф за … 12345» и «… 67890» — один вид
    ded["kind_txt"] = ded["btn"].where(ded["fin"], ded["btn"].str.replace(r"\d+", "N", regex=True))

    by_num = {str(n).strip(): c for n, c in zip(ctr["number"], ctr["contract"])}
    fin = ded[ded["fin"]].copy()
    fin["what"] = fin["btn"].map(kind)
    fin["num"] = fin["btn"].map(doc_number)
    fin["contract"] = fin["num"].map(lambda n: by_num.get(n, "") if n else "")
    # разнесено корректировками GL: по дате отчёта, иначе — по месяцу целиком
    try:
        adj = con.execute(ADJ_SQL, [report_date]).df()
    except Exception:                            # журнала ещё нет — отчёт без колонки
        adj = pd.DataFrame(columns=["id", "d", "amount"])
    adj["d"] = pd.to_datetime(adj["d"])
    adj["m"] = adj["d"].dt.to_period("M")
    fin["m"] = fin["d"].dt.to_period("M")
    a_m = adj.groupby("m")["amount"].sum()
    ids_m = adj.groupby("m")["id"].agg(lambda s: ", ".join(f"#{i}" for i in sorted(s)))
    f_m = fin.groupby("m")["amount"].sum()
    fin["posted"], fin["adj_ids"] = "нет", ""
    for d, g in fin.groupby("d"):
        free = adj[adj["d"] == d].copy()
        rest = []
        # 1) точное совпадение суммы за дату
        for idx, r in g.iterrows():
            hit = free[(free["amount"] - r["amount"]).abs() < 0.01]
            if len(hit):
                k = hit.index[0]
                fin.loc[idx, ["posted", "adj_ids"]] = ["разнесено", f"#{free.at[k, 'id']}"]
                free = free.drop(k)
            else:
                rest.append(idx)
        if not rest:
            continue
        # 2) оставшиеся строки за дату закрыты остальными корректировками за дату в сумме
        left = fin.loc[rest, "amount"].sum()
        ids = ", ".join(f"#{x}" for x in sorted(free["id"]))
        if len(free) and abs(free["amount"].sum() - left) < 0.5:
            fin.loc[rest, ["posted", "adj_ids"]] = ["разнесено", ids]
        elif len(free):
            fin.loc[rest, ["posted", "adj_ids"]] = ["частично", ids]
    # 3) не сошлось по дате, но месяц закрыт целиком (корректировка одной суммой за месяц)
    for idx in fin.index[fin["posted"] != "разнесено"]:
        m = fin.at[idx, "m"]
        if a_m.get(m, 0.0) >= f_m[m] - 0.5:
            fin.loc[idx, ["posted", "adj_ids"]] = ["разнесено за месяц", ids_m.get(m, "")]
    fin = fin.sort_values(["d", "btn"], ascending=[False, True])

    new_from = pd.Timestamp(report_date - timedelta(days=NEW_DAYS))
    s = (ded.groupby("kind_txt")
         .agg(fin=("fin", "max"), first=("d", "min"), last=("d", "max"),
              n=("n", "sum"), amount=("amount", "sum"))
         .reset_index())
    s["new"] = s["first"] >= new_from
    s = s.sort_values(["fin", "new", "amount"], ascending=[False, False, False])

    month = (fin.assign(m=fin["d"].dt.to_period("M").dt.to_timestamp())
             .pivot_table(index="m", columns="what", values="amount", aggfunc="sum", fill_value=0)
             .sort_index(ascending=False))
    month["Итого, ₽"] = month.sum(axis=1)
    month["Разнесено корр. GL, ₽"] = [a_m.get(pd.Period(m, "M"), 0.0) for m in month.index]
    month["Осталось, ₽"] = month["Итого, ₽"] - month["Разнесено корр. GL, ₽"]
    return {"fin": fin, "sum": s, "month": month, "total": ded["amount"].sum(),
            "fin_total": fin["amount"].sum(), "new_from": new_from}


def to_excel(res: dict, report_date: date) -> bytes:
    from gear.management.commands import mp
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"nan_inf_to_errors": True})
    base = {"font_name": mp.FONT, "font_size": 9, "font_color": "#" + mp.TEXT, "valign": "top"}
    line = {"bottom": 1, "bottom_color": "#" + mp.LINE}
    F = lambda **k: wb.add_format({**base, **k})
    fmt = {
        "title": F(font_size=14, bold=True), "sub": F(font_color="#" + mp.TEXT_2),
        "hdr": F(bold=True, font_color="#FFFFFF", bg_color="#" + mp.NAVY, text_wrap=True,
                 align="center", valign="vcenter", border=1, border_color="#" + mp.NAVY_2),
        "text": F(**line), "wrap": F(**line, text_wrap=True),
        "date": F(**line, num_format="dd.mm.yyyy"), "month": F(**line, num_format="mmm yyyy"),
        "money": F(**line, num_format=mp.FMT_MONEY_DEC),
        "flag": F(**line, bold=True, font_color="#9C2A00"),
        "ok": F(**line, font_color="#" + mp.NAVY_3),
        "tot": F(bold=True, top=1, num_format=mp.FMT_MONEY_DEC),
        "totl": F(bold=True, top=1), "lbl": F(bold=True, font_color="#" + mp.NAVY_3, **line),
    }
    sub = (f"Удержания WB по {report_date:%d.%m.%Y} · всего {res['total']:,.0f} ₽, из них "
           f"финансовые {res['fin_total']:,.0f} ₽ · сформировано "
           + pd.Timestamp.now().strftime("%d.%m.%Y %H:%M")).replace(",", " ")
    num = lambda v: 0.0 if v != v or abs(v) < 0.005 else float(v)

    def head(ws, title, cols, row=3):
        ws.write(0, 0, title, fmt["title"])
        ws.write(1, 0, sub, fmt["sub"])
        for j, (h, w) in enumerate(cols):
            ws.write(row, j, h, fmt["hdr"])
            ws.set_column(j, j, w)
        ws.set_row(row, 30)
        ws.freeze_panes(row + 1, 0)

    # 1. Финансовые удержания — построчно
    ws = wb.add_worksheet("Финансовые")
    head(ws, "Финансовые удержания WB: займы, кредиты, проценты", (
        ("Дата отчёта WB", 12), ("Обоснование WB", 70), ("Вид", 20), ("№ в обосновании", 18),
        ("Договор у нас", 60), ("Сумма, ₽", 16), ("Разнесено", 18), ("Корректировки GL", 22)))
    f = res["fin"]
    for i, r in enumerate(f.itertuples(index=False), start=4):
        ws.write_datetime(i, 0, r.d.to_pydatetime(), fmt["date"])
        ws.write(i, 1, r.btn, fmt["wrap"])
        ws.write(i, 2, r.what, fmt["text"])
        ws.write_string(i, 3, str(r.num), fmt["text"])
        ws.write(i, 4, r.contract or ("не найден" if r.num else "номер не указан"),
                 fmt["text"] if r.contract else fmt["flag"])
        ws.write_number(i, 5, num(r.amount), fmt["money"])
        ok = r.posted.startswith("разнесено")
        ws.write(i, 6, r.posted, fmt["ok"] if ok else fmt["flag"])
        ws.write(i, 7, r.adj_ids, fmt["text"])
    end = 4 + len(f)
    ws.write(end, 0, "Итого", fmt["totl"])
    ws.write_number(end, 5, num(f["amount"].sum()), fmt["tot"])
    ws.autofilter(3, 0, max(end - 1, 3), 7)

    # 2. По месяцам — финансовые по видам
    ws = wb.add_worksheet("По месяцам")
    mo = res["month"]
    cols = [("Месяц", 12)] + [(c, 18) for c in mo.columns]
    head(ws, "Финансовые удержания по месяцам", cols)
    for i, (m, r) in enumerate(mo.iterrows(), start=4):
        ws.write_datetime(i, 0, m.to_pydatetime(), fmt["month"])
        for j, c in enumerate(mo.columns, start=1):
            ws.write_number(i, j, num(r[c]), fmt["money"])

    # 3. Сводка — все виды удержаний
    ws = wb.add_worksheet("Все удержания")
    head(ws, "Все удержания WB по видам", (
        ("Обоснование WB (числа заменены на N)", 80), ("Финансовое", 12), ("Новое", 10),
        ("Впервые", 12), ("Последнее", 12), ("Строк", 10), ("Сумма, ₽", 16)))
    s = res["sum"]
    for i, r in enumerate(s.itertuples(index=False), start=4):
        ws.write(i, 0, r.kind_txt, fmt["wrap"])
        ws.write(i, 1, "да" if r.fin else "", fmt["flag"] if r.fin else fmt["text"])
        ws.write(i, 2, "новое" if r.new else "", fmt["flag"] if r.new else fmt["text"])
        ws.write_datetime(i, 3, r.first.to_pydatetime(), fmt["date"])
        ws.write_datetime(i, 4, r.last.to_pydatetime(), fmt["date"])
        ws.write_number(i, 5, int(r.n), fmt["text"])
        ws.write_number(i, 6, num(r.amount), fmt["money"])
    ws.autofilter(3, 0, max(3 + len(s), 3), 6)

    # 4. Как читать
    ws = wb.add_worksheet("Как читать")
    ws.set_column(0, 0, 22)
    ws.set_column(1, 1, 110)
    ws.write(0, 0, "Как читать", fmt["title"])
    notes = [
        ("Источник", "Еженедельные отчёты WB о реализации, колонка «Удержания» и её обоснование. "
                     "Это те же данные, что в личном кабинете WB, — смотреть там не нужно."),
        ("Финансовые", "Займы, кредиты, проценты, овердрафт, «перевод на баланс заёмщика». Это не "
                       "расход WB: тело гасит долг по договору займа, проценты и комиссии — "
                       "финансовые расходы. В манпаке такие удержания в расходы WB не попадают."),
        ("Вид", "Тело / Проценты — WB указал сам. «Тело и проценты вместе» — WB не разделил, "
                "делить по графику платежей из договора."),
        ("Договор у нас", "Найден по номеру из обоснования. «Не найден» — номера нет в карточках "
                          "договоров: завести договор или поправить номер. «Номер не указан» — "
                          "WB не написал номер, договор определить по датам и сумме."),
        ("Новое", f"Вид удержания впервые появился за последние {NEW_DAYS} дней — проверить, что "
                  "это и куда относится."),
        ("Что делать", "По финансовому удержанию — корректировка GL (Главная книга → "
                       "Корректировки GL): Дт счёт займа или 630000 с договором, Кт 610000 / "
                       "540101. Галочка «Отразить в Cash Flow» переносит сумму из 122501 в "
                       "статью финансовой деятельности."),
        ("Разнесено", "Сверка с корректировками GL, у которых Кт статья 540101: сумма за дату "
                      "отчёта WB, иначе за месяц целиком. «Частично» — корректировок меньше, "
                      "чем удержаний. Номера корректировок — в соседней колонке."),
    ]
    for i, (a, b) in enumerate(notes, start=2):
        ws.write(i, 0, a, fmt["lbl"])
        ws.write(i, 1, b, fmt["wrap"])
        ws.set_row(i, 36)
    wb.close()
    return buf.getvalue()


def build_wb_deductions_workbook(report_date: date) -> tuple[bytes, str]:
    from conns import get_duckdb_conn_with_opt
    with get_duckdb_conn_with_opt(ro=True) as con:
        res = build(report_date, con)
    return to_excel(res, report_date), f"Удержания WB {report_date:%Y%m%d}.xlsx"
