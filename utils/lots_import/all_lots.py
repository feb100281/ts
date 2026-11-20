# utils/lots_import/all_lots.py

import pandas as pd
from pathlib import Path


base_path = Path.cwd()

source_folder = Path('/Users/daria/Desktop/ТРЕНДСЕТТЕР/Бух данные/Лоты')

lots_path = base_path / "data" / "lots"
lots_path.mkdir(parents=True, exist_ok=True)


LOTS_CONFIGS = {
    "01 УПРАВЛЕНКА Расчет себестоимости H&M 1 лот (Calcualtion COGS 1 lot).xlsx": {
        "sheet": "ALL DATA 1 LOT",
        "columns": "A:T",
        "header_row": 1,
        "start_row": 2,
        "end_row": 85371,
    },
    
    
     "02 Расчет себестоимости H&M 2 лот (Calcualtion COGS 2 lot).xlsx": {
        "sheet": "ALL DATA 2 LOT",
        "columns": "A:T",
        "header_row": 1,
        "start_row": 2,
        "end_row": 42996,
    },
     
     
     "03 Расчет себестоимости H&M 3 лот (3 LOT CALCULATION COST AND BREAK-EVEN POINT).xlsx": {
        "sheet": "ALL DATA",
        "columns": "A:N",
        "header_row": 1,
        "start_row": 2,
        "end_row": 23531,
    },

     
     
     "04_2 Расчет себестоимости H&M 4 лот Бангладеш (4 LOT BANGLADESH-CALCULATION COST AND BREAK-EVEN POINT).xlsx": {
        "sheet": "COST AND CALCULATION MIN PRICE",
        "columns": "A:AA",
        "header_row": 2,
        "start_row": 3,
        "end_row": 212,
    },
     
     
     "04_3 Расчет себестоимости Marks & Spencer 4 лот (4 LOT M&S-CALCULATION COST AND BREAK-EVEN POINT).xlsx": {
        "sheet": "ALL DATA",
        "columns": "A:AF",
        "header_row": 1,
        "start_row": 2,
        "end_row": 26652,
    },
     
     
      "05 Расчет себестоимости H&M 5 лот (Calcualtion COGS 5 lot).xlsx": {
        "sheet": "ALL DATA 5",
        "columns": "A:X",
        "header_row": 1,
        "start_row": 2,
        "end_row": 10476,
    },
      
      "06_1 Расчет себестоимости H&M 6 лот (1-4) (6 LOT CALCUALTION COST AND BREAK-EVEN POINT).xlsx": {
        "sheet": "COST",
        "columns": "A:AE",
        "header_row": 2,
        "start_row": 3,
        "end_row": 1914,
    },
      
       "06_2 Расчет себестоимости H&M 6 лот (2-4) (Вывоз 6 лот 2025 + себес от ваге).xlsx": {
        "sheet": "6 LOT Вывоз",
        "columns": "A:AB",
        "header_row": 2,
        "start_row": 3,
        "end_row": 1468,
    },
       
       
       "06_3 Расчет себестоимости H&M 6 лот (3-4) (Вывоз_файл_себес_03-06-2025).xlsx": {
        "sheet": "6 лот вывоз 03-06-2025",
        "columns": "A:AH",
        "header_row": 2,
        "start_row": 3,
        "end_row": 145,
    },
       
        "06_3 Расчет себестоимости H&M 6 лот (3-4) (Вывоз_файл_себес_03-06-2025).xlsx": {
        "sheet": "Бангладеш",
        "columns": "A:AJ",
        "header_row": 2,
        "start_row": 3,
        "end_row": 259,
    },
       
       "06_4 Расчет себестоимости H&M 6 лот (4-4) (Цены 2 6 ЛОТ первый поставка. себес).xlsx": {
        "sheet": "UNIT COST",
        "columns": "A:AI",
        "header_row": 2,
        "start_row": 3,
        "end_row": 317,
    },
       
        "07 Расчет себестоимости Bershka 7 лот (BERSHKA GRADE-COST).xlsx": {
        "sheet": "Calculation COST",
        "columns": "A:AX",
        "header_row": 2,
        "start_row": 3,
        "end_row": 1898,
    },
        
        "08_1 Расчет себестоимости H&M 8 лот (1-2) (CALCULATION COST-DISKO CLUB 1-я фура (Армения) 17536 ед.).xlsx": {
        "sheet": "COST",
        "columns": "A:BF",
        "header_row": 2,
        "start_row": 3,
        "end_row": 6536,
    },
        
        "08_2 Расчет себестоимости H&M 8 лот (2-2) (Rasxodi_disco_2_я_фура_диско_клаб_из_Еревана (2)).xlsx": {
        "sheet": "total",
        "columns": "A:G",
        "header_row": 1,
        "start_row": 2,
        "end_row": 7522,
    },
        
        "08_3 Расчет себестоимости H&M 8 лот и Бершка остатки из Арташата- чего нет в УПД, но по факту пришли (Отгрузка_№_48_H&M_WB_ДИСКОКЛАБ_2_ая_и_3_яя_фура;_….xlsx": {
        "sheet": "Лист1",
        "columns": "A:D",
        "header_row": 1,
        "start_row": 2,
        "end_row": 3931,
    },
        
        "09 Расчет себестоимости H&M 9 лот (Final себес).xlsx": {
        "sheet": "Себес итог",
        "columns": "A:G",
        "header_row": 2,
        "start_row": 3,
        "end_row": 476,
    },
        
        "10_1 Расчет себестоимости Mothercare 10 лот (1-2) (Calculation COST Mothercare).xlsx": {
        "sheet": "COGS",
        "columns": "A:AI",
        "header_row": 2,
        "start_row": 3,
        "end_row": 167,
    },
        
        "10_2 Расчет себестоимости Mothercare 10 лот (2-2) (Себес итог + УПД (статус 1) № 34 от 31 марта 2026 г).xlsx": {
        "sheet": "Себес средн итог",
        "columns": "A:F",
        "header_row": 3,
        "start_row": 4,
        "end_row": 380,
    },
        
        "11_1 Расчет себестоимости H&M 11 лот (1-2) (Себес_Спец_ООО_Трендсеттер_11_лот_Орбика).xlsx": {
        "sheet": "Лист2",
        "columns": "A:B",
        "header_row": 3,
        "start_row": 4,
        "end_row": 1024,
    },
        
        "11_2 Расчет себестоимости H&M 11 лот (2-2) (Себес_Спец_ООО_Трендсеттер_11_лот_Орбика (2)).xlsx": {
        "sheet": "Лист2",
        "columns": "A:B",
        "header_row": 3,
        "start_row": 4,
        "end_row": 1024,
    },
     
}


def clean_columns(columns):
    return (
        columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


for filename, config in LOTS_CONFIGS.items():

    filepath = source_folder / filename

    if not filepath.exists():
        print(f"Файл не найден: {filename}")
        continue

    print(f"\nЧитаем файл: {filename}")

    headers_df = pd.read_excel(
        filepath,
        sheet_name=config["sheet"],
        skiprows=config["header_row"] - 1,
        nrows=1,
        usecols=config["columns"],
        dtype=str,
        header=None,
    )

    nrows_to_read = config["end_row"] - config["start_row"] + 1

    df = pd.read_excel(
        filepath,
        sheet_name=config["sheet"],
        skiprows=config["start_row"] - 1,
        nrows=nrows_to_read,
        usecols=config["columns"],
        dtype=str,
        header=None,
    )

    df.columns = clean_columns(headers_df.iloc[0])

    df.columns = [
        col if col and col != "nan" else f"empty_{i}"
        for i, col in enumerate(df.columns)
    ]

    # Номер строки Excel
    df["excel_row_number"] = range(
        config["start_row"],
        config["start_row"] + len(df)
    )

    # Удаляем дубли колонок
    df = df.loc[:, ~df.columns.duplicated()]

    # Удаляем пустые колонки
    df = df.loc[:, ~df.columns.str.startswith("empty", na=False)]

    # Удаляем полностью пустые строки
    df = df.dropna(how="all")

    # Удаляем строки, где все значения пустые строки
    df = df[
        ~df.apply(
            lambda row: row.astype(str).str.strip().eq("").all(),
            axis=1
        )
    ]

    # Добавляем служебные колонки
    df["file_name"] = filename
    df["sheet"] = config["sheet"]

    safe_sheet_name = (
        config["sheet"]
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    output_file = (
        lots_path /
        f"{Path(filename).stem}__{safe_sheet_name}.parquet"
    )

    df.to_parquet(output_file, index=False)

    print(
        f"Готово: {filename} | "
        f"строк: {len(df)} | "
        f"parquet: {output_file}"
    )