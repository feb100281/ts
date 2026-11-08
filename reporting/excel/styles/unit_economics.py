# reporting/excel/styles/unit_economics.py

from datetime import date, datetime

from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from reporting.excel.styles.theme import FILLS, FONTS, BORDERS, ALIGNMENTS, COLORS
from reporting.excel.styles.style_helpers import (
    clear_range,
    set_column_widths,
    set_row_heights,
    draw_sheet_header,
    draw_toc_button,
    draw_section_title,
    draw_table_header,
)

from reporting.excel.unit_economics_data import (
    ROW_ORDER,
    ROW_SALES_QTY,
    ROW_RETURNS_QTY,
    ROW_NET_QTY,
    ROW_AMOUNT_BEFORE_SPP,
    ROW_AMOUNT_BEFORE_SPP_VATLESS,
    ROW_AVG_PRICE_BEFORE_SPP,
    ROW_AVG_COGS,
    ROW_WB_COSTS,
    ROW_PROMO,
    ROW_OTHER_OVERHEADS,
    ROW_NET_PROFIT,
    ROW_GROSS_MARGIN,
    ROW_MARGIN_NO_PROMO,
    ROW_MARGIN_WITH_PROMO,
    ROW_NET_MARGIN,
    QTY_ROWS,
    MONEY_ROWS,
    PERCENT_ROWS,
    ESTIMATED_CASH_ROWS,
    FORMULA_ROWS,
)


LABEL_COL_WIDTH = 52
DATA_COL_WIDTH = 13

NOTE_FILL = PatternFill("solid", fgColor="FBF6E3")
NOTE_FONT = Font(name="Roboto", size=9, color=COLORS["text_gray"])
NOTE_TITLE_FONT = Font(name="Roboto", size=9, bold=True, color=COLORS["black"])

TOTAL_COL_FILL = PatternFill("solid", fgColor=COLORS["total_green"])
ESTIMATE_FONT = Font(name="Roboto", size=10, italic=True, color=COLORS["blue"])
ESTIMATE_FILL = PatternFill("solid", fgColor="EAF2FB")

THIN_GRAY = Side(style="thin", color=COLORS["border_gray"])

CASH_METHODOLOGY = "\n".join([
    "МЕТОД: ЦЕЛЕВОЙ ОБОРОТ (КЭШ, С ВОЗВРАТАМИ). Продажа и возврат учитываются как два "
    "отдельных события на свою фактическую дату: продажа — на дату продажи, возврат — "
    "на дату возврата. Прошлые периоды задним числом не пересчитываются. Строки 3, 6 и "
    "9–16 на листе — не готовые числа, а формулы Excel со ссылками на другие строки "
    "этого же столбца: можно кликнуть на ячейку и увидеть, из чего она получена. "
    "Порядок расчёта каждого показателя:",
    "",
    "1. Кол-во продаж, шт — количество единиц, реализованных за период. Источник — "
    "построчные данные WB по цене реализации (retail_price), дата операции — фактическая "
    "дата продажи.",
    "2. Кол-во возвратов, шт — количество единиц, возвращённых за период; отдельное "
    "событие на дату фактического возврата, независимо от того, когда товар был продан.",
    "3. Кол-во чистых продаж, шт = Кол-во продаж − Кол-во возвратов (формула).",
    "4. Продажи до СПП с НДС, ₽ — фактически поступившая касса за период по статье ДДС "
    "111000 «Выручка от продажи товаров» (та же сумма, что показана на листе CF), уже с "
    "НДС — берётся напрямую, без каких-либо досчётов, и совпадает с суммой на листе CF. "
    "ВАЖНО: эта строка НЕ совпадает со строкой «Выручка от основной деятельности» на "
    "листе PL — там начисление по дате бухгалтерской проводки (метод начисления), а "
    "здесь — фактическая касса (метод оплаты); небольшое расхождение между ними "
    "ожидаемо и не является ошибкой.",
    "5. Продажи до СПП без НДС, ₽ — единственный расчётный показатель во всём кэш-блоке "
    "(касса по ДДС не хранит НДС отдельно по операциям). Считается как пункт 4, "
    "умноженный на фактическое НДС-соотношение периода: (сумма после СПП без НДС) / "
    "(сумма после СПП с НДС) — это соотношение берётся из построчных данных WB (поле "
    "retail_amount, где НДС известен по каждой операции) этого же кэш-блока и того же "
    "месяца. Используется как знаменатель строк маржинальности (13–16) ниже.",
    "6. Средняя цена на ед. продаж до СПП с НДС, ₽ = Продажи до СПП с НДС (пункт 4) / "
    "Кол-во чистых продаж (пункт 3) (формула).",
    "7. Средняя цена на ед. продаж после СПП с НДС (цена для покупателя), ₽ — сумма, "
    "фактически уплаченная покупателем после применения скидки СПП (WB, поле "
    "retail_amount — отличается от retail_price, которое даёт цену ДО СПП), делённая "
    "на Кол-во чистых продаж.",
    "8. Средняя с/с на ед. продаж без НДС, ₽ — управленческая себестоимость по методу "
    "FIFO (списание товара в порядке поступления партий, привязано к конкретной продаже, "
    "а не к периоду и не к бухгалтерской проводке) — та же ставка на единицу, что и в "
    "блоке FIFO ниже, за тот же месяц. Взята намеренно одинаковой в обоих блоках: разница "
    "между методами — в том, ЧТО считать выручкой и КАК признавать возвраты, а не в "
    "себестоимости товара.",
    "9. Расходы ВБ без продвижения, ₽ — комплексный пул операционных расходов площадки: "
    "комиссия WB за продажу, логистика, хранение, приёмка, штрафы, удержания, программа "
    "лояльности и корректировки. Считается из сырых данных площадки (та же методология, "
    "что в daily_sales), а НЕ из бухгалтерского ГК — на счетах 1.4/1.5 отдельных статей "
    "по логистике/хранению/приёмке/штрафам/комиссии вообще нет, там только маркетинг, "
    "комиссия банка, аренда и подобное. Показано со знаком расхода (отрицательное число). "
    "Общая для обоих блоков — это расход периода, он не зависит от способа признания "
    "выручки.",
    "10. Продвижение, ₽ — счета бухгалтерского учёта 1.4 и 1.5, статьи с «WB» в названии "
    "группы или статьи, относящиеся к рекламе, продвижению или маркетингу. Показано со "
    "знаком расхода. Общая для обоих блоков.",
    "11. Прочие накладные расходы, ₽ — остаток счетов 1.4/1.5 (не про WB), плюс счёт 1.6 "
    "(прочие доходы/расходы), плюс счёт 1.7 (финансовые расходы). Используется только в "
    "чистой прибыли (пункт 12). Общая для обоих блоков.",
    "12. Чистая прибыль (управленческая), ₽ = Продажи до СПП без НДС (5) − Средняя с/с "
    "(8) × Кол-во чистых продаж (3) + Расходы ВБ (9) + Продвижение (10) + Прочие "
    "накладные (11) (формула). Это управленческий результат снизу вверх, из показателей "
    "этого же листа — он НЕ равен строке «Чистая прибыль / убыток» на листе PL: там своя "
    "методология (начисление, налог на прибыль, другой контур расходов), сравнивать эти "
    "два числа напрямую некорректно.",
    "13. Маржинальность по валовой прибыли, % = 1 − (Средняя с/с, пункт 8 × Кол-во "
    "чистых продаж, пункт 3) / Продажи до СПП без НДС (пункт 5) (формула). В знаменателе "
    "— вся себестоимость за месяц (ставка на единицу, умноженная на количество), а не "
    "сама по себе цифра из пункта 8.",
    "14. Маржинальность по маржинальной прибыли (без продвижения), % = (Валовая прибыль "
    "+ Расходы ВБ без продвижения, пункт 9) / Продажи до СПП без НДС (формула). Расходы "
    "ВБ здесь уже отрицательны, поэтому прибавляются, а не вычитаются.",
    "15. Маржинальность по маржинальной прибыли (с продвижением), % — то же самое, "
    "дополнительно с учётом продвижения (пункт 10) (формула).",
    "16. Рентабельность по чистой прибыли, % = Чистая прибыль (пункт 12) / Продажи до "
    "СПП без НДС (пункт 5) (формула).",
    "",
    "Себестоимость и расходы ВБ учитываются по дате бухгалтерской проводки/операции. "
    "Если месяц ещё не закрыт на момент формирования отчёта, эти показатели могут быть "
    "неполными — отчёт показывает фактически проведённые на дату отчёта данные и не "
    "прогнозирует их до конца месяца.",
    "Количество продаж и возвратов по этому методу может не совпадать с блоком FIFO ниже: "
    "здесь возврат уменьшает показатели месяца, в котором он фактически произошёл, а в "
    "блоке FIFO — месяца, в котором товар был изначально продан. Это особенность двух "
    "методов учёта, а не ошибка.",
])

FIFO_METHODOLOGY = "\n".join([
    "МЕТОД: FIFO (УПРАВЛЕНЧЕСКИЙ). Выручка и себестоимость признаются на дату ИСХОДНОЙ "
    "продажи товара. Если товар впоследствии возвращают, возврат уменьшает показатели "
    "именно того месяца, когда товар был продан, а не месяца фактического возврата — "
    "поэтому при повторном формировании отчёта прошлые месяцы могут немного измениться, "
    "если по ним прошёл новый возврат. Строки 3, 6 и 9–16 на листе — не готовые числа, а "
    "формулы Excel со ссылками на другие строки этого же столбца. Порядок расчёта "
    "каждого показателя:",
    "",
    "1. Кол-во продаж, шт — количество единиц, проданных в месяце по дате исходной "
    "продажи (управленческие данные daily_sales, inventories.inv_gl_final).",
    "2. Кол-во возвратов, шт — количество единиц, проданных в этом месяце, продажи по "
    "которым были впоследствии отменены возвратом (на любую дату вплоть до даты отчёта). "
    "Показано для сопоставления с кэш-методом; отдельного «события возврата» в этом "
    "методе нет — возврат просто уменьшает данные месяца продажи, а не создаёт запись в "
    "месяце возврата.",
    "3. Кол-во чистых продаж, шт = Кол-во продаж − Кол-во возвратов (формула).",
    "4. Продажи до СПП с НДС, ₽ — управленческая выручка по цене до применения скидки "
    "СПП, с НДС, просуммированная по датам исходных продаж и уменьшенная на суммы по "
    "продажам, впоследствии отменённым возвратом.",
    "5. Продажи до СПП без НДС, ₽ — та же выручка, но по каждой продаже вычтен НДС по "
    "её реальной ставке (10% или 22%, известна построчно в управленческих данных) — это "
    "прямой расчёт, не оценка. Используется как знаменатель строк маржинальности "
    "(13–16) ниже.",
    "6. Средняя цена на ед. продаж до СПП с НДС, ₽ = Продажи до СПП с НДС (пункт 4) / "
    "Кол-во чистых продаж (пункт 3) (формула).",
    "7. Средняя цена на ед. продаж после СПП с НДС (цена для покупателя), ₽ — сумма, "
    "фактически полученная от покупателя по тем же продажам (после СПП), делённая на "
    "Кол-во чистых продаж.",
    "8. Средняя с/с на ед. продаж без НДС, ₽ — управленческая себестоимость по методу "
    "FIFO (списание товара в порядке поступления партий, привязано к конкретной продаже, "
    "а не усреднено по периоду), делённая на Кол-во чистых продаж. Отличается от "
    "бухгалтерской себестоимости счёта 1.3 — и именно эта, управленческая, ставка на "
    "единицу используется и в кэш-блоке выше, за тот же месяц.",
    "9. Расходы ВБ без продвижения, ₽ — тот же комплексный пул операционных расходов "
    "площадки, что и в кэш-блоке (комиссия WB, логистика, хранение, приёмка, штрафы, "
    "удержания, лояльность, корректировки) — это расход периода, он не зависит от "
    "способа признания выручки, поэтому берётся из одного источника для обоих блоков. "
    "Показано со знаком расхода.",
    "10. Продвижение, ₽ — те же счета 1.4/1.5, статьи с «WB» в названии, относящиеся к "
    "рекламе, продвижению или маркетингу — общая для обоих блоков.",
    "11. Прочие накладные расходы, ₽ — остаток счетов 1.4/1.5 (без WB), плюс счёт 1.6, "
    "плюс счёт 1.7 — общая для обоих блоков. Используется только в чистой прибыли.",
    "12. Чистая прибыль (управленческая), ₽ = Продажи до СПП без НДС (5) − Средняя с/с "
    "(8) × Кол-во чистых продаж (3) + Расходы ВБ (9) + Продвижение (10) + Прочие "
    "накладные (11) (формула). Налог на прибыль здесь не учитывается — это "
    "управленческий, а не бухгалтерский результат, и он НЕ равен строке «Чистая прибыль "
    "/ убыток» листа PL (там другая методология признания выручки и учтён налог).",
    "13. Маржинальность по валовой прибыли, % = 1 − (Средняя с/с, пункт 8 × Кол-во "
    "чистых продаж, пункт 3) / Продажи до СПП без НДС (пункт 5) (формула).",
    "14. Маржинальность по маржинальной прибыли (без продвижения), % = (Валовая прибыль "
    "+ Расходы ВБ без продвижения, пункт 9) / Продажи до СПП без НДС (формула).",
    "15. Маржинальность по маржинальной прибыли (с продвижением), % — то же самое, "
    "дополнительно с учётом продвижения (пункт 10) (формула).",
    "16. Рентабельность по чистой прибыли, % = Чистая прибыль (пункт 12) / Продажи до "
    "СПП без НДС (пункт 5) (формула). Оба блока (кэш и FIFO) считают чистую прибыль "
    "и рентабельность ОДИНАКОВО — снизу вверх из показателей этого листа; разница между "
    "блоками — только в дате признания выручки/себестоимости и в количестве чистых "
    "продаж (пункт 3), а не в методе расчёта прибыли.",
    "",
    "Данные по этому методу поступают из системы учёта остатков и продаж и могут "
    "уточняться по датам, близким к дате отчёта, по мере обработки новых возвратов.",
])


def _safe_str_date(dt):
    if dt is None:
        return ""
    if isinstance(dt, (datetime, date)):
        return dt.strftime("%d.%m.%Y")
    return str(dt)


def _unmerge_all(ws):
    for merged in list(ws.merged_cells.ranges):
        ws.unmerge_cells(str(merged))


def _estimate_note_height(text, total_width_units):
    """Грубая оценка высоты строки под многострочный текст методики: чем шире
    объединённый диапазон ячеек (столбец меток + столбцы с данными), тем
    больше символов помещается в одну визуальную строку до переноса."""
    chars_per_line = max(int(total_width_units * 1.7), 70)

    total_lines = 0
    for paragraph in text.split("\n"):
        if paragraph == "":
            total_lines += 1
        else:
            total_lines += max(1, -(-len(paragraph) // chars_per_line))

    height = 15 * total_lines + 20
    return min(max(height, 90), 900)


def _draw_note_box(ws, row, col_start, col_end, text, height=58):
    ws.merge_cells(
        start_row=row, start_column=col_start,
        end_row=row, end_column=col_end,
    )
    cell = ws.cell(row=row, column=col_start)
    cell.value = text
    cell.font = NOTE_FONT
    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    for col in range(col_start, col_end + 1):
        c = ws.cell(row=row, column=col)
        c.fill = NOTE_FILL
        c.border = Border(
            left=THIN_GRAY if col == col_start else None,
            right=THIN_GRAY if col == col_end else None,
            top=THIN_GRAY,
            bottom=THIN_GRAY,
        )

    ws.row_dimensions[row].height = height


def _number_format_for_row(row_name):
    if row_name in QTY_ROWS:
        return "#,##0"
    if row_name in MONEY_ROWS:
        return "#,##0"
    if row_name in PERCENT_ROWS:
        return "0.0%"
    return "General"


def _row_num(data_start_row, row_name):
    return data_start_row + ROW_ORDER.index(row_name)


def _formula_for_row(row_name, col_letter, data_start_row):
    """Строит формулу Excel для расчётных строк (см. FORMULA_ROWS) — ссылки
    на другие строки ТОГО ЖЕ столбца, чтобы Даря могла кликнуть на ячейку
    в Excel и увидеть, из чего получено число, а не просто готовую цифру."""

    def rn(name):
        return f"{col_letter}{_row_num(data_start_row, name)}"

    net_qty = rn(ROW_NET_QTY)
    revenue_vatless = rn(ROW_AMOUNT_BEFORE_SPP_VATLESS)
    avg_cogs = rn(ROW_AVG_COGS)
    wb_costs = rn(ROW_WB_COSTS)
    promo = rn(ROW_PROMO)
    other_overheads = rn(ROW_OTHER_OVERHEADS)
    net_profit = rn(ROW_NET_PROFIT)

    if row_name == ROW_NET_QTY:
        return f"={rn(ROW_SALES_QTY)}-{rn(ROW_RETURNS_QTY)}"

    if row_name == ROW_AVG_PRICE_BEFORE_SPP:
        return f'=IF({net_qty}=0,"",{rn(ROW_AMOUNT_BEFORE_SPP)}/{net_qty})'

    if row_name == ROW_NET_PROFIT:
        return (
            f"={revenue_vatless}-{avg_cogs}*{net_qty}"
            f"+{wb_costs}+{promo}+{other_overheads}"
        )

    if row_name == ROW_GROSS_MARGIN:
        return f'=IF({revenue_vatless}=0,"",1-({avg_cogs}*{net_qty})/{revenue_vatless})'

    if row_name == ROW_MARGIN_NO_PROMO:
        return (
            f'=IF({revenue_vatless}=0,"",'
            f"({revenue_vatless}-{avg_cogs}*{net_qty}+{wb_costs})/{revenue_vatless})"
        )

    if row_name == ROW_MARGIN_WITH_PROMO:
        return (
            f'=IF({revenue_vatless}=0,"",'
            f"({revenue_vatless}-{avg_cogs}*{net_qty}+{wb_costs}+{promo})/{revenue_vatless})"
        )

    if row_name == ROW_NET_MARGIN:
        return f'=IF({revenue_vatless}=0,"",{net_profit}/{revenue_vatless})'

    return None


def _draw_block(ws, start_row, title, methodology_text, block_df, year_groups, ordered_cols):
    row = start_row

    draw_section_title(ws, row, 1, len(ordered_cols) + 1, title)
    row += 1

    total_width_units = LABEL_COL_WIDTH + DATA_COL_WIDTH * len(ordered_cols)
    note_height = _estimate_note_height(methodology_text, total_width_units)
    _draw_note_box(ws, row, 1, len(ordered_cols) + 1, methodology_text, height=note_height)
    row += 2

    # year header row (объединённые ячейки по годам) + месяц/итого строка
    year_row = row
    month_row = row + 1

    col = 2
    for group in year_groups:
        span = len(group["month_cols"]) + 1  # + "Итого {year}"
        ws.merge_cells(start_row=year_row, start_column=col, end_row=year_row, end_column=col + span - 1)
        cell = ws.cell(row=year_row, column=col, value=str(group["year"]))
        cell.font = FONTS["header_white"]
        cell.fill = FILLS["header"]
        cell.alignment = ALIGNMENTS["center"]
        for c in range(col, col + span):
            ws.cell(row=year_row, column=c).fill = FILLS["header"]
            ws.cell(row=year_row, column=c).border = BORDERS["thin"]
        col += span

    ws.cell(row=year_row, column=1).fill = FILLS["header"]
    ws.cell(row=year_row, column=1).border = BORDERS["thin"]

    draw_table_header(ws, month_row, ["Показатель"] + ordered_cols, start_col=1, wrap=True)
    ws.row_dimensions[month_row].height = 28

    data_start_row = month_row + 1

    for i, row_name in enumerate(ROW_ORDER):
        r = data_start_row + i
        is_estimated = row_name in ESTIMATED_CASH_ROWS and title.startswith("МЕТОД: ЦЕЛЕВОЙ")
        is_formula_row = row_name in FORMULA_ROWS

        label_cell = ws.cell(row=r, column=1, value=row_name)
        label_cell.font = FONTS["bold"] if row_name in PERCENT_ROWS else FONTS["normal"]
        label_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        label_cell.border = BORDERS["thin"]
        label_cell.fill = FILLS["alt"] if i % 2 == 0 else FILLS["none"]

        number_format = _number_format_for_row(row_name)

        for j, col_name in enumerate(ordered_cols, start=2):
            value = block_df.loc[row_name, col_name] if (not block_df.empty and col_name in block_df.columns) else None
            cell = ws.cell(row=r, column=j)
            col_letter = get_column_letter(j)

            if is_formula_row and not block_df.empty and col_name in block_df.columns:
                # Формула Excel со ссылками на другие строки этого же столбца —
                # чтобы число можно было проверить, кликнув на ячейку.
                cell.value = _formula_for_row(row_name, col_letter, data_start_row)
            elif value is not None and row_name in PERCENT_ROWS:
                cell.value = float(value) / 100.0
            elif value is not None:
                cell.value = float(value)
            else:
                cell.value = None

            cell.number_format = number_format
            cell.border = BORDERS["thin"]

            is_total_col = any(col_name == g["total_col"] for g in year_groups)

            if is_estimated:
                cell.font = ESTIMATE_FONT
                cell.fill = ESTIMATE_FILL
            elif is_total_col:
                cell.font = FONTS["bold"]
                cell.fill = TOTAL_COL_FILL
            else:
                cell.font = FONTS["normal"]
                cell.fill = FILLS["alt"] if i % 2 == 0 else FILLS["none"]

    return data_start_row + len(ROW_ORDER)


def style_unit_economics_sheet(ws, payload, date_to=None):
    _unmerge_all(ws)
    clear_range(ws, row_start=1, row_end=400, col_start=1, col_end=120)

    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "B9"

    draw_toc_button(ws)

    subtitle = "Управленческая отчетность (management pack)"
    currency = "Российский рубль (RUB)"
    if date_to:
        currency = f"{currency} • дата отчета: {_safe_str_date(date_to)}"

    draw_sheet_header(
        ws,
        title="1.8 ЮНИТ-ЭКОНОМИКА ПРОДАЖ (КЭШ / FIFO)",
        subtitle=subtitle,
        currency=currency,
    )

    year_groups = payload.get("year_groups") or []
    ordered_cols = []
    for g in year_groups:
        ordered_cols.extend(g["month_cols"])
        ordered_cols.append(g["total_col"])

    widths = {"A": LABEL_COL_WIDTH}
    for i in range(len(ordered_cols)):
        widths[get_column_letter(i + 2)] = DATA_COL_WIDTH
    set_column_widths(ws, widths)

    row_heights = {1: 20, 2: 24, 3: 18, 4: 18, 6: 10}
    set_row_heights(ws, row_heights)

    row = 8

    row = _draw_block(
        ws, row,
        "МЕТОД: ЦЕЛЕВОЙ ОБОРОТ (КЭШ, С ВОЗВРАТАМИ)",
        CASH_METHODOLOGY,
        payload.get("cash"),
        year_groups,
        ordered_cols,
    )

    row += 2

    row = _draw_block(
        ws, row,
        "МЕТОД: FIFO (УПРАВЛЕНЧЕСКИЙ)",
        FIFO_METHODOLOGY,
        payload.get("fifo"),
        year_groups,
        ordered_cols,
    )

    return row
