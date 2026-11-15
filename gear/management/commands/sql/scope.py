# gear/management/commands/sql/scope.py
"""Компания пакета: РФ, Армения (₽ или AMD), консолидация.

Источники из Postgres (pl_for_csv, cf_to_csv, gl.fact, банковские счета) подменяются
временными представлениями DuckDB с отбором по компании и, для AMD, пересчётом сумм
по курсу ЦБ РФ на дату проводки. Все запросы идут через ScopedCon, который делает подмену.
"""
from __future__ import annotations

RU_GROUP = "Трендсеттер РФ"

# ключ: (название, группы компаний или None для всех, валюта)
SCOPES = {
    "ru": ("Трендсеттер РФ", [RU_GROUP], "RUB"),
    "am_rub": ("Армения", ["Армения"], "RUB"),
    "am_amd": ("Армения", ["Армения"], "AMD"),
    "all": ("Консолидация", None, "RUB"),
}
DEFAULT = "ru"

# порядок важен: длинные имена раньше коротких
SUBST = [
    ("pg.public.pl_for_csv", "scope_pl_for_csv"),
    ("pg.pl_for_csv", "scope_pl_for_csv"),
    ("pg.public.cf_to_csv", "scope_cf_to_csv"),
    ("pg.cf_to_csv", "scope_cf_to_csv"),
    ("pg.gl.fact", "scope_gl_fact"),
    ("pg.public.ba_balance_csv", "scope_ba_balance_csv"),
    ("pg.ba_balance_csv", "scope_ba_balance_csv"),
    ("pg.public.corporate_bankaccount", "scope_bankaccount"),
    ("pg.corporate_bankaccount", "scope_bankaccount"),
    ("pg.public.wb_balance_for_csv", "scope_wb_balance"),
    ("pg.wb_balance_for_csv", "scope_wb_balance"),
    ("pg.public.grossbook_vatadjustment", "scope_vatadjustment"),
    ("pg.grossbook_vatadjustment", "scope_vatadjustment"),
]


def norm(key: str | None) -> str:
    return key if key in SCOPES else DEFAULT


def title(key: str) -> str:
    name, _, cur = SCOPES[norm(key)]
    return name if name != "Армения" else f"{name}, {'драмы' if cur == 'AMD' else 'рубли'}"


def suffix(key: str) -> str:
    return "" if norm(key) == DEFAULT else "_" + norm(key)


def has_ru(key: str) -> bool:
    groups = SCOPES[norm(key)][1]
    return groups is None or RU_GROUP in groups


def currency(key: str) -> str:
    return SCOPES[norm(key)][2]


def apply(sql: str) -> str:
    for a, b in SUBST:
        sql = sql.replace(a, b)
    return sql


def prepare(con, key: str):
    """Временные представления для выбранной компании на сыром подключении."""
    key = norm(key)
    _, groups, cur = SCOPES[key]
    if groups is None:
        owners = "SELECT id FROM pg.public.corporate_owners"
    else:
        lst = ", ".join("'" + g.replace("'", "''") + "'" for g in groups)
        owners = f"SELECT id FROM pg.public.corporate_owners WHERE report_group IN ({lst})"
    con.execute(f"CREATE OR REPLACE TEMP TABLE scope_owners AS {owners}")
    ru_only = "TRUE" if has_ru(key) else "FALSE"

    if cur == "AMD":
        con.execute("""
            CREATE OR REPLACE TEMP TABLE scope_rate AS
            SELECT date::DATE AS d, rate::DOUBLE AS rate FROM pg.public.macro_currencyrate
            WHERE currency = 'AMD' AND base_currency = 'RUB' ORDER BY 1""")

        def conv(src, cols, money_int=False):
            rep = ", ".join(
                (f"CAST(ROUND(t.{c} / r.rate) AS BIGINT) AS {c}" if money_int
                 else f"ROUND(t.{c} / r.rate, 2) AS {c}") for c in cols)
            return (f"SELECT t.* REPLACE ({rep}) FROM {src} t "
                    f"ASOF LEFT JOIN scope_rate r ON t.date_from::DATE >= r.d "
                    f"WHERE t.company_id IN (SELECT id FROM scope_owners)")
        pl = conv("pg.public.pl_for_csv_all", ["dt", "cr", "amount"])
        cf = conv("pg.public.cf_to_csv_all", ["dt", "cr", "amount"])
        gl = conv("pg.gl.fact", ["dt", "cr"], money_int=True)
    else:
        flt = "WHERE company_id IN (SELECT id FROM scope_owners)"
        pl = f"SELECT * FROM pg.public.pl_for_csv_all {flt}"
        cf = f"SELECT * FROM pg.public.cf_to_csv_all {flt}"
        gl = f"SELECT * FROM pg.gl.fact {flt}"

    con.execute(f"CREATE OR REPLACE TEMP VIEW scope_pl_for_csv AS {pl}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW scope_cf_to_csv AS {cf}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW scope_gl_fact AS {gl}")
    con.execute("""CREATE OR REPLACE TEMP VIEW scope_bankaccount AS
        SELECT * FROM pg.public.corporate_bankaccount WHERE corporate_id IN (SELECT id FROM scope_owners)""")
    con.execute("""CREATE OR REPLACE TEMP VIEW scope_ba_balance_csv AS
        SELECT t.* FROM pg.public.ba_balance_csv t
        WHERE t.acc_id IN (SELECT bs_acc_id FROM scope_bankaccount)""")
    con.execute(f"CREATE OR REPLACE TEMP VIEW scope_wb_balance AS "
                f"SELECT * FROM pg.public.wb_balance_for_csv WHERE {ru_only}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW scope_vatadjustment AS "
                f"SELECT * FROM pg.public.grossbook_vatadjustment WHERE {ru_only}")


class ScopedCon:
    """Подключение DuckDB, в котором все запросы читают источники выбранной компании."""

    def __init__(self, con, key: str):
        self._con = con
        self.scope = norm(key)
        prepare(con, self.scope)

    def execute(self, sql, *args, **kwargs):
        return self._con.execute(apply(sql) if isinstance(sql, str) else sql, *args, **kwargs)

    def sql(self, sql, *args, **kwargs):
        return self._con.sql(apply(sql), *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._con, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
