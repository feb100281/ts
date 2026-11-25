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
    if cur == "RUB":
        con.execute("""CREATE OR REPLACE TEMP VIEW scope_ba_balance_csv AS
            SELECT t.* FROM pg.public.ba_balance_csv t
            WHERE t.acc_id IN (SELECT bs_acc_id FROM scope_bankaccount)""")
    else:
        # счета в валюте пакета — обороты из выписок без пересчёта; прочие — из книги по курсу на дату
        con.execute(f"""CREATE OR REPLACE TEMP VIEW scope_ba_balance_csv AS
            SELECT d.date AS date_from, ba.bs_acc_id AS acc_id, c.name AS "Банковский счет",
                   ROUND(SUM(COALESCE(d.dt, 0)), 2) AS "Поступления",
                   ROUND(SUM(COALESCE(d.cr, 0)), 2) AS "Расход",
                   ROUND(SUM(COALESCE(d.dt, 0) - COALESCE(d.cr, 0)), 2) AS "Обороты"
            FROM pg.public.treasury_cfdata d
            JOIN scope_bankaccount ba ON ba.id = d.ba_id
            JOIN pg.public.corporate_coa c ON c.id = ba.bs_acc_id
            WHERE upper(ba.currency) = '{cur}' AND d.date IS NOT NULL
            GROUP BY 1, 2, 3
            UNION ALL
            SELECT t.* REPLACE (ROUND(t."Поступления" / r.rate, 2) AS "Поступления",
                                ROUND(t."Расход" / r.rate, 2) AS "Расход",
                                ROUND(t."Обороты" / r.rate, 2) AS "Обороты")
            FROM pg.public.ba_balance_csv t
            ASOF LEFT JOIN scope_rate r ON t.date_from::DATE >= r.d
            WHERE t.acc_id IN (SELECT bs_acc_id FROM scope_bankaccount WHERE upper(currency) <> '{cur}')""")
    con.execute(f"CREATE OR REPLACE TEMP TABLE scope_flags AS SELECT {ru_only} AS has_ru")
    # НДС розницы: в валюте пакета (своя валюта компании или рубли по курсу ЦБ на дату)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE scope_rates_all AS
        SELECT upper(currency) AS cur, date::DATE AS d, rate::DOUBLE AS rate
        FROM pg.public.macro_currencyrate WHERE base_currency = 'RUB' ORDER BY 1, 2""")
    to_rub = "CASE WHEN x.cur = 'RUB' THEN 1 ELSE r.rate END"
    factor = (to_rub if cur == "RUB" else
              f"CASE WHEN x.cur = '{cur}' THEN 1 ELSE {to_rub} / NULLIF(t.rate, 0) END")
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW scope_retail_vat AS
        SELECT x.d, x.co, x.kind, x.vat * {factor} AS vat
        FROM (
            SELECT s.doc_date::DATE AS d, s.kind,
                   CASE WHEN s.kind = 'sale' THEN 1 ELSE -1 END
                       * (s.amount - s.amount_novat)::DOUBLE AS vat,
                   ow.name AS co, upper(COALESCE(ow.currency, 'RUB')) AS cur
            FROM pg.public.sales_retailsale s
            JOIN pg.public.corporate_owners ow ON ow.id = s.owner_id
            WHERE s.owner_id IN (SELECT id FROM scope_owners)
        ) x
        ASOF LEFT JOIN scope_rates_all r ON r.cur = x.cur AND x.d >= r.d
        ASOF LEFT JOIN (SELECT * FROM scope_rates_all WHERE cur = '{cur}') t ON x.d >= t.d""")
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


# --- Проверки (НДС, договоры, баланс, удержания WB): отбор по компании, суммы в рублях ---

CHECK_SUBST = [
    ("pg.gl.accural_distribution", "scope_accural_distribution"),
    ("pg.public.grossbook_gladjustment", "scope_gladjustment"),
    ("pg.public.upd_income_lines", "scope_upd_lines"),
    ("pg.public.treasury_cfdata", "scope_cfdata"),
    ("pg.wb_dwh.realization_kv", "scope_realization_kv"),
    ("inventories.inv_gl", "scope_inv_gl"),
]


def check_options():
    """Компании для проверок: только рублёвые варианты."""
    return [(k, t) for k, t in options() if k in (DEFAULT, ALL) or k.endswith("|RUB")]


def check_key(key: str | None) -> str:
    """Ключ проверки всегда в рублях: учёт договоров и НДС ведётся в рублях."""
    _, groups, _ = resolve(key)
    if groups is None:
        return ALL
    return DEFAULT if groups == [RU_GROUP] else f"{groups[0]}|RUB"


def prepare_checks(con, key: str):
    key = check_key(key)
    prepare(con, key)
    if resolve(key)[1] is None:
        for src, dst in CHECK_SUBST:
            con.execute(f"CREATE OR REPLACE TEMP VIEW {dst} AS SELECT * FROM {src}")
        return
    ru = "TRUE" if has_ru(key) else "FALSE"
    con.execute("""CREATE OR REPLACE TEMP TABLE scope_contracts AS
        SELECT id FROM pg.public.contracts_contracts WHERE owner_id IN (SELECT id FROM scope_owners)""")
    con.execute(f"""CREATE OR REPLACE TEMP VIEW scope_accural_distribution AS
        SELECT * FROM pg.gl.accural_distribution
        WHERE contract_id IN (SELECT id FROM scope_contracts) OR (contract_id IS NULL AND {ru})""")
    con.execute("""CREATE OR REPLACE TEMP VIEW scope_gladjustment AS
        SELECT * FROM pg.public.grossbook_gladjustment WHERE owner_id IN (SELECT id FROM scope_owners)""")
    con.execute(f"""CREATE OR REPLACE TEMP VIEW scope_upd_lines AS
        SELECT l.* FROM pg.public.upd_income_lines l
        JOIN pg.public.cards_upddocument d ON d.id = l.upd_document_id
        WHERE d.contract_id IN (SELECT id FROM scope_contracts) OR (d.contract_id IS NULL AND {ru})""")
    con.execute("""CREATE OR REPLACE TEMP VIEW scope_cfdata AS
        SELECT * FROM pg.public.treasury_cfdata WHERE ba_id IN (SELECT id FROM scope_bankaccount)""")
    con.execute(f"CREATE OR REPLACE TEMP VIEW scope_realization_kv AS "
                f"SELECT * FROM pg.wb_dwh.realization_kv WHERE {ru}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW scope_inv_gl AS "
                f"SELECT * FROM inventories.inv_gl WHERE {ru}")


class CheckCon(ScopedCon):
    """Подключение для проверок: источники выбранной компании, суммы в рублях."""

    def __init__(self, con, key: str):
        self._con = con
        self.scope = check_key(key)
        prepare_checks(con, self.scope)

    @staticmethod
    def _sql(sql):
        if not isinstance(sql, str):
            return sql
        for a, b in CHECK_SUBST:
            sql = sql.replace(a, b)
        return apply(sql)

    def execute(self, sql, *args, **kwargs):
        return self._con.execute(self._sql(sql), *args, **kwargs)

    def sql(self, sql, *args, **kwargs):
        return self._con.sql(self._sql(sql), *args, **kwargs)
