# gear/app/manpack/callbacks.py
from __future__ import annotations

import logging
import traceback
from datetime import date

import pandas as pd
from dash import Input, Output, State, dcc, html, no_update

from . import data, excel
from .config import (PL_CP_RESULT_ID, PL_ITEM_ID, BK_DATE_ID, BK_RESULT_ID, FC_BASE_ID, FC_CONV_ID, FC_FIX_ID, FC_KMD_ID,
                     FC_RESULT_ID, FC_REV_ID, FX_CUR_ID, FX_RESULT_ID, METHOD_BTN_ID,
                     METHOD_MODAL_ID, CF_BANK_ID, CF_CONTRACT_ID, CF_CP_ID, CF_DIR_ID, CF_GROUP_ID,
                     CF_ITEM_ID, CF_PERIOD_ID, CF_RESULT_ID, CONTENT_ID, CT_FILES_ID,
                     CT_RESULT_ID, CT_SEARCH_ID, CT_TYPE_ID, FX_CURRENCIES, MONTH_ID,
                     PACK_BTN_ID, PACK_DL_ID, PACK_STATUS_ID, TAB_ID, x_btn, x_dl)
from .tabs import banks, cash, contracts, forecast, fx, loans, overview, pl, upd
from .theme import fmt_date, month_title, note

log = logging.getLogger(__name__)
BUILDERS = {"overview": overview.build, "pl": pl.build, "cash": cash.build,
            "banks": banks.build, "loans": loans.build, "contracts": contracts.build,
            "upd": upd.build, "fx": fx.build, "forecast": forecast.build}


def _me(value) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return data.month_end(date.today())


def _error(e):
    log.exception("manpack")
    return html.Div(className="mp-error", children=[
        html.B("Не удалось показать раздел. "), html.Span(str(e)),
        html.Pre(traceback.format_exc()[-1500:]),
    ])


def _send(content: bytes, name: str):
    return dcc.send_bytes(content, filename=name)


def register_manpack_callbacks(app):

    @app.callback(
        Output(CONTENT_ID, "children"),
        Input(TAB_ID, "value"),
        Input(MONTH_ID, "value"),
    )
    def render(tab, month):
        import time
        t0 = time.time()
        try:
            return BUILDERS.get(tab, overview.build)(_me(month))
        except Exception as e:
            return _error(e)
        finally:
            print(f"[manpack] вкладка {tab}: {time.time() - t0:.1f} c", flush=True)

    @app.callback(
        Output(CF_RESULT_ID, "children"),
        Input(CF_PERIOD_ID, "value"), Input(CF_CP_ID, "value"),
        Input(CF_CONTRACT_ID, "value"), Input(CF_ITEM_ID, "value"),
        Input(CF_BANK_ID, "value"), Input(CF_DIR_ID, "value"), Input(CF_GROUP_ID, "value"),
    )
    def cf_update(period, cps, cts, items, bks, direction, group):
        try:
            return cash.result(period, cps, cts, items, bks, direction, group)
        except Exception as e:
            return _error(e)

    @app.callback(
        Output(CT_RESULT_ID, "children"),
        Input(CT_SEARCH_ID, "value"), Input(CT_TYPE_ID, "value"),
        Input(CT_FILES_ID, "checked"),
    )
    def ct_update(search, title, only_files):
        try:
            return contracts.result(search, title, only_files)
        except Exception as e:
            return _error(e)

    @app.callback(Output(PL_CP_RESULT_ID, "children"), Input(PL_ITEM_ID, "value"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def pl_cp_update(value, month):
        try:
            return pl.counterparties(_me(month), value)
        except Exception as e:
            return _error(e)

    @app.callback(Output(BK_RESULT_ID, "children"), Input(BK_DATE_ID, "value"),
                  State(MONTH_ID, "value"))
    def bk_update(value, month):
        try:
            return banks.result(banks.as_date(value, _me(month)))
        except Exception as e:
            return _error(e)

    @app.callback(Output(FX_RESULT_ID, "children"), Input(FX_CUR_ID, "value"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def fx_update(currencies, month):
        try:
            return fx.chart(_me(month), currencies or [])
        except Exception as e:
            return _error(e)

    @app.callback(
        Output(FC_RESULT_ID, "children"),
        Input(FC_BASE_ID, "value"), Input(FC_REV_ID, "value"), Input(FC_KMD_ID, "value"),
        Input(FC_FIX_ID, "value"), Input(FC_CONV_ID, "checked"), State(MONTH_ID, "value"))
    def fc_update(mode, rev, kmd, fix, ex_conv, month):
        def f(v):
            try:
                return float(v or 0)
            except (TypeError, ValueError):
                return 0.0
        try:
            return forecast.result(_me(month), mode, f(rev), f(kmd), f(fix), bool(ex_conv))
        except Exception as e:
            return _error(e)

    @app.callback(Output(METHOD_MODAL_ID, "opened"), Input(METHOD_BTN_ID, "n_clicks"),
                  prevent_initial_call=True)
    def open_method(n):
        return bool(n)

    # ------------------------------------------------------------ выгрузки
    @app.callback(
        Output(PACK_DL_ID, "data"), Output(PACK_STATUS_ID, "children"),
        Input(PACK_BTN_ID, "n_clicks"), State(MONTH_ID, "value"),
        prevent_initial_call=True,
    )
    def dl_pack(n, month):
        if not n:
            return no_update, no_update
        try:
            me = _me(month)
            rd = min(me, data.pl_bundle()["report_date"])
            content, name = excel.management_pack(rd)
            return _send(content, name), note(f"Мэн пак на {fmt_date(rd)} сформирован.", "good")
        except Exception as e:
            return no_update, note(f"Не удалось сформировать мэн пак: {e}", "bad")

    @app.callback(Output(x_dl("summary"), "data"), Input(x_btn("summary"), "n_clicks"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_summary(n, month):
        if not n:
            return no_update
        me = _me(month)
        s = data.month_summary(me)
        as_of = min(data.pl_bundle()["report_date"], me)
        return _send(excel.summary_xlsx(s, me, as_of), f"vyvody_{me:%Y_%m}.xlsx")

    @app.callback(Output(x_dl("pl"), "data"), Input(x_btn("pl"), "n_clicks"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_pl(n, month):
        if not n:
            return no_update
        me = _me(month)
        ms, hdr, key, detail = pl.table_data(me)
        cols = ["Показатель"] + hdr

        def rows(src):
            out, fmts = [], {}
            for label, kind, _style, vals in src:
                if kind == "head":
                    out.append([label.upper()] + [None] * len(hdr))
                    continue
                if kind == "pct":
                    fmts[len(out)] = "FMT_PCT"
                out.append([label] + list(vals))
            return out, fmts
        k_rows, k_f = rows(key)
        d_rows, d_f = rows(detail)
        sub = f"{me.year} год по {month_title(me).lower()} · ₽ без НДС · расходы в скобках"
        return _send(excel.tables_xlsx([
            ("Ключевые показатели", "P&L: ключевые показатели", sub, cols, k_rows,
             {"row_formats": k_f, "totals": False}),
            ("P&L по статьям", "P&L по статьям", sub, cols, d_rows,
             {"row_formats": d_f, "totals": False}),
        ]), f"pl_{me:%Y_%m}.xlsx")

    @app.callback(
        Output(x_dl("cash"), "data"), Input(x_btn("cash"), "n_clicks"),
        State(CF_PERIOD_ID, "value"), State(CF_CP_ID, "value"), State(CF_CONTRACT_ID, "value"),
        State(CF_ITEM_ID, "value"), State(CF_BANK_ID, "value"), State(CF_DIR_ID, "value"),
        State(CF_GROUP_ID, "value"), prevent_initial_call=True)
    def dl_cash(n, period, cps, cts, items, bks, direction, group):
        if not n:
            return no_update
        df, start, end = cash.filtered(period, cps, cts, items, bks, direction)
        if df is None or df.empty:
            return no_update
        names = {"ops": "Операции", "cp": "По контрагентам", "contract": "По договорам",
                 "item": "По статьям", "subitem": "По подстатьям", "bank": "По счетам",
                 "day": "По дням", "month": "По месяцам"}
        main = group or "ops"
        tables = []
        for g in [main] + [x for x in ("item", "cp") if x != main]:
            cols, rows = cash.grouped(df, g)
            tables.append((names[g], "Движение денежных средств",
                           f"{start:%d.%m.%Y} – {end:%d.%m.%Y} · {dict(cash.GROUPS)[g]}",
                           cols, rows))
        return _send(excel.tables_xlsx(tables), f"dds_{start:%Y%m%d}-{end:%Y%m%d}.xlsx")

    @app.callback(Output(x_dl("banks"), "data"), Input(x_btn("banks"), "n_clicks"),
                  State(BK_DATE_ID, "value"), State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_banks(n, value, month):
        if not n:
            return no_update
        s = banks.snapshot(banks.as_date(value, _me(month)))
        acc = [[a["name"].strip(), a["cur"], a["status"], a["balance"]]
               for a in s["accounts"] + banks.reference_rows(s)]
        cf = [[f"{m:%m.%Y}", op, net, cl] for m, op, net, cl, _ in s["cf"]]
        return _send(excel.tables_xlsx([
            ("Остатки ДС", "Остатки денежных средств", f"на {fmt_date(s['as_of'])}",
             ["Счёт", "Валюта", "Статус", "Остаток"], acc, {"totals": False}),
            ("Cash Flow по месяцам", "Остаток на начало и конец месяца", "по Cash Flow, ₽",
             ["Месяц", "На начало, ₽", "Сальдо, ₽", "На конец, ₽"], cf, {"totals": False}),
        ]), f"ostatki_ds_{s['as_of']:%Y%m%d}.xlsx")

    @app.callback(Output(x_dl("wb"), "data"), Input(x_btn("wb"), "n_clicks"),
                  State(BK_DATE_ID, "value"), State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_wb(n, value, month):
        if not n:
            return no_update
        as_of = banks.as_date(value, _me(month))
        rec, transit, _avg, _last = banks.payouts(as_of)
        rows = [[x["in_dt"], x["out_amount"]] for x in rec]
        t_rows = [[x["out_dt"], x["out_amount"]] for x in transit]
        return _send(excel.tables_xlsx([
            ("Поступления от WB", "Поступления от WB на расчётный счёт",
             f"{month_title(as_of)} по {fmt_date(as_of)}",
             ["Дата зачисления", "Сумма, ₽"], rows),
            ("Деньги в пути", "Деньги в пути", "выведены из кабинета WB, на счёт не пришли",
             ["Дата вывода", "Сумма, ₽"], t_rows),
        ]), f"postupleniya_wb_{as_of:%Y%m%d}.xlsx")

    @app.callback(Output(x_dl("ct_paid"), "data"), Input(x_btn("ct_paid"), "n_clicks"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_ct_paid(n, month):
        if not n:
            return no_update
        me = _me(month)
        tables = contracts.paid_tables(me)
        if not tables:
            return no_update
        return _send(excel.tables_xlsx(tables), f"dogovory_platezhi_{me:%Y_%m}.xlsx")

    @app.callback(Output(x_dl("loans"), "data"), Input(x_btn("loans"), "n_clicks"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_loans(n, month):
        if not n:
            return no_update
        me = _me(month)
        rs = loans.rows(me)
        cols = ["Контрагент", "Сторона", "Договор", "Валюта", "Ставка, %", "Выдано / получено, ₽",
                "Погашено, ₽", "Основной долг, ₽", "Проценты к уплате, ₽", "Всего долг, ₽",
                "Срок погашения", "Файлов, шт"]
        rows = [[r["cp"], r["side"], r["contract"], r["cur"], r["rate"], r["drawdown"],
                 r["repaid"], r["principal"], r["interest"], r["debt"], r["due"], r["docs"]]
                for r in rs]
        return _send(excel.tables_xlsx([
            ("Займы и кредиты", "Займы и кредиты",
             f"задолженность на {fmt_date(min(me, date.today()))}", cols, rows)]),
            f"zaimy_{me:%Y_%m}.xlsx")

    @app.callback(Output(x_dl("contracts"), "data"), Input(x_btn("contracts"), "n_clicks"),
                  State(CT_SEARCH_ID, "value"), State(CT_TYPE_ID, "value"),
                  State(CT_FILES_ID, "checked"), prevent_initial_call=True)
    def dl_contracts(n, search, title, only_files):
        if not n:
            return no_update
        cols, rows = contracts.table(search, title, only_files)
        return _send(excel.tables_xlsx([
            ("Договоры", "Реестр договоров", "по условиям поиска", cols, rows,
             {"totals": False})]), "dogovory.xlsx")

    @app.callback(Output(x_dl("upd"), "data"), Input(x_btn("upd"), "n_clicks"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_upd(n, month):
        if not n:
            return no_update
        me = _me(month)
        docs, brands, tot = upd.tables(me)
        if not tot:
            return no_update
        nz = lambda v: None if v != v else v
        d_rows = [[r.d, r.number, r.cp, r.contract or "", r.qty, r.buh, r.man, r.diff,
                   nz(r.diff_pct), int(r.no_man)] for r in docs.itertuples()]
        sub = f"{month_title(me)} · ₽ без НДС"
        return _send(excel.tables_xlsx([
            ("Приходы", "Приходы (УПД)", sub,
             ["Дата", "УПД", "Поставщик", "Договор", "Кол-во, шт", "Бух. стоимость, ₽",
              "Упр. стоимость, ₽", "Разница, ₽", "Разница, %", "Строк без упр. с/с, шт"], d_rows),
        ]), f"prihody_{me:%Y_%m}.xlsx")

    @app.callback(Output(x_dl("fx"), "data"), Input(x_btn("fx"), "n_clicks"),
                  State(MONTH_ID, "value"), prevent_initial_call=True)
    def dl_fx(n, month):
        if not n:
            return no_update
        me = _me(month)
        st, df = fx.stats(me)
        if df.empty:
            return no_update
        pv = df.pivot_table(index="date", columns="currency", values="rate", aggfunc="last")
        pv = pv.reindex(columns=[c for c in FX_CURRENCIES if c in pv.columns]).reset_index()
        rate_cols = ["Дата"] + [f"Цена {c}" for c in pv.columns[1:]]
        rate_rows = [[r[0]] + [None if pd.isna(v) else float(v) for v in r[1:]]
                     for r in pv.itertuples(index=False)]
        s_rows = [[s["cur"], s["rate"], s["date"], s["m0"], s["m_ch"], s["y0"], s["y_ch"]]
                  for s in st]
        return _send(excel.tables_xlsx([
            ("Сводка", "Курсы валют", f"на конец периода: {month_title(me).lower()}",
             ["Валюта", "Цена, ₽", "Дата", "Цена на начало месяца", "Изменение за месяц, %",
              "Цена на начало года", "Изменение с начала года, %"], s_rows, {"totals": False}),
            ("Курсы по дням", "Курсы валют по дням", "рублей за единицу валюты",
             rate_cols, rate_rows, {"totals": False}),
        ]), f"kursy_{me:%Y_%m}.xlsx")
