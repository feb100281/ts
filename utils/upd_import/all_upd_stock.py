import pandas as pd
from pathlib import Path
import re

source_folder = Path('/Users/daria/Desktop/ТРЕНДСЕТТЕР/Бух данные/upds/all_stock_upd')
base_path = Path.cwd()
upd_path = base_path / "data" / "all_stock_upd"
upd_path.mkdir(parents=True, exist_ok=True)

COLUMN_MAPPING = {
    'А': 'Код_товара',
    '1а': 'Наименование_товара',
    '2а': 'Единица_измерения',
    '3': 'Количество',
    '4': 'Цена_без_НДС',
    '5': 'Стоимость_без_НДС',
    '7': 'Ставка_НДС',
    '8': 'Сумма_НДС',
    '9': 'Стоимость_с_НДС',
    '10а': 'Страна_происхождения',
    '11': 'Декларация',
}



UPD_CONFIGS = {
    "УПД 1 от 25 января 2024 г.xlsx": {
        "number": "1",
        "date": "2024-01-25",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 7348,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },

    "УПД 2 от 1 февраля 2024 г.xlsx": {
        "number": "2",
        "date": "2024-02-01",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 7032,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },

    "УПД 5 от 6 февраля 2024 г.xlsx": {
        "number": "5",
        "date": "2024-02-06",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 7585,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },

    "УПД 6 от 12 февраля 2024 г.xlsx": {
        "number": "6",
        "date": "2024-02-12",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 150,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },

    "УПД 9 от 16 февраля 2024 г.xlsx": {
        "number": "9",
        "date": "2024-02-16",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 7444,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },

    "УПД 13 от 22 февраля 2024 г.xlsx": {
        "number": "13",
        "date": "2024-02-22",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 7297,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
    
    
     "УПД 23 от 6 марта 2024 г.xlsx": {
        "number": "23",
        "date": "2024-03-06",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 27,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
     
     "УПД 33 от 22 марта 2024 г.xlsx": {
        "number": "33",
        "date": "2024-03-22",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 57,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
     
     "УПД 36 от 4 апреля 2024 г.xlsx": {
        "number": "36",
        "date": "2024-04-04",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 103,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
     
     "УПД 111 от 19 июля 2024 г.xlsx": {
        "number": "111",
        "date": "2024-07-19",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 91,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
     
      "УПД 74 от 14 августа 2025 г.xlsx": {
        "number": "74",
        "date": "2025-08-14",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 730,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 83 от 25 августа 2025 г.xlsx": {
        "number": "83",
        "date": "2025-08-25",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 5522,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 27 от 18 марта 2026 г.xlsx": {
        "number": "27",
        "date": "2026-03-18",
        "columns": "B:BQ",
        "header_row": 16,
        "start_row": 17,
        "end_row": 528,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      
      "УПД 26 от 18 марта 2026 г.xlsx": {
        "number": "26",
        "date": "2026-03-18",
        "columns": "B:BQ",
        "header_row": 16,
        "start_row": 17,
        "end_row": 66,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 892 от 23 декабря 2023 г.xlsx": {
        "number": "892",
        "date": "2023-12-23",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 3366,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 884 от 19 декабря 2023 г.xlsx": {
        "number": "884",
        "date": "2023-12-19",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 561,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 872 от 15 декабря 2023 г.xlsx": {
        "number": "872",
        "date": "2023-12-15",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 11158,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 24 от 6 марта 2024 г.xlsx": {
        "number": "24",
        "date": "2024-03-06",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 6496,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 31 от 15 марта 2024 г.xlsx": {
        "number": "31",
        "date": "2024-03-15",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 7098,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
      "УПД 40 от 29 марта 2024 г.xlsx": {
        "number": "40",
        "date": "2024-03-29",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 5419,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
       "УПД 91 от 14 июня 2024 г.xlsx": {
        "number": "91",
        "date": "2024-06-14",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 3305,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
       
        "УПД 131 от 23 августа 2024 г.xlsx": {
        "number": "131",
        "date": "2024-08-23",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 896,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
        
        "УПД 132 от 23 августа 2024 г.xlsx": {
        "number": "132",
        "date": "2024-08-23",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 3556,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
        
        "УПД 142 от 5 сентября 2024 г.xlsx": {
        "number": "142",
        "date": "2024-09-05",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 6622,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
        
        "УПД 146 от 19 сентября 2024 г.xlsx": {
        "number": "146",
        "date": "2024-09-19",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 5216,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
        
        "УПД 147 от 19 сентября 2024 г.xlsx": {
        "number": "147",
        "date": "2024-09-19",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 2496,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
        
        "УПД 154 от 30 сентября 2024 г.xlsx": {
        "number": "154",
        "date": "2024-09-30",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 2988,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
        
      "УПД 156 от 8 октября 2024 г.xlsx": {
        "number": "156",
        "date": "2024-10-08",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 2262,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
      
       "УПД 162 от 17 октября 2024 г.xlsx": {
        "number": "162",
        "date": "2024-10-17",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 2555,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "Лист_1"
    },
       
       "УПД 582 от 30 августа 2023 г.xlsx": {
        "number": "582",
        "date": "2023-08-30",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 2227,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "TDSheet"
    },
       
     "УПД 625 от 28 сентября 2023 г.xlsx": {
        "number": "625",
        "date": "2023-09-28",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 6297,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "TDSheet"
    },
     
    
    "УПД 709 от 5 октября 2023 г.xlsx": {
        "number": "709",
        "date": "2023-10-05",
        "columns": "B:BT",
        "header_row": 14,
        "start_row": 15,
        "end_row": 4235,
        "supplier": "МЕГАМОЛСТРОЙ ООО",
        "sheet": "TDSheet"
    },
    

    "УПД 710 от 5 октября 2023 г.xlsx": {
            "number": "710",
            "date": "2023-10-05",
            "columns": "B:BT",
            "header_row": 14,
            "start_row": 15,
            "end_row": 1037,
            "supplier": "МЕГАМОЛСТРОЙ ООО",
            "sheet": "TDSheet"
        },
    
        "УПД 713 от 11 октября 2023 г.xlsx": {
                "number": "713",
                "date": "2023-10-11",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 5524,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "TDSheet"
            },
        
        "УПД 728 от 18 октября 2023 г.xlsx": {
                "number": "728",
                "date": "2023-10-18",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 7581,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "TDSheet"
            },
        
        "УПД 731 от 20 октября 2023 г.xlsx": {
                "number": "731",
                "date": "2023-10-20",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 8487,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "TDSheet"
            },
        
        "УПД 782 от 27 октября 2023 г.xlsx": {
                "number": "782",
                "date": "2023-10-27",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 7938,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
        
         "УПД 783 от 28 октября 2023 г.xlsx": {
                "number": "783",
                "date": "2023-10-28",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 6740,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
         
          "УПД 784 от 2 ноября 2023 г.xlsx": {
                "number": "784",
                "date": "2023-11-02",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 8553,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
          
           "УПД 788 от 3 ноября 2023 г.xlsx": {
                "number": "788",
                "date": "2023-11-03",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 6093,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
           
           "УПД 791 от 10 ноября 2023 г.xlsx": {
                "number": "791",
                "date": "2023-11-10",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 9668,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
           
            "УПД 792 от 11 ноября 2023 г.xlsx": {
                "number": "792",
                "date": "2023-11-11",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 3748,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
            
             "УПД 804 от 15 ноября 2023 г.xlsx": {
                "number": "804",
                "date": "2023-11-15",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 6194,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
             
            "УПД 813 от 23 ноября 2023 г.xlsx": {
                "number": "813",
                "date": "2023-11-23",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 1247,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
            
            "УПД 814 от 24 ноября 2023 г.xlsx": {
                "number": "814",
                "date": "2023-11-24",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 1009,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
            
            "УПД 815 от 23 ноября 2023 г.xlsx": {
                "number": "815",
                "date": "2023-11-23",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 12637,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
            
        "УПД 821 от 29 ноября 2023 г.xlsx": {
                "number": "821",
                "date": "2023-11-29",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 2127,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
        
        "УПД 825 от 1 декабря 2023 г.xlsx": {
                "number": "825",
                "date": "2023-12-01",
                "columns": "B:BT",
                "header_row": 14,
                "start_row": 15,
                "end_row": 247,
                "supplier": "МЕГАМОЛСТРОЙ ООО",
                "sheet": "Лист_1"
            },
        
        "УПД 302 от 27 ноября 2025 г.xlsx": {
                "number": "302",
                "date": "2025-11-27",
                "columns": "A:EK",
                "header_row": 25,
                "start_row": 26,
                "end_row": 726,
                "supplier": "ОРБИКО СТАЙЛ ООО",
                "sheet": "Лист1"
  
            },
        
         "УПД 303 от 27 ноября 2025 г.xlsx": {
                "number": "303",
                "date": "2025-11-27",
                "columns": "A:EK",
                "header_row": 25,
                "start_row": 26,
                "end_row": 2147,
                "supplier": "ОРБИКО СТАЙЛ ООО",
                "sheet": "Лист1"
  
            },
    
    }


def to_number(s):
    return (
        s.astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
        .pipe(pd.to_numeric, errors='coerce')
    )


def is_header_value(df, col, values):
    if col not in df.columns:
        return pd.Series(False, index=df.index)

    return df[col].astype(str).str.strip().isin(values)


for filename, config in UPD_CONFIGS.items():
    filepath = source_folder / filename

    if not filepath.exists():
        print(f"Файл не найден: {filename}")
        continue

    headers_df = pd.read_excel(
        filepath,
        sheet_name=config["sheet"],
        skiprows=config["header_row"] - 1,
        nrows=1,
        usecols=config["columns"],
        dtype=str,
        header=None
    )

    nrows_to_read = config["end_row"] - config["start_row"] + 1

    df = pd.read_excel(
        filepath,
        sheet_name=config["sheet"],
        skiprows=config["start_row"] - 1,
        nrows=nrows_to_read,
        usecols=config["columns"],
        dtype=str,
        header=None
    )

    df.columns = headers_df.iloc[0].astype(str)

    df.columns = (
        df.columns
        .astype(str)
        .str.replace('\n', ' ', regex=False)
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )

    df.columns = [
        col if col and col != 'nan' else f'empty_{i}'
        for i, col in enumerate(df.columns)
    ]
    
    

    rename_dict = {}
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean in COLUMN_MAPPING:
            rename_dict[col] = COLUMN_MAPPING[col_clean]

    df = df.rename(columns=rename_dict)

    # Удаляем дубли колонок ДО расчетов
    df = df.loc[:, ~df.columns.duplicated()]

    # Удаляем ненужные колонки
    cols_to_drop = ['1', '1б', '2', '6', '10']
    cols_to_drop = [col for col in cols_to_drop if col in df.columns]
    df = df.drop(columns=cols_to_drop)

    # Удаляем пустые колонки
    df = df.loc[:, ~df.columns.str.startswith('empty', na=False)]

    # Удаляем строки, где нет наименования товара
    if 'Наименование_товара' in df.columns:
        df = df.dropna(subset=['Наименование_товара'])
        df = df[df['Наименование_товара'].astype(str).str.strip() != '']

    # 1. Удаляем только явные строки-шапки
    header_mask = (
        is_header_value(df, 'Код_товара', ['А', 'Код_товара']) &
        is_header_value(df, 'Наименование_товара', ['1а', 'Наименование_товара']) &
        is_header_value(df, 'Количество', ['3', 'Количество'])
    )

    df = df[~header_mask].copy()

    # 2. Удаляем текстовый мусор от многострочной шапки
    trash_words = [
        'Код товара',
        'Наименование товара',
        'Количе',
        'чество',
        'объем',
        'Цена (тариф)',
        'Стоимость товаров',
        'Налоговая ставка',
        'Сумма налога',
        'Регистрационный номер декларации',
        'единицу изм',
        'венных прав',
        'ляемая поку',

    ]

    text_cols = [
        col for col in df.columns
        if col in [
            'Код_товара',
            'Наименование_товара',
            'Количество',
            'Единица_измерения',
            'Цена_без_НДС',
            'Стоимость_без_НДС',
            'Ставка_НДС',
            'Сумма_НДС',
            'Стоимость_с_НДС',
            'Страна_происхождения',
            'Декларация',
        ]
    ]

    trash_mask = pd.Series(False, index=df.index)

    for col in text_cols:
        s = df[col].astype(str).str.strip()
        trash_mask |= s.isin(['NULL', 'nan', 'None'])
        trash_mask |= s.str.contains('|'.join(map(re.escape, trash_words)), case=False, na=False, regex=True)

    df = df[~trash_mask].copy()

    # 3. Оставляем только реальные товарные строки
    if 'Количество' in df.columns and 'Стоимость_с_НДС' in df.columns:
        qty_num = to_number(df['Количество'])
        amount_num = to_number(df['Стоимость_с_НДС'])

        df = df[qty_num.notna() & amount_num.notna()].copy()

    # Добавляем служебные колонки
    df['file_name'] = filename
    df['number'] = config['number']
    df['date'] = config['date']
    df['supplier'] = config['supplier']

    # Расчет итога по документу
    if 'Стоимость_с_НДС' in df.columns:
        df['_Стоимость_с_НДС_num'] = to_number(df['Стоимость_с_НДС']).fillna(0)
        total_amount_vat = df['_Стоимость_с_НДС_num'].sum()
        df = df.drop(columns=['_Стоимость_с_НДС_num'])
    else:
        total_amount_vat = 0

    df['итого_сумма_с_ндс_по_файлу'] = total_amount_vat

    column_order = [
        'supplier',
        'file_name',
        'number',
        'date',
        'итого_сумма_с_ндс_по_файлу',
        'Код_товара',
        'Наименование_товара',
        'Количество',
        'Единица_измерения',
        'Цена_без_НДС',
        'Стоимость_без_НДС',
        'Ставка_НДС',
        'Сумма_НДС',
        'Стоимость_с_НДС',
        'Страна_происхождения',
        'Декларация',
    ]

    existing_columns = [col for col in column_order if col in df.columns]
    df = df[existing_columns]

    output_file = upd_path / f"{Path(filename).stem}.parquet"
    df.to_parquet(output_file, index=False)

    print(f"Готово: {filename} | строк: {len(df)} | сумма: {total_amount_vat:,.2f}")