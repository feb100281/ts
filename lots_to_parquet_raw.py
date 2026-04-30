import pandas as pd
from pprint import pprint
import paramiko
from dotenv import load_dotenv
import os
import tempfile
from pathlib import Path


load_dotenv()

host = "82.202.197.94"
user = os.getenv("SERVER_USER")
psw = os.getenv("SERVER_PSW")

server_path = '/home/daria/ts/data/lots/raws'

# Пути к файлам комментим иначе git конфликт
# '/Users/pavelustenko/Downloads/lots/03 Расчет себестоимости H&M 3 лот (3 LOT CALCULATION COST AND BREAK-EVEN POINT).xlsx'

def get_xls_file(file):
    xls = pd.ExcelFile(file)
    pprint(xls.sheet_names)
    return  xls

def get_df(xls: pd.ExcelFile, sheet, skipheader=0, skipfooter=0, cols=None):
    df = xls.parse(
        sheet_name=sheet,
        dtype=str,
        skiprows=skipheader,
        skipfooter=skipfooter,
        usecols=cols
    )

    # 🔥 удаляем Unnamed колонки
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    return df

def send_parquet_to_server(
    df: pd.DataFrame,
    remote_dir: str,
    remote_filename: str,
    host: str,
    user: str,
    password: str,
    port: int = 22,
):
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        local_path = tmp.name

    # сохраняем parquet локально
    df.to_parquet(local_path, engine="pyarrow", index=False)

    remote_path = f"{remote_dir.rstrip('/')}/{remote_filename}"

    transport = paramiko.Transport((host, port))
    transport.connect(username=user, password=password)

    sftp = paramiko.SFTPClient.from_transport(transport)

    try:
        # если папки нет — создаст ошибку
        sftp.put(local_path, remote_path)
        print(f"Uploaded: {remote_path}")
    finally:
        sftp.close()
        transport.close()
        Path(local_path).unlink(missing_ok=True)
    
    
    
        


xls = get_xls_file('/Users/pavelustenko/Downloads/lots/03 Расчет себестоимости H&M 3 лот (3 LOT CALCULATION COST AND BREAK-EVEN POINT).xlsx')




