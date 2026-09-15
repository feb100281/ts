# =============================================================================
#  07C. ЛИСТ «ВЫВОДЫ С БАЛАНСА WB»
#
#      Каждый вывод средств с баланса площадки сопоставлен с поступлением
#      на расчётный счёт: видно, какой датой деньги списались у WB и какой
#      фактически пришли. Разница между итогами и есть «деньги в пути».
#
#      Данные — витрина wb_payouts (sql/wb_payouts.txt): списания из
#      ежедневного баланса WB, поступления из движения денежных средств
#      по статье выручки от маркетплейса. Само сопоставление — здесь,
#      в match_wb_payouts: это алгоритм, а не витрина.
# =============================================================================

PAYOUTS_SHEET_NAME = "Выводы с баланса WB"

PAYOUT_MATCH_DAYS = 15      # окно поиска поступления после вывода
PAYOUT_MATCH_EPS = 1.0      # допуск по сумме, рублей

FMT_DATE = "DD.MM.YYYY"


def split_payouts(payout_rows):
    """Делит витрину wb_payouts на списания с баланса WB и поступления."""
    outs, ins = [], []
    for side, dt, amount, cp_name in payout_rows:
        dt = dt if isinstance(dt, date) else date.fromisoformat(str(dt))
        value = round(abs(float(amount or 0)), 2)
        if not value:
            continue
        row = {"dt": dt, "amount": value, "cp_name": (cp_name or "").strip()}
        (outs if side == "OUT" else ins).append(row)
    outs.sort(key=lambda x: x["dt"])
    ins.sort(key=lambda x: x["dt"])
    return outs, ins


def match_wb_payouts(outs, ins):
    """Сопоставляет вывод с баланса WB и поступление на расчётный счёт.

    Проход первый — по совпадению суммы: поступление ищется в окне
    PAYOUT_MATCH_DAYS дней после вывода, берётся самое раннее подходящее.
    Проход второй — остаток по порядку: деньги приходят в той же
    последовательности, в которой выводились.

    Возвращает (пары, поступления без вывода). Вид пары:
        exact   — сошлись по сумме;
        order   — сопоставлено по порядку, сумма не совпала;
        transit — вывод есть, поступления ещё нет (деньги в пути).
    """
    used = [False] * len(ins)
    pairs = []

    def take(i, out, kind):
        used[i] = True
        inc = ins[i]
        pairs.append({
            "out_dt": out["dt"], "out_amount": out["amount"],
            "in_dt": inc["dt"], "in_amount": inc["amount"],
            "cp_name": inc["cp_name"],
            "days": (inc["dt"] - out["dt"]).days,
            "kind": kind,
        })

    rest = []
    for out in outs:
        hit = None
        for i, inc in enumerate(ins):
            if inc["dt"] < out["dt"]:
                continue
            if (inc["dt"] - out["dt"]).days > PAYOUT_MATCH_DAYS:
                break
            if used[i]:
                continue
            if abs(inc["amount"] - out["amount"]) <= PAYOUT_MATCH_EPS:
                hit = i
                break
        if hit is None:
            rest.append(out)
        else:
            take(hit, out, "exact")

    for out in rest:
        hit = None
        for i, inc in enumerate(ins):
            if not used[i] and inc["dt"] >= out["dt"]:
                hit = i
                break
        if hit is None:
            pairs.append({
                "out_dt": out["dt"], "out_amount": out["amount"],
                "in_dt": None, "in_amount": 0.0, "cp_name": "",
                "days": None, "kind": "transit",
            })
        else:
            take(hit, out, "order")

    pairs.sort(key=lambda p: (p["out_dt"], p["in_dt"] or date.max))
    orphans = [ins[i] for i, flag in enumerate(used) if not flag]
    return pairs, orphans


def build_wb_payouts(ws, pairs, orphans, report_date, as_of=None):
    """Лист с расшифровкой выводов: дата списания → дата поступления."""
    as_of = as_of or report_date

    sheet_setup(ws, landscape=False)
    ncols = 8

    title_band(
        ws,
        "ВЫВОДЫ С БАЛАНСА МАРКЕТПЛЕЙСА",
        "Какой датой деньги списались с баланса WB и какой пришли на счёт",
        ncols,
        extra="Российский рубль (RUB) · нарастающим итогом за всё время "
              "работы с площадкой по %s · месяцы раскрываются кнопкой «+» "
              "слева" % as_of.strftime("%d.%m.%Y"),
    )

    for i, w in enumerate([3, 22, 18, 22, 18, 14, 34, 4], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    f_section = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_hdr = Font(name=FONT, size=9, bold=True, color="FFFFFF")
    f_label = Font(name=FONT, size=10, color=TEXT)
    f_label_b = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_month = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_date = Font(name=FONT, size=9, color=TEXT_2)
    f_income = Font(name=FONT, size=9, color=INCOME)
    f_expense = Font(name=FONT, size=9, color=EXPENSE)
    f_income_b = Font(name=FONT, size=10, bold=True, color=INCOME)
    f_expense_b = Font(name=FONT, size=10, bold=True, color=EXPENSE)
    f_bold_num = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_note = Font(name=FONT, size=8, color=MUTED)

    def section(r, text):
        write(ws, r, 2, text, font=f_section, align="left", border=B_SECTION)
        for cc in range(3, ncols + 1):
            ws.cell(row=r, column=cc).border = B_SECTION
        ws.row_dimensions[r].height = 18
        return r + 1

    total_out = round(sum(p["out_amount"] for p in pairs), 2)
    total_in = round(sum(p["in_amount"] for p in pairs), 2)
    transit = round(total_out - total_in, 2)
    in_transit = [p for p in pairs if p["kind"] == "transit"]
    delays = [p["days"] for p in pairs if p["days"] is not None]

    # ------------------------------------------------------------- сводка
    r = 7
    r = section(r, "СВОДКА")

    summary = [
        ("Выведено с баланса WB, всего", total_out, f_expense_b,
         "Списания с баланса площадки за всё время работы"),
        ("Поступило на расчётный счёт, всего", total_in, f_income_b,
         "Сопоставленные поступления от площадки"),
        ("Из них ещё в пути", transit, f_bold_num,
         "Выведено, но на счёт пока не зачислено: %d %s"
         % (len(in_transit), "вывод" if len(in_transit) == 1 else "выводов")),
        ("Средняя задержка зачисления, дней",
         round(sum(delays) / len(delays), 1) if delays else 0.0, f_label_b,
         "От даты списания с баланса WB до даты поступления на счёт"),
    ]
    first_sum_row = r
    for lbl, value, fnt, hint in summary:
        is_days = lbl.startswith("Средняя")
        write(ws, r, 2, lbl, font=f_label, border=B_BOTTOM,
              align="left", indent=1)
        write(ws, r, 3, value, font=fnt,
              fmt=FMT_PRICE if is_days else FMT_MONEY,
              border=B_BOTTOM, align="right")
        write(ws, r, 4, hint, font=f_note, border=B_BOTTOM, align="left")
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=ncols)
        for cc in range(5, ncols + 1):
            ws.cell(row=r, column=cc).border = B_BOTTOM
        ws.row_dimensions[r].height = 17
        r += 1

    r += 1

    # ------------------------------------------------- расшифровка по выводам
    r = section(r, "РАСШИФРОВКА ПО КАЖДОМУ ВЫВОДУ")

    headers = [
        (2, "Дата списания с WB", "left"),
        (3, "Сумма вывода", "right"),
        (4, "Дата поступления на счёт", "left"),
        (5, "Сумма поступления", "right"),
        (6, "Задержка, дней", "right"),
        (7, "Статус", "left"),
    ]
    for col, text, align in headers:
        write(ws, r, col, text, font=f_hdr, fillc=NAVY, align=align,
              indent=1 if align == "left" else 0, wrap=True)
    ws.cell(row=r, column=ncols).fill = fill(NAVY)
    ws.row_dimensions[r].height = 24
    hdr_row = r
    r += 1

    status_text = {
        "exact": "Получено",
        "order": "Получено, сумма отличается",
        "transit": "В пути, на счёт не зачислено",
    }

    months = OrderedDict()
    for p in pairs:
        months.setdefault((p["out_dt"].year, p["out_dt"].month), []).append(p)

    month_rows = []
    for (year, month), group in months.items():
        month_row = r
        r += 1
        first_detail = r

        for p in group:
            write(ws, r, 2, p["out_dt"], font=f_date, fmt=FMT_DATE,
                  border=B_BOTTOM, align="left", indent=1)
            write(ws, r, 3, p["out_amount"], font=f_expense, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            write(ws, r, 4, p["in_dt"], font=f_date, fmt=FMT_DATE,
                  border=B_BOTTOM, align="left", indent=1)
            write(ws, r, 5, p["in_amount"] or None, font=f_income,
                  fmt=FMT_MONEY, border=B_BOTTOM, align="right")
            write(ws, r, 6, p["days"], font=f_date, fmt=FMT_QTY,
                  border=B_BOTTOM, align="right")
            label = status_text[p["kind"]]
            if p["cp_name"]:
                label += " · " + p["cp_name"]
            write(ws, r, 7, label, font=f_date, border=B_BOTTOM,
                  align="left", indent=1)
            ws.cell(row=r, column=ncols).border = B_BOTTOM
            ws.row_dimensions[r].outlineLevel = 1
            ws.row_dimensions[r].hidden = True
            ws.row_dimensions[r].height = 16
            r += 1

        last_detail = r - 1
        write(ws, month_row, 2, "%s %d" % (MONTHS_RU[month - 1], year),
              font=f_month, fillc=SURFACE_2, border=B_BOTTOM_STRONG,
              align="left", indent=1)
        write(ws, month_row, 3, "=SUM(C%d:C%d)" % (first_detail, last_detail),
              font=f_expense_b, fmt=FMT_MONEY, fillc=SURFACE_2,
              border=B_BOTTOM_STRONG, align="right")
        write(ws, month_row, 4, None, fillc=SURFACE_2,
              border=B_BOTTOM_STRONG)
        write(ws, month_row, 5, "=SUM(E%d:E%d)" % (first_detail, last_detail),
              font=f_income_b, fmt=FMT_MONEY, fillc=SURFACE_2,
              border=B_BOTTOM_STRONG, align="right")
        write(ws, month_row, 6, None, fillc=SURFACE_2, border=B_BOTTOM_STRONG)
        write(ws, month_row, 7,
              "выводов: %d" % len(group), font=f_note, fillc=SURFACE_2,
              border=B_BOTTOM_STRONG, align="left", indent=1)
        ws.cell(row=month_row, column=ncols).fill = fill(SURFACE_2)
        ws.cell(row=month_row, column=ncols).border = B_BOTTOM_STRONG
        ws.row_dimensions[month_row].height = 18
        month_rows.append(month_row)

    # итог — сумма только строк месяцев, диапазон складывать нельзя:
    # внутри него лежат и месячные итоги, и сами выводы
    write(ws, r, 2, "ИТОГО ЗА ВСЁ ВРЕМЯ", font=f_label_b, fillc=TOTAL_ROW,
          border=B_TOTAL, align="left", indent=1)
    for col, fnt in ((3, f_expense_b), (5, f_income_b)):
        cl = get_column_letter(col)
        formula = ("=" + "+".join("%s%d" % (cl, rr) for rr in month_rows)
                   if month_rows else 0)
        write(ws, r, col, formula, font=fnt, fmt=FMT_MONEY, fillc=TOTAL_ROW,
              border=B_TOTAL, align="right")
    for cc in (4, 6, ncols):
        ws.cell(row=r, column=cc).fill = fill(TOTAL_ROW)
        ws.cell(row=r, column=cc).border = B_TOTAL
    write(ws, r, 7, "выводов всего: %d" % len(pairs), font=f_note,
          fillc=TOTAL_ROW, border=B_TOTAL, align="left", indent=1)
    ws.row_dimensions[r].height = 20
    total_row = r
    r += 2

    # сводка ссылается на итог расшифровки — цифры не разъезжаются
    ws.cell(row=first_sum_row, column=3).value = "=C%d" % total_row
    ws.cell(row=first_sum_row + 1, column=3).value = "=E%d" % total_row
    ws.cell(row=first_sum_row + 2, column=3).value = (
        "=C%d-E%d" % (total_row, total_row))

    # ------------------------------------------- поступления без вывода
    if orphans:
        r = section(r, "ПОСТУПЛЕНИЯ ОТ ПЛОЩАДКИ БЕЗ СООТВЕТСТВУЮЩЕГО ВЫВОДА")
        for inc in orphans:
            write(ws, r, 2, inc["dt"], font=f_date, fmt=FMT_DATE,
                  border=B_BOTTOM, align="left", indent=1)
            write(ws, r, 5, inc["amount"], font=f_income, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            write(ws, r, 7, inc["cp_name"] or "Маркетплейс", font=f_date,
                  border=B_BOTTOM, align="left", indent=1)
            for cc in (3, 4, 6, ncols):
                ws.cell(row=r, column=cc).border = B_BOTTOM
            ws.row_dimensions[r].height = 16
            r += 1
        r += 1

    note = (
        "Как читать лист. Левая пара колонок — списание с баланса "
        "маркетплейса, правая — фактическое зачисление на расчётный счёт. "
        "Пара строится так: сначала ищется поступление с той же суммой в "
        "пределах %d дней после вывода, оставшиеся выводы сопоставляются по "
        "порядку — деньги приходят в той же последовательности, в которой "
        "выводились. Строки со статусом «сумма отличается» стоит "
        "проверить руками: обычно это разбитый или объединённый платёж.\n"
        "Задержка зачисления — норма: между списанием у площадки и "
        "поступлением на счёт проходит один-три рабочих дня, и именно эта "
        "разница показана на листе «Остатки ДС» как деньги в пути. Поэтому "
        "итог «выведено» всегда больше итога «поступило» ровно на сумму "
        "невыясненных на отчётную дату выводов."
        % PAYOUT_MATCH_DAYS
    )
    write(ws, r, 2, note, font=f_note, align="left", wrap=True, indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
    ws.row_dimensions[r].height = 72

    ws.freeze_panes = ws.cell(row=hdr_row + 1, column=1)
    ws.print_title_rows = "1:%d" % hdr_row
    ws.sheet_properties.outlinePr.summaryBelow = False
    return r
