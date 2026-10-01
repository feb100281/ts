import os
import duckdb
from dotenv import load_dotenv

load_dotenv()
db_path = os.getenv("DUCKDB_PATH")
con = duckdb.connect(db_path)

rel = con.sql("select * from reports_stocks.stocks_by_product where date_from = '2026-05-01'").show()
## Обязталено закрывать connection or used try/except or with 