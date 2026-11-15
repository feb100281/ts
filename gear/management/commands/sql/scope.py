# gear/management/commands/sql/scope.py
"""Компания пакета: группа отчётности из карточек собственников (в своей валюте или в рублях)
или консолидация.

Источники из Postgres (pl_for_csv, cf_to_csv, gl.fact, банковские счета) подменяются
временными представлениями DuckDB с отбором по компании и, для валюты компании, пересчётом сумм
по курсу ЦБ РФ на дату проводки. Все запросы идут через ScopedCon, который делает подмену.
"""
from __future__ import annotations

RU_GROUP = "Трендсеттер РФ"
DEFAULT = "ru"
ALL = "all"
LEGACY = {"am_rub": "Армения|RUB", "am_amd": "Армения|AMD"}

CURRENCY_NAMES = {"RUB": "рубли", "AMD": "драмы", "KZT": "тенге", "USD": "доллары",
                  "EUR": "евро", "CNY": "юани", "KGS": "сомы", "UZS": "сумы",
                  "AZN": "манаты", "AED": "дирхамы", "GEL": "лари", "BYN": "бел. рубли"}
CURRENCY_TITLES = {"RUB": "Российский рубль (RUB)", "AMD": "Армянский драм (AMD)",
                   "KZT": "Казахстанский тенге (KZT)", "USD": "Доллар США (USD)",
                   "EUR": "Евро (EUR)", "CNY": "Китайский юань (CNY)", "KGS": "Киргизский сом (KGS)",
                   "UZS": "Узбекский сум (UZS)", "AZN": "Азербайджанский манат (AZN)",
                   "AED": "Дирхам ОАЭ (AED)"}
CURRENCY_SIGNS = {"RUB": "₽", "AMD": "֏", "KZT": "₸", "USD": "$", "EUR": "€", "CNY": "¥",
                  "KGS": "сом", "UZS": "сум", "AZN": "₼", "AED": "AED"}
CURRENCY_PREP = {"AMD": "драмах", "KZT": "тенге", "USD": "долларах", "EUR": "евро",
                 "CNY": "юанях", "KGS": "сомах", "UZS": "сумах", "AZN": "манатах", "AED": "дирхамах"}
CURRENCY_DATA = {"RUB": "в российских рублях (RUB)", "AMD": "в армянских драмах (AMD)",
                 "KZT": "в тенге (KZT)", "USD": "в долларах США (USD)", "EUR": "в евро (EUR)"}


def _groups():
    """Группы отчётности из карточек собственников: {группа: валюта учёта}."""
    from collections import Counter
    from corporate.models import Owners
    cur = {}
    for g, c in (Owners.objects.filter(in_reports=True).exclude(report_group="")
                 .values_list("report_group", "currency")):
        cur.setdefault(g, Counter())[(c or "RUB").upper()] += 1
    return {g: c.most_common(1)[0][0] for g, c in cur.items()}


def options():
    """Варианты выбора компании для окна выгрузки: [(ключ, подпись)]."""
    out = [(DEFAULT, RU_GROUP)]
    for g, c in sorted(_groups().items()):
        if g == RU_GROUP:
            continue
        if c != "RUB":
            out.append((f"{g}|{c}", f"{g}, {CURRENCY_NAMES.get(c, c)}"))
        out.append((f"{g}|RUB", f"{g}, рубли"))
    out.append((ALL, "Консолидация, рубли"))
    return out


def resolve(key: str | None):
    """(название, группы или None для всех, валюта)."""
    key = LEGACY.get(key, key) or DEFAULT
    if key == ALL:
        return "Консолидация", None, "RUB"
    if "|" in key:
        g, c = key.split("|", 1)
        if g and c.isalpha() and len(c) == 3:
            return g, [g], c.upper()
    return RU_GROUP, [RU_GROUP], "RUB"


def norm(key: str | None) -> str:
    name, groups, cur = resolve(key)
    if groups is None:
        return ALL
    if groups == [RU_GROUP]:
        return DEFAULT
    return f"{groups[0]}|{cur}"


def title(key: str) -> str:
    name, groups, cur = resolve(key)
    return name if groups is None or name == RU_GROUP else f"{name}, {CURRENCY_NAMES.get(cur, cur)}"


def suffix(key: str) -> str:
    """Суффикс имени файла: латиница и цифры."""
    import re
    k = norm(key)
    if k == DEFAULT:
        return ""
    tr = str.maketrans("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                       "abvgdeejziiklmnoprstufhccss_y_eua")
    return "_" + re.sub(r"[^a-z0-9]+", "_", k.lower().translate(tr)).strip("_")


def has_ru(key: str) -> bool:
    groups = resolve(key)[1]
    return groups is None or RU_GROUP in groups


def currency(key: str) -> str:
    return resolve(key)[2]


def apply(sql: str) -> str:
    for a, b in SUBST:
        sql = sql.replace(a, b)
    return sql


def prepare(con, key: str):
    """Временные представления для выбранной компании на сыром подключении."""
    key = norm(key)
    _, groups, cur = resolve(key)
    if groups is None:
        owners = "SELECT id FROM pg.public.corporate_owners"
    else:
        lst = ", ".join("'" + g.replace("'", "''") + "'" for g in groups)
        owners = f"SELECT id FROM pg.public.corporate_owners WHERE report_group IN ({lst})"
    con.execute(f"CREATE OR REPLACE TEMP TABLE scope_owners AS {owners}")
    ru_only = "TRUE" if has_ru(key) else "FALSE"

    if cur != "RUB":
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE scope_rate AS
            SELECT date::DATE AS d, rate::DOUBLE AS rate FROM pg.public.macro_currencyrate
            WHERE currency = '{cur}' AND base_currency = 'RUB' ORDER BY 1""")

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
