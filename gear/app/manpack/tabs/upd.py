# gear/app/manpack/tabs/upd.py
"""Приходы (УПД): стоимость в бухгалтерской и управленческой оценке, разница."""
from __future__ import annotations

from datetime import date

from dash import html

from .. import data
from ..config import x_btn
from ..theme import card, col, empty, export_button, grid, kpi, money, month_title, note, num


def tables(me: date):
    """→ (по документам, по брендам, итоги) — и для экрана, и для Excel."""
    df = data.upd(data.month_start(me), me)
    if df.empty:
        return [], [], {}
    docs = df.groupby(["doc_id", "number", "d", "cp"]).agg(
        contract=("contract", "first"), qty=("upd_qty", "sum"), buh=("buh", "sum"),
        man=("man", "sum"), no_man=("no_man", "sum"), lines=("upd_qty", "size")).reset_index()
    docs["diff"] = docs["man"] - docs["buh"]
    docs["diff_pct"] = docs["diff"] / docs["buh"].where(docs["buh"] != 0) * 100
    docs = docs.sort_values(["d", "number"], ascending=[False, True])
    brands = df.groupby("brand").agg(qty=("upd_qty", "sum"), buh=("buh", "sum"),
                                     man=("man", "sum")).reset_index()
    brands["diff"] = brands["man"] - brands["buh"]
    brands["diff_pct"] = brands["diff"] / brands["buh"].where(brands["buh"] != 0) * 100
    brands["buh_unit"] = brands["buh"] / brands["qty"].where(brands["qty"] != 0)
    brands["man_unit"] = brands["man"] / brands["qty"].where(brands["qty"] != 0)
    brands = brands.sort_values("buh", ascending=False)
    tot = {"qty": df["upd_qty"].sum(), "buh": df["buh"].sum(), "man": df["man"].sum(),
           "docs": docs["doc_id"].nunique(), "no_man": int(df["no_man"].sum())}
    return docs, brands, tot


def build(me: date):
    docs, brands, tot = tables(me)
    if not tot:
        return [empty(f"За {month_title(me).lower()} приходов (УПД) нет")]
    diff = tot["man"] - tot["buh"]
    doc_rows = [{
        "d": r.d.strftime("%d.%m.%Y"),
        "number": f"[{r.number}](/admin/cards/upddocument/{r.doc_id}/change/)",
        "cp": r.cp, "contract": r.contract or "", "qty": r.qty, "buh": r.buh, "man": r.man,
        "diff": r.diff, "diff_pct": None if r.diff_pct != r.diff_pct else r.diff_pct,
        "no_man": int(r.no_man)} for r in docs.itertuples()]
    return [
        html.Div(className="mp-kpis", children=[
            kpi("Приходов (УПД)", num(tot["docs"]), sub=f"{num(tot['qty'])} шт"),
            kpi("Стоимость, бух. учёт", money(tot["buh"]), sub="без НДС, по УПД"),
            kpi("Стоимость, упр. учёт", money(tot["man"]), sub="управленческая себестоимость"),
            kpi("Разница упр. − бух.", money(diff),
                sub=f"{diff / tot['buh'] * 100:+.1f}%".replace(".", ",") if tot["buh"] else "",
                tone="expense" if diff > 0 else "pos"),
        ]),
        note(f"В {num(tot['no_man'])} строках не задана управленческая себестоимость — "
             "по ним управленческая стоимость равна нулю, разница завышена.", "warn")
        if tot["no_man"] else None,
        card("Приходы по документам", grid("mp-upd-grid", doc_rows, [
            col("d", "Дата", width=110), col("number", "УПД", "link", width=170),
            col("cp", "Поставщик", minWidth=220), col("contract", "Договор", width=150),
            col("qty", "Кол-во, шт", "num", width=115),
            col("buh", "Бух. стоимость", "num", width=150),
            col("man", "Упр. стоимость", "num", width=150),
            col("diff", "Разница", "num", width=130),
            col("diff_pct", "Разница, %", "pct", width=115),
            col("no_man", "Строк без упр. с/с", "num", width=150)], height=560),
            subtitle=f"{month_title(me)} · ₽ без НДС",
            actions=export_button(x_btn("upd"), "Приходы, Excel")),
    ]
