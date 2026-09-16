# =============================================================================
#  10. КНИГА СО СВОДНЫМИ (нативные сводные таблицы Excel)
#
#      Отдельный файл: два листа со сводными — по движению денежных средств
#      и по P&L — и два листа-источника с сырыми строками витрин.
#
#      Команда только наполняет источники и раздвигает диапазоны «умных
#      таблиц»; сами сводные Excel пересчитывает при открытии файла
#      (refreshOnLoad). Макросов и VBA нет.
#
#      Раскладка задана в скелете assets/pivots_skeleton.xlsx и собирается
#      скриптом assets/build_pivots_skeleton.py — руками в Excel скелет
#      править нельзя, Excel переписывает его по-своему.
# =============================================================================

PIVOTS_SKELETON = Path(__file__).resolve().parent / "assets" / "pivots_skeleton.xlsx"

PIVOT_SOURCES = {
    "raw_cf": "SELECT * FROM pg.cf_to_csv WHERE date_from <= $date_from "
              "ORDER BY date_from",
    "raw_pl": "SELECT * FROM pg.pl_for_csv WHERE date_from <= $date_from "
              "ORDER BY date_from",
}


def _pivot_cell(value):
    """Приводит значение из витрины к типу, который принимает openpyxl."""
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def fill_pivot_source(ws, table_name, columns, rows):
    """Наполняет лист-источник и раздвигает диапазон «умной таблицы».

    Колонки раскладываются по заголовкам, которые уже лежат в скелете:
    поля сводной привязаны к позициям, и менять порядок нельзя, даже
    если витрина однажды вернёт колонки в другом порядке.
    """
    header = [ws.cell(row=1, column=i).value
              for i in range(1, ws.max_column + 1)]
    header = [h for h in header if h]
    if not header:
        header = list(columns)

    order = []
    for name in header:
        order.append(columns.index(name) if name in columns else None)

    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row)

    for i, row in enumerate(rows, start=2):
        for j, src in enumerate(order, start=1):
            if src is None:
                continue
            ws.cell(row=i, column=j, value=_pivot_cell(row[src]))

    last_row = max(2, 1 + len(rows))
    ref = "A1:%s%d" % (get_column_letter(len(header)), last_row)

    table = ws.tables.get(table_name)
    if table is not None:
        table.ref = ref
        if table.autoFilter is not None:
            table.autoFilter.ref = ref

    return len(rows)


def build_pivots_workbook(date_from, out_path=None):
    """Собирает книгу со сводными на отчётную дату."""
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)

    if not PIVOTS_SKELETON.exists():
        raise ValueError(
            "Не найден скелет сводных: %s. Соберите его скриптом "
            "assets/build_pivots_skeleton.py" % PIVOTS_SKELETON.name)

    data = {}
    with get_duckdb_conn_with_opt(ro=True) as con:
        for name, sql in PIVOT_SOURCES.items():
            cur = con.execute(sql, parameters={"date_from": date_from})
            data[name] = ([d[0] for d in cur.description], cur.fetchall())

    wb = load_workbook(PIVOTS_SKELETON)

    counts = {}
    for name, (columns, rows) in data.items():
        if name in wb.sheetnames:
            counts[name] = fill_pivot_source(wb[name], name, columns, rows)

    # сводные обновятся сами при открытии файла
    for sheet in wb.worksheets:
        for pivot in getattr(sheet, "_pivots", []):
            pivot.cache.refreshOnLoad = True
        for view in sheet.views.sheetView:
            view.tabSelected = False
    wb.active = 0

    path = Path(out_path) if out_path else Path(
        "pivots_%s.xlsx" % date_from.isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)

    return path, counts
