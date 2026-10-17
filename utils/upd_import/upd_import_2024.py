# ЭТО 2024 ГОД
import pandas as pd

from pathlib import Path


# source_folder = Path('/Users/daria/Desktop/ТРЕНДСЕТТЕР/Бух данные/upds/2024')
source_folder = Path('/Users/daria/Desktop/ТРЕНДСЕТТЕР/Бух данные/upds/! УПД')
base_path = Path.cwd()
upd_path = base_path / "data" / "upd_2024"
upd_path.mkdir(parents=True, exist_ok=True)

UPD_LIST = {

    "47 УПД HM-013 от 10.10.2024.xlsx": {
        "number": "HM-013",
        "date": "2024-10-10",
        "columns": "B:P",
        "header_row": 16,
        "nrows":102,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
    
     "49 УПД HM-015 от 22.10.2024.xlsx": {
        "number": "HM-015",
        "date": "2024-10-22",
        "columns": "B:Q",
        "header_row": 16,
        "nrows":150,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
     
     "13 УПД HM-031 от 08.04.2025.xlsx": {
        "number": "HM-031",
        "date": "2025-04-08",
        "columns": "B:P",
        "header_row": 16,
        "nrows":530,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
     
     
      "11 УПД HM-028 от 03.02.2025.xlsx": {
        "number": "HM-028",
        "date": "2025-02-03",
        "columns": "B:P",
        "header_row": 16,
        "nrows":327,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
      
      
      "20 УПД HM-034 от 25.04.2025.xlsx": {
        "number": "HM-034",
        "date": "2025-04-25",
        "columns": "B:P",
        "header_row": 16,
        "nrows":397,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
      
       "34 УПД HM-033 от 21.04.2025.xlsx": {
        "number": "HM-033",
        "date": "2025-04-21",
        "columns": "B:P",
        "header_row": 16,
        "nrows":455,
        "dropna_col": "№",
        "supplier": "ЗАО «Арминвест»",
        "sheet": "1. Счет-Фактура"
    },
       
       "23 УПД HM-042 от 07.08.2025.xlsx": {
        "number": "HM-042",
        "date": "2025-08-07",
        "columns": "B:P",
        "header_row": 16,
        "nrows":359,
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
    df = df.rename(columns={df.columns[-1]: "Артикул"})
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
    
    
    
    
       