def build_wb_payouts(ws, receipts, withdrawn_total, report_date, as_of=None):
    """Лист «Поступления от WB»: зачисления от площадки на расчётный счёт.

    receipts — строки поступлений (дата, сумма, контрагент) из витрины
    движения денежных средств. Ничего не сопоставляется и не достраивается:
    на листе только то, что реально прошло по расчётному счёту.
    """
    as_of = as_of or report_date

    sheet_setup(ws, landscape=False)
    ncols = 6

    title_band(
        ws,
        "ПОСТУПЛЕНИЯ ОТ МАРКЕТПЛЕЙСА",
        "Зачисления от площадки на расчётный счёт: даты и суммы",
        ncols,
        extra="Российский рубль (RUB) · нарастающим итогом за всё время "
              "работы с площадкой по %s · месяцы раскрываются кнопкой «+» "
              "слева" % as_of.strftime("%d.%m.%Y"),
    )

    for i, w in enumerate([3, 34, 22, 40, 22, 4], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    f_section = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_hdr = Font(name=FONT, size=9, bold=True, color="FFFFFF")
    f_label = Font(name=FONT, size=10, color=TEXT)
    f_label_b = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_month = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_date = Font(name=FONT, size=9, color=TEXT_2)
    f_income = Font(name=FONT, size=9, color=INCOME)
    f_income_b = Font(name=FONT, size=10, bold=True, color=INCOME)
    f_bold_num = Font(name=FONT, size=10, bold=True, color=TEXT)
    f_note = Font(name=FONT, size=8, color=MUTED)

    def section(r, text):
        write(ws, r, 2, text, font=f_section, align="left", border=B_SECTION)
        for cc in range(3, ncols + 1):
            ws.cell(row=r, column=cc).border = B_SECTION
        ws.row_dimensions[r].height = 18
        return r + 1

    total_in = round(sum(x["amount"] for x in receipts), 2)

    # ------------------------------------------------------------- сводка
    r = 7
    r = section(r, "СВОДКА")

    summary = [
        ("Поступило на расчётный счёт, всего", total_in, f_income_b,
         "Зачисления от площадки за всё время работы, %d %s"
         % (len(receipts),
            "поступление" if len(receipts) == 1 else "поступлений")),
        ("Списано с баланса WB, всего", withdrawn_total, f_label_b,
         "Та же строка «Выведено средств, всего» на листе «Остатки ДС»"),
        ("Разница", round(withdrawn_total - total_in, 2), f_bold_num,
         "Списано площадкой, но на счёт ещё не зачислено — деньги в пути"),
    ]
    first_sum_row = r
    for lbl, value, fnt, hint in summary:
        write(ws, r, 2, lbl, font=f_label, border=B_BOTTOM,
              align="left", indent=1)
        write(ws, r, 3, value, font=fnt, fmt=FMT_MONEY,
              border=B_BOTTOM, align="right")
        write(ws, r, 4, hint, font=f_note, border=B_BOTTOM, align="left")
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=ncols)
        for cc in range(5, ncols + 1):
            ws.cell(row=r, column=cc).border = B_BOTTOM
        ws.row_dimensions[r].height = 17
        r += 1

    r += 1

    # ------------------------------------------ расшифровка по поступлениям
    r = section(r, "РАСШИФРОВКА ПО ДАТАМ ЗАЧИСЛЕНИЯ")

    headers = [
        (2, "Дата зачисления на счёт", "left"),
        (3, "Сумма поступления", "right"),
        (4, "Плательщик", "left"),
    ]
    for col, text, align in headers:
        write(ws, r, col, text, font=f_hdr, fillc=NAVY, align=align,
              indent=1 if align == "left" else 0, wrap=True)
    for cc in (5, ncols):
        ws.cell(row=r, column=cc).fill = fill(NAVY)
    ws.row_dimensions[r].height = 22
    hdr_row = r
    r += 1

    months = OrderedDict()
    for x in sorted(receipts, key=lambda x: x["dt"]):
        months.setdefault((x["dt"].year, x["dt"].month), []).append(x)

    month_rows = []
    for (year, month), group in months.items():
        month_row = r
        r += 1
        first_detail = r

        for x in group:
            write(ws, r, 2, x["dt"], font=f_date, fmt=FMT_DATE,
                  border=B_BOTTOM, align="left", indent=1)
            write(ws, r, 3, x["amount"], font=f_income, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            write(ws, r, 4, x["cp_name"] or "Маркетплейс", font=f_date,
                  border=B_BOTTOM, align="left", indent=1)
            for cc in (5, ncols):
                ws.cell(row=r, column=cc).border = B_BOTTOM
            ws.row_dimensions[r].outlineLevel = 1
            ws.row_dimensions[r].hidden = True
            ws.row_dimensions[r].height = 16
            r += 1

        last_detail = r - 1
        write(ws, month_row, 2, "%s %d" % (MONTHS_RU[month - 1], year),
              font=f_month, fillc=SURFACE_2, border=B_BOTTOM_STRONG,
              align="left", indent=1)
        write(ws, month_row, 3, "=SUM(C%d:C%d)" % (first_detail, last_detail),
              font=f_income_b, fmt=FMT_MONEY, fillc=SURFACE_2,
              border=B_BOTTOM_STRONG, align="right")
        write(ws, month_row, 4, "поступлений: %d" % len(group), font=f_note,
              fillc=SURFACE_2, border=B_BOTTOM_STRONG, align="left", indent=1)
        for cc in (5, ncols):
            ws.cell(row=month_row, column=cc).fill = fill(SURFACE_2)
            ws.cell(row=month_row, column=cc).border = B_BOTTOM_STRONG
        ws.row_dimensions[month_row].height = 18
        month_rows.append(month_row)

    # итог — сумма только строк месяцев: складывать диапазон нельзя,
    # внутри него лежат и месячные итоги, и сами поступления
    write(ws, r, 2, "ИТОГО ЗА ВСЁ ВРЕМЯ", font=f_label_b, fillc=TOTAL_ROW,
          border=B_TOTAL, align="left", indent=1)
    formula = ("=" + "+".join("C%d" % rr for rr in month_rows)
               if month_rows else 0)
    write(ws, r, 3, formula, font=f_income_b, fmt=FMT_MONEY, fillc=TOTAL_ROW,
          border=B_TOTAL, align="right")
    write(ws, r, 4, "поступлений всего: %d" % len(receipts), font=f_note,
          fillc=TOTAL_ROW, border=B_TOTAL, align="left", indent=1)
    for cc in (5, ncols):
        ws.cell(row=r, column=cc).fill = fill(TOTAL_ROW)
        ws.cell(row=r, column=cc).border = B_TOTAL
    ws.row_dimensions[r].height = 20
    total_row = r
    r += 2

    # сводка ссылается на итог расшифровки — цифры не разъезжаются
    ws.cell(row=first_sum_row, column=3).value = "=C%d" % total_row

    note = (
        "Что на листе. Каждая строка — зачисление от маркетплейса на "
        "расчётный счёт: дата, сумма и плательщик, всё по данным учёта. "
        "Месяцы свёрнуты, в строке месяца — сумма за месяц и количество "
        "зачислений; раскрываются кнопкой «+» слева.\n"
        "Почему итог меньше, чем «Выведено средств, всего» на листе "
        "«Остатки ДС». Между списанием с баланса площадки и зачислением на "
        "счёт проходит один-три рабочих дня, поэтому на отчётную дату часть "
        "выведенного ещё не дошла. Эта разница показана в сводке и совпадает "
        "с деньгами в пути."
    )
    write(ws, r, 2, note, font=f_note, align="left", wrap=True, indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
    ws.row_dimensions[r].height = 58

    ws.freeze_panes = ws.cell(row=hdr_row + 1, column=1)
    ws.print_title_rows = "1:%d" % hdr_row
    ws.sheet_properties.outlinePr.summaryBelow = False
    return r
