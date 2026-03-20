
# # reporting/excel/engine.py
# # Движ под мэн пак в excel
# import os
# import django
# from pathlib import Path

# import pandas as pd

# from openpyxl import load_workbook
# from openpyxl.utils import get_column_letter
# from openpyxl.utils import column_index_from_string
# from openpyxl.utils.cell import coordinate_from_string

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ts.settings")
# django.setup()

# from django.db import connection

# import os
# import django
# from pathlib import Path
# from datetime import date

# from openpyxl import load_workbook
# from openpyxl.utils import get_column_letter

# from .treasure import get_treasury_report, get_wb_balance

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ts.settings")
# django.setup()

# from django.db import connection


# TEMPLATE_PATH = Path("reporting/excel/template.xlsx")
# OUTPUT_PATH = Path("reporting/excel/manpack.xlsx")

# DATA_UPDATE = {
#     "raw_cf": "raw_cf",
#     "raw_pl": "raw_pl",
# }

# SQL = {
#     "raw_cf": (
#         "SELECT * "
#         "FROM public.cf_to_csv "
#         "WHERE date_from <= %s "
#     ),
#     "raw_pl": (
#         "SELECT * "
#         "FROM public.pl_for_csv "
#         "WHERE date_from <= %s "
#     ),
# }


# def fetch_data(sql, date_to):
#     with connection.cursor() as cur:
#         cur.execute(sql, [date_to])
#         rows = cur.fetchall()
#         columns = [col[0] for col in cur.description]

#     return columns, rows


# def update_table(ws, tbl_name, sql, date_to):
#     columns, rows = fetch_data(sql, date_to)

#     if tbl_name not in ws.tables:
#         raise ValueError(f"Таблица {tbl_name!r} не найдена на листе {ws.title!r}")

#     table = ws.tables[tbl_name]

#     start_cell, end_cell = table.ref.split(":")
#     start_col_idx = ws[start_cell].column
#     start_row_idx = ws[start_cell].row
#     end_col_idx = ws[end_cell].column
#     old_end_row_idx = ws[end_cell].row

#     # заголовки
#     for i, col_name in enumerate(columns, start=start_col_idx):
#         ws.cell(row=start_row_idx, column=i, value=col_name)

#     data_start_row = start_row_idx + 1

#     # пишем новые данные
#     for r_idx, row in enumerate(rows, start=data_start_row):
#         for c_idx, value in enumerate(row, start=start_col_idx):
#             ws.cell(row=r_idx, column=c_idx, value=value)

#     # очищаем хвост старых данных
#     new_last_row = data_start_row + len(rows) - 1 if rows else data_start_row
#     clear_to_row = max(old_end_row_idx, ws.max_row)

#     for r in range(new_last_row + 1, clear_to_row + 1):
#         for c in range(start_col_idx, end_col_idx + 1):
#             ws.cell(row=r, column=c, value=None)

#     last_col = start_col_idx + len(columns) - 1
#     table.ref = (
#         f"{get_column_letter(start_col_idx)}{start_row_idx}:"
#         f"{get_column_letter(last_col)}{new_last_row}"
#     )


# def write_df(ws, start_cell, df):
#     col_letter, row_start = coordinate_from_string(start_cell)
#     col_start = column_index_from_string(col_letter)

#     # 1. заголовки (колонки df)
#     for j, col_name in enumerate(df.columns):
#         ws.cell(row=row_start, column=col_start + j + 1, value=col_name)

#     # 2. индекс (в первый столбец)
#     for i, idx in enumerate(df.index):
#         ws.cell(row=row_start + i + 1, column=col_start, value=idx)

#     # 3. данные
#     for i, row in enumerate(df.itertuples(index=False)):
#         for j, value in enumerate(row):
#             ws.cell(
#                 row=row_start + i + 1,
#                 column=col_start + j + 1,
#                 value=value
#             )



# def main(date_to='2026-03-16'):
#     # дата для запроса баланса wb
#     wb_date = date_to
    
#     # дата для всего остального
    
#     date_to =  pd.to_datetime(date_to).date() if date_to else date.today()
    

#     # грузим шаблон ОДИН раз
#     wb = load_workbook(TEMPLATE_PATH)

#     for sheet_name, table_name in DATA_UPDATE.items():
#         ws = wb[sheet_name]
#         sql = SQL[table_name]
#         update_table(ws, table_name, sql, date_to)
    
#     #Печатаем Treasures Report
#     ba_df = get_treasury_report(date_to)
#     wb_df = get_wb_balance(wb_date)
#     ws = wb["2.1"]
#     write_df(ws, "A15", ba_df)
#     write_df(ws, "A35",wb_df)
#     ba_ballance = ba_df['Остаток'].sum()
#     ws["E7"] = ba_ballance   
#     money_in_trasfer = wb_df['Деньги в пути (ДВП)'].max()
#     wb_ballance = wb_df['Конечный баланс'].max()
#     ws["E8"] = money_in_trasfer   
#     ws["E9"] = wb_ballance   
    
    
#     #Печатаем дату    
#     wb["TOC"]["D5"] = date_to.strftime('%d %B %Y')
    
    
#     wb.security = None
#     wb.save(OUTPUT_PATH)
#     print(f"Файл сохранен: {OUTPUT_PATH}")


# if __name__ == "__main__":
#     main()








# reporting/excel/engine.py
from pathlib import Path
from datetime import date

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils import column_index_from_string
from openpyxl.utils.cell import coordinate_from_string
from django.db import connection

from .treasure import get_treasury_report, get_wb_balance


TEMPLATE_PATH = Path("reporting/excel/template.xlsx")

DATA_UPDATE = {
    "raw_cf": "raw_cf",
    "raw_pl": "raw_pl",
}

SQL = {
    "raw_cf": (
        "SELECT * "
        "FROM public.cf_to_csv "
        "WHERE date_from <= %s "
    ),
    "raw_pl": (
        "SELECT * "
        "FROM public.pl_for_csv "
        "WHERE date_from <= %s "
    ),
}


def fetch_data(sql, date_to):
    with connection.cursor() as cur:
        cur.execute(sql, [date_to])
        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]

    return columns, rows


def update_table(ws, tbl_name, sql, date_to):
    columns, rows = fetch_data(sql, date_to)

    if tbl_name not in ws.tables:
        raise ValueError(f"Таблица {tbl_name!r} не найдена на листе {ws.title!r}")

    table = ws.tables[tbl_name]

    start_cell, end_cell = table.ref.split(":")
    start_col_idx = ws[start_cell].column
    start_row_idx = ws[start_cell].row
    end_col_idx = ws[end_cell].column
    old_end_row_idx = ws[end_cell].row

    for i, col_name in enumerate(columns, start=start_col_idx):
        ws.cell(row=start_row_idx, column=i, value=col_name)

    data_start_row = start_row_idx + 1

    for r_idx, row in enumerate(rows, start=data_start_row):
        for c_idx, value in enumerate(row, start=start_col_idx):
            ws.cell(row=r_idx, column=c_idx, value=value)

    new_last_row = data_start_row + len(rows) - 1 if rows else data_start_row
    clear_to_row = max(old_end_row_idx, ws.max_row)

    for r in range(new_last_row + 1, clear_to_row + 1):
        for c in range(start_col_idx, end_col_idx + 1):
            ws.cell(row=r, column=c, value=None)

    last_col = start_col_idx + len(columns) - 1
    table.ref = (
        f"{get_column_letter(start_col_idx)}{start_row_idx}:"
        f"{get_column_letter(last_col)}{new_last_row}"
    )


def write_df(ws, start_cell, df):
    col_letter, row_start = coordinate_from_string(start_cell)
    col_start = column_index_from_string(col_letter)

    for j, col_name in enumerate(df.columns):
        ws.cell(row=row_start, column=col_start + j + 1, value=col_name)

    for i, idx in enumerate(df.index):
        ws.cell(row=row_start + i + 1, column=col_start, value=idx)

    for i, row in enumerate(df.itertuples(index=False)):
        for j, value in enumerate(row):
            ws.cell(
                row=row_start + i + 1,
                column=col_start + j + 1,
                value=value
            )


def build_manpack(date_to=None, output_path=None):
    wb_date = date_to
    date_to = pd.to_datetime(date_to).date() if date_to else date.today()

    wb = load_workbook(TEMPLATE_PATH)

    for sheet_name, table_name in DATA_UPDATE.items():
        ws = wb[sheet_name]
        sql = SQL[table_name]
        update_table(ws, table_name, sql, date_to)

    ba_df = get_treasury_report(date_to)
    wb_df = get_wb_balance(wb_date)

    ws = wb["2.1"]
    write_df(ws, "A15", ba_df)
    write_df(ws, "A35", wb_df)

    ba_ballance = ba_df["Остаток"].sum()
    ws["E7"] = ba_ballance

    money_in_trasfer = wb_df["Деньги в пути (ДВП)"].max()
    wb_ballance = wb_df["Конечный баланс"].max()

    ws["E8"] = money_in_trasfer
    ws["E9"] = wb_ballance

    wb["TOC"]["D5"] = date_to.strftime("%d %B %Y")
    wb.security = None

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_path)
        return output_path

    return wb


def main(date_to="2026-03-16", output_path="reporting/excel/manpack.xlsx"):
    output_path = build_manpack(date_to=date_to, output_path=output_path)
    print(f"Файл сохранен: {output_path}")


if __name__ == "__main__":
    main()