import pandas as pd

from pathlib import Path


source_folder = Path('/Users/pavelustenko/Downloads/import_xlsx/2025')
base_path = Path.cwd()
upd_path = base_path / "data" / "upd"
upd_path.mkdir(parents=True, exist_ok=True)

UPD_LIST = {

    "Araqum MS-004 +Артикул (2).xlsx": {
        "number": "MS-004",
        "date": "2025-04-10",
        "columns": "B:O",
        "header_row": 16,
        "nrows":4259,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum MS-001 +Артикул (2) (1) (1).xlsx": {
        "number": "MS-001",
        "date": "2025-03-18",
        "columns": "B:O",
        "header_row": 16,
        "nrows":3585,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum HM-041 +Артикул.xlsx": {
        "number": "HM-041",
        "date": "2025-07-01",
        "columns": "B:O",
        "header_row": 16,
        "nrows":150,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum MS-003 +Артикул (1).xlsx": {
        "number": "MS-003",
        "date": "2025-04-02",
        "columns": "B:O",
        "header_row": 16,
        "nrows":2616,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum HM-036 +Артикул.xlsx": {
        "number": "HM-036",
        "date": "2025-05-21",
        "columns": "B:O",
        "header_row": 16,
        "nrows":275,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum HM-031 +Артикул.xlsx": {
        "number": "HM-031",
        "date": "2025-04-08",
        "columns": "B:O",
        "header_row": 16,
        "nrows":530,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum HM-032 +Артикул (2).xlsx": {
        "number": "HM-032",
        "date": "2025-04-10",
        "columns": "B:O",
        "header_row": 16,
        "nrows":253,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
     "Araqum HM-045.xlsx": {
        "number": "HM-045",
        "date": "2025-11-11",
        "columns": "B:O",
        "header_row": 16,
        "nrows":1939,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum HM-044.xlsx": {
        "number": "HM-044",
        "date": "2025-10-06",
        "columns": "B:O",
        "header_row": 16,
        "nrows":210,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum MS-005 +Артикул (1) (1).xlsx": {
        "number": "MS-005",
        "date": "2025-07-01",
        "columns": "B:O",
        "header_row": 16,
        "nrows":554,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum HM-046.xlsx": {
        "number": "HM-046",
        "date": "2025-12-04",
        "columns": "B:O",
        "header_row": 16,
        "nrows":2607,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum HM-029 +Артикул.xlsx": {
        "number": "HM-029",
        "date": "2025-02-17",
        "columns": "B:O",
        "header_row": 16,
        "nrows":171,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum HM-030 +Артикул (1).xlsx": {
        "number": "HM-030",
        "date": "2025-04-02",
        "columns": "B:O",
        "header_row": 16,
        "nrows":332,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum HM-042 +Артикул (1).xlsx": {
        "number": "HM-042",
        "date": "2025-08-07",
        "columns": "B:O",
        "header_row": 16,
        "nrows":359,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum MS-002 +Артикул.xlsx": {
        "number": "MS-002",
        "date": "2025-03-26",
        "columns": "B:O",
        "header_row": 16,
        "nrows":4248,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum HM-038 +Артикул + Номер.xlsx": {
        "number": "HM-038",
        "date": "2025-06-03",
        "columns": "B:O",
        "header_row": 16,
        "nrows":77,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum MS-006 +Артикул - на отправку брокер.xlsx": {
        "number": "MS-006",
        "date": "2025-08-07",
        "columns": "B:O",
        "header_row": 16,
        "nrows":4455,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
    "Araqum HM-028 БЕЗ Артикулов 1.xlsx": {
        "number": "HM-028",
        "date": "2025-02-03",
        "columns": "B:O",
        "header_row": 16,
        "nrows":327,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
     "Araqum HM-043 +Артикул (1) (1) (1).xlsx": {
        "number": "HM-043",
        "date": "2025-08-22",
        "columns": "B:O",
        "header_row": 16,
        "nrows":4435,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    }, 
     "Araqum HM-033 +Артикул.xlsx": {
        "number": "HM-033",
        "date": "2025-04-21",
        "columns": "B:O",
        "header_row": 16,
        "nrows":455,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },  
    "Araqum HM-040 +Артикул + Номер.xlsx": {
        "number": "HM-040",
        "date": "2025-06-16",
        "columns": "B:O",
        "header_row": 16,
        "nrows":65,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },  
    "Araqum HM-034 +Артикул.xlsx": {
        "number": "HM-034",
        "date": "2025-04-25",
        "columns": "B:O",
        "header_row": 16,
        "nrows":397,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },  
    "Araqum HM-037 +Артикул + Номер (1).xlsx": {
        "number": "HM-037",
        "date": "2025-05-29",
        "columns": "B:O",
        "header_row": 16,
        "nrows":74,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum HM-035 +Артикул.xlsx": {
        "number": "HM-035",
        "date": "2025-05-20",
        "columns": "B:O",
        "header_row": 16,
        "nrows":161,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    "Araqum HM-039 +Артикул + Номер (2).xlsx": {
        "number": "HM-039",
        "date": "2025-06-10",
        "columns": "B:O",
        "header_row": 16,
        "nrows":149,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },    
    "Araqum HM-027 +Артикул.xlsx": {
        "number": "HM-027",
        "date": "2025-02-03",
        "columns": "B:O",
        "header_row": 16,
        "nrows":149,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
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
    
    
    
    
       