# gear/management/commands/sql/read_query.py
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


base = read_sql("base.txt")
base_stocks = read_sql("base_stocks.txt")
wb_costs = read_sql("wb_costs.txt")
dayly_sales_agg = read_sql("dayly_sales_agg.txt")
margin = read_sql("margin.txt")
opex = read_sql("opex.txt")
cf = read_sql("cf.txt")
treasury = read_sql("treasury.txt")
deposits = read_sql("deposits.txt")
pl_notes = read_sql("pl_notes.txt")

