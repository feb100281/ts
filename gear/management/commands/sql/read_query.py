# gear/management/commands/sql/read_query.py
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def ensure_pl_src(con) -> bool:
    """Временное представление pl_src: pl_for_csv + зарплата по начислению из ЗУП.

    Без файлов data/zup/*.parquet — просто pl_for_csv (кассовый метод).
    Возвращает True, если данные ЗУП подключены.
    """
    from django.conf import settings
    zup = Path(settings.BASE_DIR) / "data" / "zup"
    pay, con_f = zup / "payroll.parquet", zup / "contributions.parquet"
    if pay.exists() and con_f.exists():
        try:
            con.execute(read_sql("pl_src.txt")
                        .replace("{payroll}", str(pay).replace("'", "''"))
                        .replace("{contrib}", str(con_f).replace("'", "''")))
            return True
        except Exception as e:
            print(f"[pl_src] ЗУП не подключён, кассовый метод: {type(e).__name__}: {e}",
                  flush=True)
    con.execute("CREATE OR REPLACE TEMP VIEW pl_src AS SELECT * FROM pg.public.pl_for_csv")
    return False


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
wb_payouts = read_sql("wb_payouts.txt")

