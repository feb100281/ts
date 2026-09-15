def build_wb_payouts(ws, pairs, orphans, report_date, as_of=None):
    """Лист «Выводы с баланса WB»: когда списано у площадки и когда пришло."""
    as_of = as_of or report_date

    sheet_setup(ws, landscape=False)
    ncols = 6

    title_band(
        ws,
        "ПОСТУПЛЕНИЯ ОТ МАРКЕТПЛЕЙСА",
        "Какой датой деньги списались с баланса WB и какой пришли на счёт",
        ncols,
        extra="Российский рубль (RUB) · нарастающим итогом за всё время "
              "работы с площадкой по %s · месяцы раскрываются кнопкой «+» "
              "слева" % as_of.strftime("%d.%m.%Y"),
    )

    for i, w in enumerate([3, 32, 22, 28, 34, 4], start=1):
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

    total = round(sum(p["out_amount"] for p in pairs), 2)
    received = round(sum(p["out_amount"] for p in pairs
                         if p["in_dt"] is not None), 2)
    in_transit = [p for p in pairs if p["in_dt"] is None]

    # ------------------------------------------------------------- сводка
    r = 7
    r = section(r, "СВОДКА")

    summary = [
        ("Поступления от площадки, всего", total, f_income_b,
         "Списано с баланса WB за всё время работы"),
        ("Зачислено на расчётный счёт", received, f_bold_num,
         "Выводы, для которых найдено поступление на счёт"),
        ("Ещё в пути", round(total - received, 2), f_label_b,
         "Списано с баланса WB, но на счёт пока не зачислено: %d %s"
         % (len(in_transit),
            "поступление" if len(in_transit) == 1 else "поступлений")),
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
    r = section(r, "РАСШИФРОВКА ПО КАЖДОМУ ПОСТУПЛЕНИЮ")

    headers = [
        (2, "Дата списания с баланса WB", "left"),
        (3, "Сумма поступления", "right"),
        (4, "Дата поступления на счёт", "left"),
        (5, "Статус", "left"),
    ]
    for col, text, align in headers:
        write(ws, r, col, text, font=f_hdr, fillc=NAVY, align=align,
              indent=1 if align == "left" else 0, wrap=True)
    ws.cell(row=r, column=ncols).fill = fill(NAVY)
    ws.row_dimensions[r].height = 24
    hdr_row = r
    r += 1

    months = OrderedDict()
    for p in pairs:
        months.setdefault((p["out_dt"].year, p["out_dt"].month), []).append(p)

    month_rows = []
    for (year, month), group in months.items():
        month_row = r
        r += 1
        first_detail = r

        for p in group:
            arrived = p["in_dt"] is not None
            write(ws, r, 2, p["out_dt"], font=f_date, fmt=FMT_DATE,
                  border=B_BOTTOM, align="left", indent=1)
            write(ws, r, 3, p["out_amount"], font=f_income, fmt=FMT_MONEY,
                  border=B_BOTTOM, align="right")
            write(ws, r, 4, p["in_dt"], font=f_date, fmt=FMT_DATE,
                  border=B_BOTTOM, align="left", indent=1)
            label = "Зачислено" if arrived else "В пути, ещё не зачислено"
            if arrived and p["cp_name"]:
                label += " · " + p["cp_name"]
            write(ws, r, 5, label, font=f_date, border=B_BOTTOM,
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
              font=f_income_b, fmt=FMT_MONEY, fillc=SURFACE_2,
              border=B_BOTTOM_STRONG, align="right")
        write(ws, month_row, 4, None, fillc=SURFACE_2, border=B_BOTTOM_STRONG)
        write(ws, month_row, 5, "поступлений: %d" % len(group), font=f_note,
              fillc=SURFACE_2, border=B_BOTTOM_STRONG, align="left", indent=1)
        ws.cell(row=month_row, column=ncols).fill = fill(SURFACE_2)
        ws.cell(row=month_row, column=ncols).border = B_BOTTOM_STRONG
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
    for cc in (4, ncols):
        ws.cell(row=r, column=cc).fill = fill(TOTAL_ROW)
        ws.cell(row=r, column=cc).border = B_TOTAL
    write(ws, r, 5, "поступлений всего: %d" % len(pairs), font=f_note,
          fillc=TOTAL_ROW, border=B_TOTAL, align="left", indent=1)
    ws.row_dimensions[r].height = 20
    total_row = r
    r += 2

    # сводка ссылается на итог расшифровки — цифры не разъезжаются
    ws.cell(row=first_sum_row, column=3).value = "=C%d" % total_row

    note = (
        "Как читать лист. Строка — один вывод средств с баланса "
        "маркетплейса: дата, когда площадка списала деньги со своего "
        "баланса, сумма и дата, когда они фактически пришли на расчётный "
        "счёт. Месяцы свёрнуты, в строке месяца — сумма и количество "
        "поступлений; раскрываются кнопкой «+» слева.\n"
        "Задержка зачисления — норма: между списанием у площадки и "
        "поступлением на счёт проходит один-три рабочих дня. Строки без "
        "даты поступления — это и есть деньги в пути на отчётную дату, "
        "та же сумма показана на листе «Остатки ДС»."
    )
    write(ws, r, 2, note, font=f_note, align="left", wrap=True, indent=1)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=ncols)
    ws.row_dimensions[r].height = 58

    ws.freeze_panes = ws.cell(row=hdr_row + 1, column=1)
    ws.print_title_rows = "1:%d" % hdr_row
    ws.sheet_properties.outlinePr.summaryBelow = False
    return r
