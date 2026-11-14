"""Предварительный отчёт: ДДС и продажи Армении, консолидация ДДС с РФ в рублях.

Строится напрямую из операций и продаж, без главной книги. Только чтение.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Max, Min, Sum
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from corporate.models import BankAccount, Owners
from macro.models import CurrencyRate
from sales.models import RetailSale
from treasury.models import BankStatements, CfData

RU_GROUP = "Трендсеттер РФ"
HEAD_FILL = PatternFill("solid", fgColor="EEF4FB")
HEAD_FONT = Font(bold=True, color="2F7FB5")
TOTAL_FONT = Font(bold=True)
THIN = Side(style="thin", color="D5DDE6")
GRID = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
NUM = "#,##0;[Red]-#,##0"
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def mlabel(m: date) -> str:
    return f"{MONTHS[m.month - 1]} {m.year}"


class Rates:
    """Курс к рублю на дату или ближайшую предыдущую."""

    def __init__(self, currencies, start, finish):
        self.data = defaultdict(list)
        qs = (CurrencyRate.objects.filter(base_currency="RUB", currency__in=currencies,
                                          date__gte=date(start.year - 1, 1, 1), date__lte=finish)
              .order_by("currency", "date").values_list("currency", "date", "rate"))
        for cur, d, r in qs:
            self.data[cur].append((d, r))
        self.missing = set()

    def get(self, cur, d):
        if cur == "RUB":
            return Decimal(1)
        best = None
        for rd, r in self.data.get(cur, []):
            if rd > d:
                break
            best = r
        if best is None:
            self.missing.add(cur)
        return best


def sheet_header(ws, row, values, widths=None):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=row, column=i, value=v)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, GRID
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


def put(ws, row, values, bold=False, fmt=NUM):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=row, column=i, value=float(v) if isinstance(v, Decimal) else v)
        c.border = GRID
        if isinstance(v, (int, float, Decimal)):
            c.number_format = fmt
        if bold:
            c.font = TOTAL_FONT


def pivot_sheet(wb, title, note, rows, months, value_key):
    """rows: [{'item': str, 'month': date, value_key: Decimal}] → статья × месяц."""
    ws = wb.create_sheet(title)
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=12)
    ws.cell(row=2, column=1, value=note).font = Font(italic=True, color="7F8C99")
    table = defaultdict(lambda: defaultdict(Decimal))
    for r in rows:
        if r[value_key] is not None:
            table[r["item"]][r["month"]] += r[value_key]
    sheet_header(ws, 4, ["Статья ДДС"] + [mlabel(m) for m in months] + ["Итого"],
                 [48] + [14] * (len(months) + 1))
    row = 5
    totals = defaultdict(Decimal)
    for item in sorted(table, key=lambda s: (s.startswith("—"), s)):
        vals = [table[item][m] for m in months]
        for m, v in zip(months, vals):
            totals[m] += v
        put(ws, row, [item] + vals + [sum(vals)])
        row += 1
    tv = [totals[m] for m in months]
    put(ws, row, ["Итого чистый поток"] + tv + [sum(tv)], bold=True)
    ws.freeze_panes = "B5"
    return ws


class Command(BaseCommand):
    help = "Предварительный отчёт по Армении и консолидация ДДС в рублях (xlsx)"

    def add_arguments(self, parser):
        parser.add_argument("out")

    def handle(self, *args, out, **options):
        am_owners = list(Owners.objects.exclude(report_group=RU_GROUP).filter(bankaccount__isnull=False).distinct())
        if not am_owners:
            self.stdout.write("Армянских компаний с операциями нет")
            return
        am_ids = [o.id for o in am_owners]
        span = CfData.objects.filter(owner_id__in=am_ids).aggregate(a=Min("date"), b=Max("date"))
        start, finish = span["a"].replace(day=1), span["b"]
        months, m = [], start
        while m <= finish:
            months.append(m)
            m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)

        currencies = set(BankAccount.objects.values_list("currency", flat=True)) | {"AMD"}
        rates = Rates(currencies, start, finish)

        sql = """
            SELECT t.date, t.dt, t.cr, t.dt_eq, t.cr_eq, a.account, upper(coalesce(a.currency, 'RUB')),
                   o.id, o.name, i.code, i.name,
                   coalesce(c.title, ''), coalesce(t.cp_name_ru, cp.name, t.cp_bs_name, ''),
                   left(coalesce(t.temp_ru, t.temp, ''), 500)
            FROM treasury_cfdata t
            JOIN corporate_bankaccount a ON a.id = t.ba_id
            JOIN corporate_owners o ON o.id = a.corporate_id
            LEFT JOIN corporate_cfitems i ON i.id = t.cfitem_id
            LEFT JOIN contracts_contracts c ON c.id = t.contract_id
            LEFT JOIN counterparties_counterparty cp ON cp.id = t.cp_final_id
            WHERE t.date BETWEEN %s AND %s"""
        with connection.cursor() as cur:
            cur.execute(sql, [start, finish])
            data = cur.fetchall()
        self.stdout.write(f"Операций за период: {len(data)}")
        rows = []
        for (d, dt, cr, dt_eq, cr_eq, account, cur, oid, oname, icode, iname, contract, cp, temp) in data:
            is_am = oid in am_ids
            amount = (dt or 0) - (cr or 0)
            r_cur = rates.get(cur, d)
            rub = amount * r_cur if r_cur is not None else None
            amd = None
            if is_am:
                if cur == "AMD":
                    amd = amount
                elif dt_eq is not None or cr_eq is not None:
                    amd = (dt_eq or 0) - (cr_eq or 0)
                else:
                    r_amd = rates.get("AMD", d)
                    amd = rub / r_amd if rub is not None and r_amd else None
            item = f"{icode} {iname}" if icode else "— без статьи"
            rows.append({"company": "Армения" if is_am else "Трендсеттер РФ", "owner": oname,
                         "month": d.replace(day=1), "item": item, "account": account,
                         "currency": cur, "amount": amount, "amd": amd, "rub": rub,
                         "contract": contract, "cp": cp, "temp": temp, "date": d})
        am_rows = [r for r in rows if r["company"] == "Армения"]

        wb = Workbook()
        wb.remove(wb.active)

        pivot_sheet(wb, "ДДС Армения AMD", "Чистый поток по статьям, драмы. Валютные счета — по эквиваленту банка или курсу ЦБ РФ.",
                    am_rows, months, "amd")
        pivot_sheet(wb, "ДДС Армения ₽", "Чистый поток по статьям, рубли по курсу ЦБ РФ на дату операции.",
                    am_rows, months, "rub")
        pivot_sheet(wb, "ДДС Консолидация ₽", "Трендсеттер РФ + Армения, рубли по курсу ЦБ РФ на дату операции. "
                    "Внутригрупповые переводы не исключены.", rows, months, "rub")

        # продажи
        ws = wb.create_sheet("Продажи Армения")
        ws.cell(row=1, column=1, value="Продажи Армении (розница, 1С)").font = Font(bold=True, size=12)
        ws.cell(row=2, column=1, value="Без НДС, драмы; рубли по среднему курсу месяца.").font = Font(italic=True, color="7F8C99")
        sheet_header(ws, 4, ["Месяц", "Выручка", "Возвраты", "Выручка нетто", "Себестоимость", "Валовая прибыль",
                             "Маржа, %", "Выручка нетто ₽", "Себестоимость ₽", "Валовая прибыль ₽"],
                     [12, 16, 16, 16, 16, 16, 10, 16, 16, 16])
        row = 5
        for m in months:
            qs = RetailSale.objects.filter(owner_id__in=am_ids, period__year=m.year, period__month=m.month)
            s = qs.filter(kind="sale").aggregate(a=Sum("amount_novat"), c=Sum("cost_total"))
            r = qs.exclude(kind="sale").aggregate(a=Sum("amount_novat"), c=Sum("cost_total"))
            sale, ret = s["a"] or Decimal(0), r["a"] or Decimal(0)
            cost = (s["c"] or Decimal(0)) - (r["c"] or Decimal(0))
            net = sale - ret
            gp = net - cost
            mr = [x for d, x in rates.data.get("AMD", []) if d.year == m.year and d.month == m.month]
            avg = sum(mr) / len(mr) if mr else None
            rub = [v * avg if avg else None for v in (net, cost, gp)]
            put(ws, row, [mlabel(m), sale, ret, net, cost, gp, None] + rub)
            if net:
                c = ws.cell(row=row, column=7, value=float(gp / net))
                c.number_format = "0.0%"
            row += 1
        ws.freeze_panes = "B5"

        # остатки
        ws = wb.create_sheet("Остатки Армения")
        ws.cell(row=1, column=1, value="Остатки на счетах Армении на конец месяца (по выпискам)").font = Font(bold=True, size=12)
        sheet_header(ws, 3, ["Банк", "Счёт", "Валюта"] + [mlabel(m) for m in months], [22, 22, 8] + [16] * len(months))
        row = 4
        stmts = defaultdict(list)
        for ba_id, fin, eb in (BankStatements.objects.filter(ba__corporate_id__in=am_ids)
                               .order_by("finish").values_list("ba_id", "finish", "eb")):
            stmts[ba_id].append((fin, eb))
        for ba in BankAccount.objects.filter(corporate_id__in=am_ids).select_related("bank").order_by("bank__name", "currency", "account"):
            vals = []
            for m in months:
                nxt = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
                last = [eb for fin, eb in stmts[ba.id] if fin < nxt]
                vals.append(last[-1] if last else None)
            put(ws, row, [ba.bank.name if ba.bank else "", ba.account, ba.currency] + vals, fmt="#,##0.00")
            row += 1
        ws.freeze_panes = "D4"

        # данные для сводных
        ws = wb.create_sheet("Данные ДДС")
        cols = ["Компания", "Собственник", "Месяц", "Дата", "Статья ДДС", "Счёт", "Валюта", "Сумма в валюте",
                "Сумма AMD", "Сумма ₽", "Договор", "Контрагент", "Назначение"]
        sheet_header(ws, 1, cols, [16, 30, 10, 11, 40, 20, 8, 16, 16, 16, 30, 30, 60])
        for i, r in enumerate(sorted(rows, key=lambda x: (x["company"], x["date"])), 2):
            vals = [r["company"], r["owner"], mlabel(r["month"]), r["date"], r["item"], r["account"], r["currency"],
                    r["amount"], r["amd"], r["rub"], r["contract"], r["cp"], r["temp"][:500]]
            for j, v in enumerate(vals, 1):
                c = ws.cell(row=i, column=j, value=float(v) if isinstance(v, Decimal) else v)
                if j == 4:
                    c.number_format = "DD.MM.YYYY"
                elif j in (8, 9, 10):
                    c.number_format = "#,##0.00"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows) + 1}"
        ws.freeze_panes = "A2"

        wb.save(out)
        miss = f"; нет курсов: {', '.join(sorted(rates.missing))}" if rates.missing else ""
        no_item = sum(1 for r in am_rows if r["item"] == "— без статьи")
        self.stdout.write(f"Отчёт → {out} (месяцев: {len(months)}, операций Армении: {len(am_rows)}, "
                          f"без статьи: {no_item}{miss})")
