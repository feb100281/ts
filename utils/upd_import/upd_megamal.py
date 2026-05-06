import pandas as pd

from pathlib import Path

source_folder = Path('/Users/pavelustenko/Downloads/megamall')
base_path = Path.cwd()
upd_path = base_path / "data" / "megamall"
upd_path.mkdir(parents=True, exist_ok=True)

UPD_LIST = {
    
    "УПД (статус 1) № 34 от 31 марта 2026 г.xlsx": {
        "number": "34",
        "date": "2026-03-31",
        "columns": "B:BS",
        "header_row": 15,
        "nrows":1784,
        "dropna_col": "1",
        "supplier": "ООО «МЕГАМОЛСТРОЙ»",
        "sheet": "Лист_1"
    },
    "УПД (статус 1) № 51 от 29 апреля 2026 г.xlsx": {
        "number": "51",
        "date": "2026-04-29",
        "columns": "B:BS",
        "header_row": 15,
        "nrows":63,
        "dropna_col": "1",
        "supplier": "ООО «МЕГАМОЛСТРОЙ»",
        "sheet": "Лист_1"
    },
    "УПД (статус 1) № 52 от 29 апреля 2026 г.xlsx": {
        "number": "52",
        "date": "2026-04-29",
        "columns": "B:BS",
        "header_row": 15,
        "nrows":745,
        "dropna_col": "1",
        "supplier": "ООО «МЕГАМОЛСТРОЙ»",
        "sheet": "Лист_1"
    }
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
    df.columns = (
    df.columns
    .astype(str)
    .str.replace('\n', ' ', regex=False)
    .str.replace(r'\s+', ' ', regex=True)
    .str.strip()
    )
    df.columns = df.columns.astype(str).str.strip()
    df = df.dropna(subset=[config["dropna_col"]])
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    print(df.columns)
    df['file_name'] = filename
    df['number'] = config['number']
    df['date']=config['date']
    df['supplier']=config['supplier']
    print(df)
    
    output_file = upd_path / f"{Path(filename).stem}.parquet"
    df.to_parquet(output_file, index=False)

    print(f"Saved: {output_file} | rows: {len(df)}")