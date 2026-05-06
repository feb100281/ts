# ЭТО 2024 ГОД
import pandas as pd

from pathlib import Path


# source_folder = Path('/Users/daria/Desktop/ТРЕНДСЕТТЕР/Бух данные/upds/2024')
source_folder = Path('/Users/pavelustenko/Downloads/2024')
base_path = Path.cwd()
upd_path = base_path / "data" / "upd_2024"
upd_path.mkdir(parents=True, exist_ok=True)

UPD_LIST = {

    "Araqum HM-001 (1).xlsx": {
        "number": "HM-001",
        "date": "2024-04-23",
        "columns": "B:O",
        "header_row": 16,
        "nrows":160,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    
    "Araqum HM-004 (2).xlsx": {
        "number": "HM-004",
        "date": "2024-05-29",
        "columns": "B:O",
        "header_row": 16,
        "nrows":1632,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
     "Araqum HM-005 (3) (2).xlsx": {
        "number": "HM-005",
        "date": "2024-07-03",
        "columns": "B:O",
        "header_row": 16,
        "nrows":498,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
     
    "Araqum HM-006 (1) (2).xlsx": {
        "number": "HM-006",
        "date": "2024-07-12",
        "columns": "B:O",
        "header_row": 16,
        "nrows":504,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-007 (3) (2).xlsx": {
        "number": "HM-007",
        "date": "2024-07-25",
        "columns": "B:O",
        "header_row": 16,
        "nrows":338,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-008.xlsx": {
        "number": "HM-008",
        "date": "2024-08-09",
        "columns": "B:O",
        "header_row": 16,
        "nrows":2825,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-010.xlsx": {
        "number": "HM-010",
        "date": "2024-09-12",
        "columns": "B:O",
        "header_row": 16,
        "nrows":6429,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-011 последний.xlsx": {
        "number": "HM-011",
        "date": "2024-09-30",
        "columns": "B:O",
        "header_row": 16,
        "nrows":1173,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-012 (12)(1) скор 31-10 (1).xlsx": {
        "number": "HM-012",
        "date": "2024-10-08",
        "columns": "B:O",
        "header_row": 16,
        "nrows":1405,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-013 последняя.xlsx": {
        "number": "HM-013",
        "date": "2024-10-10",
        "columns": "B:O",
        "header_row": 16,
        "nrows":102,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-014.xlsx": {
        "number": "HM-014",
        "date": "2024-10-15",
        "columns": "B:O",
        "header_row": 16,
        "nrows":188,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-016 (1) последнее.xlsx": {
        "number": "HM-016",
        "date": "2024-10-24",
        "columns": "B:P",
        "header_row": 16,
        "nrows":146,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-017 без арт.xlsx": {
        "number": "HM-017",
        "date": "2024-10-29",
        "columns": "B:P",
        "header_row": 16,
        "nrows":126,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-018 без арт (1) ПОСЛЕДНЕЕ.xlsx": {
        "number": "HM-018",
        "date": "2024-11-04",
        "columns": "B:P",
        "header_row": 16,
        "nrows":156,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-019 +Артикул (6).xlsx": {
        "number": "HM-019",
        "date": "2024-11-08",
        "columns": "B:P",
        "header_row": 16,
        "nrows":240,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    "Araqum HM-020 +Артикул (1).xlsx": {
        "number": "HM-020",
        "date": "2024-11-12",
        "columns": "B:P",
        "header_row": 16,
        "nrows":144,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
     "Araqum HM-021 (1).xlsx": {
        "number": "HM-021",
        "date": "2024-11-15",
        "columns": "B:P",
        "header_row": 16,
        "nrows":271,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
     
     "Araqum HM-022 +Артикул (2).xlsx": {
        "number": "HM-022",
        "date": "2024-11-21",
        "columns": "B:P",
        "header_row": 16,
        "nrows":202,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
     
     "Araqum HM-023.xlsx": {
        "number": "HM-023",
        "date": "2024-11-28",
        "columns": "B:O",
        "header_row": 16,
        "nrows":1647,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
     
      "Araqum HM-024.xlsx": {
        "number": "HM-024",
        "date": "2024-11-29",
        "columns": "B:P",
        "header_row": 16,
        "nrows":763,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
      
      "Araqum HM-025 +Артикул.xlsx": {
        "number": "HM-025",
        "date": "2024-12-03",
        "columns": "B:P",
        "header_row": 16,
        "nrows":146,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
      
       "Araqum HM-026 +Артикул.xlsx": {
        "number": "HM-026",
        "date": "2024-12-16",
        "columns": "B:P",
        "header_row": 16,
        "nrows":230,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
       
       "Araqum_HM-009.xlsx": {
        "number": "HM-009",
        "date": "2024-08-27",
        "columns": "B:O",
        "header_row": 16,
        "nrows":5550,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
       
       "Copy of Araqum HM-015 последний 2.xlsx": {
        "number": "HM-015",
        "date": "2024-10-22",
        "columns": "B:O",
        "header_row": 16,
        "nrows":150,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
       
       "HM-002.xlsx": {
        "number": "HM-002",
        "date": "2024-05-10",
        "columns": "B:O",
        "header_row": 16,
        "nrows":447,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    
    "HM-003.xlsx": {
        "number": "HM-003",
        "date": "2024-05-10",
        "columns": "B:O",
        "header_row": 16,
        "nrows":558,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
    
     "WB-4. (1) (2).xlsx": {
        "number": "WB-4",
        "date": "2024-02-08",
        "columns": "B:L",
        "header_row": 16,
        "nrows":287,
        "dropna_col": "№",
        "supplier": "ЗАО «БРЕНД ДЕВЕЛОПМЕНТ»",
        "sheet": "Счет-Фактура (2)"
    },
    
    
     "WB-5. (6) (1).xlsx": {
        "number": "WB-5",
        "date": "2024-03-14",
        "columns": "B:L",
        "header_row": 16,
        "nrows":324,
        "dropna_col": "№",
        "supplier": "ЗАО «БРЕНД ДЕВЕЛОПМЕНТ»",
        "sheet": "Счет-Фактура (2)"
    },
           
}


for filename, config in UPD_LIST.items():

    df = pd.read_excel(
    source_folder / filename,
    sheet_name=config["sheet"],
    skiprows=config["header_row"],
    usecols=config["columns"],
    nrows=config["nrows"],
    dtype=str,
    )
    df.columns = df.columns.astype(str).str.strip()
    df = df.dropna(subset=[config["dropna_col"]])
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    print(df.columns)
    df['file_name'] = filename
    df['number'] = config['number']
    df['date']=config['date']
    df['supplier']=config['supplier']
    
    output_file = upd_path / f"{Path(filename).stem}.parquet"
    df.to_parquet(output_file, index=False)

    print(f"Saved: {output_file} | rows: {len(df)}")
    
    
    
    
       