# gear/app/daily_sales/assistant/tools.py
"""Инструменты помощника: только ЧТЕНИЕ из DuckDB (без Postgres).

Защита:
  * подключение без ATTACH pg — персональные данные контрагентов недоступны;
  * разрешён один оператор SELECT / WITH / DESCRIBE / SHOW;
  * запрещённые слова (INSERT, DROP, ATTACH, COPY, read_csv ...) отсекаются;
  * таймаут запроса и лимит строк в ответе.
"""
from __future__ import annotations

import re
import threading

from conns import get_duckdb_conn_with_opt

SQL_TIMEOUT_SEC = 25
MAX_ROWS = 200
MAX_CHARS = 20_000

ALLOWED_SCHEMAS = ("sales", "stocks", "inventories", "cards", "ads")

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|create|drop|alter|truncate|attach|detach|"
    r"copy|export|import|install|load|pragma|set|reset|call|checkpoint|vacuum|"
    r"use|grant|revoke|begin|commit|rollback)\b"
    r"|\b(read_csv\w*|read_parquet|read_json\w*|read_text|read_blob|glob|"
    r"parquet_scan|csv_scan|getenv|duckdb_secrets)\s*\(",
    re.IGNORECASE,
)


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", " ", sql)


def check_sql(sql: str) -> str:
    clean = _strip_comments(sql or "").strip().rstrip(";").strip()
    if not clean:
        raise ValueError("Пустой запрос")
    if ";" in clean:
        raise ValueError("Разрешён только один запрос без ';'")
    if not re.match(r"^(select|with|describe|show|summarize)\b", clean, re.I):
        raise ValueError("Разрешены только SELECT / WITH / DESCRIBE / SHOW")
    if _FORBIDDEN.search(clean):
        raise ValueError("Запрос содержит запрещённую операцию")
    if re.search(r"\bpg\.", clean, re.I):
        raise ValueError("Доступ к Postgres (pg.*) закрыт")
    return clean


def _run(sql: str, params=None):
    with get_duckdb_conn_with_opt(with_pg=False) as con:
        timer = threading.Timer(SQL_TIMEOUT_SEC, con.interrupt)
        timer.start()
        try:
            cur = con.execute(sql, params or [])
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(MAX_ROWS + 1)
        finally:
            timer.cancel()
    return cols, rows


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v).replace("\t", " ").replace("\n", " ")


def _table_text(cols, rows) -> str:
    more = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    lines = ["\t".join(cols)] + ["\t".join(_fmt(v) for v in r) for r in rows]
    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n…(обрезано)"
    if more:
        text += f"\n…показаны первые {MAX_ROWS} строк — агрегируй сильнее"
    return text or "(пусто)"


# ---------------------------------------------------------------- tools
def list_tables(schema: str | None = None) -> str:
    schemas = [schema] if schema in ALLOWED_SCHEMAS else list(ALLOWED_SCHEMAS)
    ph = ",".join("?" * len(schemas))
    cols, rows = _run(
        f"""SELECT table_schema || '.' || table_name AS t, table_type
            FROM information_schema.tables
            WHERE table_schema IN ({ph}) ORDER BY 1""",
        schemas,
    )
    return _table_text(cols, rows)


def describe_table(table: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*", table or "", re.I):
        return "Ошибка: укажи таблицу как schema.table"
    schema, name = table.split(".")
    if schema not in ALLOWED_SCHEMAS:
        return f"Ошибка: доступны схемы {', '.join(ALLOWED_SCHEMAS)}"
    cols, rows = _run(
        """SELECT column_name, data_type FROM information_schema.columns
           WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position""",
        [schema, name],
    )
    if not rows:
        return "Таблица не найдена"
    sample_cols, sample = _run(f"SELECT * FROM {schema}.{name} LIMIT 3")
    return (_table_text(cols, rows) + "\n\nПример строк:\n"
            + _table_text(sample_cols, sample))


def run_sql(sql: str) -> str:
    clean = check_sql(sql)
    cols, rows = _run(clean)
    return _table_text(cols, rows)


TOOLS = [
    {
        "name": "list_tables",
        "description": "Список таблиц аналитической базы. Схемы: "
                       + ", ".join(ALLOWED_SCHEMAS),
        "input_schema": {
            "type": "object",
            "properties": {"schema": {"type": "string",
                                      "enum": list(ALLOWED_SCHEMAS)}},
        },
    },
    {
        "name": "describe_table",
        "description": "Колонки таблицы и 3 строки примера. Вызывай перед "
                       "первым запросом к незнакомой таблице.",
        "input_schema": {
            "type": "object",
            "properties": {"table": {"type": "string",
                                     "description": "schema.table"}},
            "required": ["table"],
        },
    },
    {
        "name": "run_sql",
        "description": "Выполнить ОДИН запрос DuckDB только на чтение "
                       "(SELECT/WITH). Возвращает до 200 строк — агрегируй "
                       "в SQL, не выгружай сырые строки.",
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    },
]

TOOLS.append({
    "name": "pl_report",
    "description": "Управленческий P&L по методике мэн пака (официальные цифры): "
                   "выручка без НДС, себестоимость FIFO, комиссия, разделы затрат, "
                   "маржинальный доход, КМД, результат до налога, чистая прибыль, "
                   "ТБУ (с конв. займами и без), запас прочности — по месяцам. "
                   "Используй для любых вопросов о прибыли, марже, затратах, ТБУ. "
                   "Первый вызов может идти до минуты, дальше быстро (кэш).",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "YYYY-MM-DD, начало периода"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD, конец периода"},
            "detail": {"type": "string", "enum": ["summary", "full"],
                       "description": "summary — итоговые показатели; "
                                      "full — плюс все статьи P&L"},
        },
    },
})


TOOLS.append({
    "name": "export_excel",
    "description": "Сформировать Excel-файл (оформление как в мэн паке) и дать "
                   "пользователю кнопку скачивания. Либо sql — запрос на чтение "
                   "(до 100 000 строк; давай колонкам понятные русские алиасы), "
                   "либо pl — P&L мэн пака по месяцам, либо margin — маржинальность "
                   "(те же параметры, что у margin_report), либо wb_sales — продажи как на "
                   "сайте WB (те же параметры, что у инструмента wb_sales). Вызывай, когда просят "
                   "файл / Excel / выгрузку или таблица больше ~30 строк.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Короткое название отчёта"},
            "description": {"type": "string", "description": "Что в файле, период"},
            "sql": {"type": "string"},
            "wb_sales": {"type": "object", "properties": {
                "date_from": {"type": "string"}, "date_to": {"type": "string"},
                "level": {"type": "string"},
                "brands": {"type": "array", "items": {"type": "string"}}}},
            "cards_check": {"type": "object", "properties": {
                "report_date": {"type": "string"}}},
            "margin": {"type": "object", "properties": {
                "date_from": {"type": "string"}, "date_to": {"type": "string"},
                "group_by": {"type": "string"}, "search": {"type": "string"},
                "only_loss": {"type": "boolean"}}},
            "pl": {"type": "object", "properties": {
                "date_from": {"type": "string"}, "date_to": {"type": "string"},
                "detail": {"type": "string", "enum": ["summary", "full"]}}},
        },
        "required": ["title"],
    },
})


TOOLS.append({
    "name": "margin_report",
    "description": "Маржинальность продаж по методике мэн пака в разрезе бренда, "
                   "категории, пола, бренд×категория, артикула или итого. "
                   "МД1 = выручка без НДС − себестоимость FIFO − комиссия; "
                   "МД2 = МД1 − расходы WB (логистика, хранение, приёмка, штрафы, "
                   "лояльность) − продвижение. МД2 < 0 — продажи в УБЫТОК. "
                   "Сортировка от худших. Используй для вопросов о марже, "
                   "рентабельности, что продаётся в убыток. Первый вызов до минуты.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "YYYY-MM-DD; по умолчанию начало текущего месяца. Для одного дня — тот же день, что date_to"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD; по умолчанию вчера"},
            "group_by": {"type": "string",
                         "enum": ["brand", "category", "gender", "brand_category",
                                  "article", "total"]},
            "search": {"type": "string",
                       "description": "Фильтр по подстроке в категории, бренде или "
                                      "наименовании, например «худи»"},
            "only_loss": {"type": "boolean", "description": "Только убыточные строки"},
            "top": {"type": "integer", "description": "Сколько строк вернуть (до 200)"},
        },
    },
})


TOOLS.append({
    "name": "wb_sales",
    "description": "Продажи и возвраты «как на сайте WB» (отчёт реализации, с НДС): "
                   "продажи/возвраты/итого в штуках, сумма до СПП, после СПП, "
                   "к перечислению, коррекции WB, доля возвратов. Возврат — строка "
                   "с типом документа «Возврат» без коррекций. ВСЕГДА используй этот "
                   "инструмент для штук, возвратов и выручки как на сайте — не SQL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD"},
            "level": {"type": "string",
                      "enum": ["day", "brand", "brand_day", "category", "nm",
                               "nm_day", "size", "detail"],
                      "description": "Детализация; итог за период — brand или category"},
            "brands": {"type": "array", "items": {"type": "string"},
                       "description": "Фильтр брендов (как в справочнике, заглавными)"},
            "top": {"type": "integer", "description": "Сколько строк вернуть (до 200)"},
            "sort_by": {"type": "string",
                        "description": "Колонка для сортировки по убыванию, напр. "
                                       "«Возвраты, шт» или «До СПП: итого, ₽»"},
        },
        "required": ["date_from", "date_to"],
    },
})


def _wb_sales(a):
    from datetime import date
    from ..wb_sales_export import fetch, LEVELS
    level = a.get("level") if a.get("level") in LEVELS else "brand"
    start = date.fromisoformat(str(a["date_from"])[:10])
    end = date.fromisoformat(str(a["date_to"])[:10])
    df = fetch(start, end, level, [b.upper() for b in a.get("brands") or []])
    if df.empty:
        return f"Нет продаж за {start:%d.%m.%Y}–{end:%d.%m.%Y}."
    num = df.select_dtypes("number").columns
    tot = df[[c for c in num if c.endswith(", шт") or c.endswith(", ₽")
              and not c.startswith("Средняя")]].sum()
    if a.get("sort_by") in df.columns:
        df = df.sort_values(a["sort_by"], ascending=False)
    view = df.head(min(int(a.get("top") or 50), 200))
    lines = ["\t".join(view.columns)]
    for r in view.itertuples(index=False):
        lines.append("\t".join(
            "" if v is None or (isinstance(v, float) and v != v)
            else (f"{v:,.1f}" if isinstance(v, float) else str(v)).replace(",", " ")
            for v in r))
    totals = "; ".join(f"{k} {v:,.0f}".replace(",", " ") for k, v in tot.items())
    return ("\n".join(lines)
            + f"\nСтрок всего: {len(df)} (показано {len(view)}). ИТОГО за "
              f"{start:%d.%m.%Y}–{end:%d.%m.%Y}: {totals}. "
              "Продажа/возврат — по типу документа WB без коррекций; коррекции — отдельно.")


TOOLS.append({
    "name": "counterparty_info",
    "description": "Справка по контрагенту и его договорам: тип и группа "
                   "контрагента, ОКВЭД, риски, список договоров (тип, номер, дата, "
                   "наша компания, валюта, подписан ли, статья, предмет). Поиск по "
                   "названию или ИНН. Платежей и сумм здесь нет.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string",
                                 "description": "Название, часть названия или ИНН"}},
        "required": ["query"],
    },
})


TOOLS.append({
    "name": "cf_report",
    "description": "ДДС (движение денег) — те же данные, что лист Cash Flow мэн пака: "
                   "поступления, выплаты, сальдо по статьям, подстатьям, контрагентам, "
                   "договорам, месяцам или дням; первая/последняя дата операции. "
                   "operations=true — список последних операций (для вопросов «когда "
                   "последний раз платили …»). search — фильтр по контрагенту, договору "
                   "или статье. direction: in — поступления, out — выплаты.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD"},
            "group_by": {"type": "string", "enum": ["month", "day", "activity", "item",
                                                    "subitem", "counterparty", "contract"]},
            "search": {"type": "string"},
            "direction": {"type": "string", "enum": ["all", "in", "out"]},
            "operations": {"type": "boolean"},
            "top": {"type": "integer"},
        },
    },
})


TOOLS.append({
    "name": "interest_report",
    "description": "Начисленные проценты по кредитам и займам за период — в ОБЕ "
                   "стороны: к уплате (мы заёмщик, расход, раздел 8 P&L) и к получению "
                   "(мы займодавец, доход). По контрагентам и договорам с типом "
                   "договора (кредит, заём, конвертируемый заём). Метод начисления.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD"},
            "direction": {"type": "string", "enum": ["all", "pay", "receive"]},
        },
    },
})


TOOLS.append({
    "name": "cash_report",
    "description": "Сколько денег: остатки по банковским счетам (по валютам, "
                   "действующие/закрытые), бессрочные депозиты, баланс личного "
                   "кабинета WB (с деньгами в пути), итог в рублях — как лист «Остатки "
                   "ДС» мэн пака; плюс Cash Flow: остаток на начало и конец каждого "
                   "месяца. Показывает, по какую дату загружены данные.",
    "input_schema": {
        "type": "object",
        "properties": {
            "as_of": {"type": "string", "description": "YYYY-MM-DD, по умолчанию сегодня"},
            "months": {"type": "integer", "description": "Сколько месяцев Cash Flow (по умолчанию 6)"},
        },
    },
})


TOOLS.append({
    "name": "wb_payouts_report",
    "description": "Поступления денег от Wildberries на расчётный счёт за период — "
                   "как лист «Поступления от WB» мэн пака: сколько поступило, сколько "
                   "выведено с баланса WB, деньги в пути, срок зачисления, список "
                   "поступлений с датой вывода. Это кассовые деньги, не продажи.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD"},
            "details": {"type": "boolean", "description": "Показать список поступлений"},
        },
    },
})


def _wb_payouts(a):
    from .wb_payouts import wb_payouts_report
    return wb_payouts_report(a.get("date_from"), a.get("date_to"), a.get("details", True))


def _cash(a):
    from .treasury import cash_report
    return cash_report(a.get("as_of"), a.get("months", 6))


def _interest(a):
    from .interest import interest_report
    return interest_report(a.get("date_from"), a.get("date_to"), a.get("direction", "all"))


def _cf(a):
    from .cashflow import cf_report
    return cf_report(a.get("date_from"), a.get("date_to"), a.get("group_by", "item"),
                     a.get("search"), a.get("direction", "all"), a.get("top", 30),
                     bool(a.get("operations")))


def _counterparty(a):
    from .counterparties import counterparty_info
    return counterparty_info(a.get("query", ""))


TOOLS.append({
    "name": "cards_check",
    "description": "Проверка карточек товаров С ОСТАТКОМ на требования WB: GTIN "
                   "(штрихкоды, маркировка), ТН ВЭД, декларации/сертификаты (номер, срок), "
                   "ОКПД2. Уровни: «Критично» и «Проверить». view: summary — сводка, "
                   "brand — по брендам, issues — список проблемных размеров.",
    "input_schema": {
        "type": "object",
        "properties": {
            "report_date": {"type": "string", "description": "Дата остатков YYYY-MM-DD, по умолчанию вчера"},
            "view": {"type": "string", "enum": ["summary", "brand", "issues"]},
            "brand": {"type": "string"},
            "level": {"type": "string", "enum": ["Критично", "Проверить"]},
            "check": {"type": "string", "enum": ["gtin", "tnved", "doc", "okpd"]},
            "top": {"type": "integer"},
        },
    },
})


TOOLS.append({
    "name": "stocks_report",
    "description": "Товарные остатки в штуках — ВСЕ места сразу: склады WB, в пути к "
                   "клиенту, в пути от клиента, наш склад FBS и итог. Используй для любых "
                   "вопросов «сколько товара на остатке / на складе / в пути / на FBS». "
                   "by: total — только итог, brand — по брендам, category — по категориям, "
                   "article — по артикулам, warehouse — по складам WB.",
    "input_schema": {
        "type": "object",
        "properties": {
            "report_date": {"type": "string",
                            "description": "Дата остатков YYYY-MM-DD, по умолчанию вчера"},
            "by": {"type": "string",
                   "enum": ["total", "brand", "category", "article", "warehouse"]},
            "brand": {"type": "string", "description": "Фильтр по бренду (часть названия)"},
            "top": {"type": "integer", "description": "Сколько строк, по умолчанию 30"},
        },
    },
})


def _stocks(a):
    from .stocks import stocks_report
    return stocks_report(a.get("report_date"), a.get("by", "total"), a.get("brand"),
                         a.get("top", 30))


TOOLS.append({
    "name": "incidents_report",
    "description": "Происшествия на складах WB (пожары и др.): где, когда и сколько товара "
                   "было на складе на день до события — штуки, карточки, бухгалтерская и "
                   "управленческая стоимость. Для вопросов про пожары, инциденты, ущерб.",
    "input_schema": {
        "type": "object",
        "properties": {"warehouse": {"type": "string",
                                     "description": "Склад (часть названия), необязательно"}},
    },
})
TOOLS.append({
    "name": "fbs_orders_report",
    "description": "Заказы FBS (сборка на нашем складе): всего, закрыто, отменено, сколько "
                   "сейчас на сборке и сколько из них за нормативом WB (48 ч), доля в "
                   "нормативе, сроки. view: summary — сводка, overdue — список просроченных "
                   "заказов, daily — динамика по дням. Период — по дате создания заказа, "
                   "по умолчанию последние 30 дней.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_from": {"type": "string", "description": "YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "YYYY-MM-DD"},
            "brand": {"type": "string", "description": "Точное название бренда"},
            "view": {"type": "string", "enum": ["summary", "overdue", "daily"]},
            "top": {"type": "integer"},
        },
    },
})


def _incidents(a):
    from .ops import incidents_report
    return incidents_report(a.get("warehouse"))


def _fbs(a):
    from .ops import fbs_orders_report
    return fbs_orders_report(a.get("date_from"), a.get("date_to"), a.get("brand"),
                             a.get("view", "summary"), a.get("top", 20))


def _cards(a):
    from .cards import cards_check
    return cards_check(a.get("report_date"), a.get("view", "summary"), a.get("brand"),
                       a.get("level"), a.get("check"), a.get("top", 40))


def _margin(a):
    from .margin import margin_report
    return margin_report(a.get("date_from"), a.get("date_to"),
                         a.get("group_by", "brand"), a.get("search"),
                         bool(a.get("only_loss")), min(int(a.get("top") or 50), 200))


def _pl(a):
    from .pl import pl_report
    return pl_report(a.get("date_from"), a.get("date_to"), a.get("detail", "summary"))


_DISPATCH = {
    "cards_check": _cards,
    "stocks_report": _stocks,
    "incidents_report": _incidents,
    "fbs_orders_report": _fbs,
    "wb_payouts_report": _wb_payouts,
    "cash_report": _cash,
    "interest_report": _interest,
    "cf_report": _cf,
    "counterparty_info": _counterparty,
    "wb_sales": _wb_sales,
    "margin_report": _margin,
    "pl_report": _pl,
    "list_tables": lambda a: list_tables(a.get("schema")),
    "describe_table": lambda a: describe_table(a.get("table", "")),
    "run_sql": lambda a: run_sql(a.get("sql", "")),
}


def call_tool(name: str, args: dict) -> tuple[str, bool]:
    """Возвращает (текст результата, is_error)."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return f"Неизвестный инструмент {name}", True
    try:
        return fn(args or {}), False
    except Exception as e:  # ошибка уходит модели, она поправит запрос
        return f"Ошибка: {type(e).__name__}: {e}"[:2000], True


def _fin(name, desc, props=None):
    TOOLS.append({"name": name, "description": desc,
                  "input_schema": {"type": "object", "properties": props or {}}})


_MONTH = {"month": {"type": "string", "description": "Любая дата месяца, YYYY-MM-DD"}}
_fin("loans_report",
     "Займы и кредиты на дату: кто кому должен, основной долг, начисленные проценты, "
     "ставка, срок погашения — по договорам, отдельно «мы должны» и «нам должны».",
     {"as_of": {"type": "string", "description": "YYYY-MM-DD, по умолчанию сегодня"}})
_fin("fx_report",
     "Курсы валют из базы компании (USD, EUR, CNY, AMD): курс, изменение за месяц и с "
     "начала года, ключевая ставка ЦБ.", _MONTH)
_fin("upd_report",
     "Приходы товара (УПД) за месяц: количество, бухгалтерская и управленческая "
     "стоимость без НДС, разница; по брендам или по документам.",
     {**_MONTH, "by": {"type": "string", "enum": ["brand", "document"]}})
_fin("month_conclusions",
     "Готовые выводы за месяц для собственника (лист «Выводы» мэн пака): результат, "
     "точка безубыточности, отклонения, прогноз.", _MONTH)


_fin("scenario_report",
     "Прогноз «что будет, если»: пересчёт прибыли и точки безубыточности среднего месяца "
     "при изменении выручки, КМД и постоянных затрат. Используй для вопросов «сколько надо "
     "продавать», «что если выручка вырастет на 20%», «выдержим ли нового сотрудника».",
     {**_MONTH,
      "base": {"type": "string", "enum": ["1", "3", "6", "me"],
               "description": "База: среднее за 3 (по умолчанию) или 6 полных месяцев, "
                              "1 — последний полный, me — выбранный месяц"},
      "revenue_pct": {"type": "number", "description": "Изменение выручки, %"},
      "kmd_pp": {"type": "number", "description": "Изменение КМД, процентных пунктов"},
      "fixed_add": {"type": "number", "description": "Рост постоянных затрат, ₽ в месяц"},
      "ex_conv": {"type": "boolean",
                  "description": "true — без процентов по конвертируемым займам"}})
_fin("profit_vs_cash_report",
     "Сопоставление прибыли (P&L, начисление) и денежного потока (ДДС) за месяц одной "
     "таблицей: итог, выручка и поступления WB, проценты, налог, товар, ДДС по видам "
     "деятельности. Для вопросов «почему прибыль есть, а денег нет» и наоборот.", _MONTH)
_fin("contracts_ending_report",
     "Договоры, срок действия которых заканчивается в указанном месяце.", _MONTH)


def _fx_tool(fn_name):
    def run(a):
        from . import finance_extra
        fn = getattr(finance_extra, fn_name)
        if fn_name == "loans_report":
            return fn(a.get("as_of"))
        if fn_name == "scenario_report":
            return fn(a.get("month"), a.get("base", "3"), a.get("revenue_pct", 0),
                      a.get("kmd_pp", 0), a.get("fixed_add", 0), a.get("ex_conv", False))
        if fn_name == "upd_report":
            return fn(a.get("month"), a.get("by", "brand"))
        return fn(a.get("month"))
    return run


# Группы инструментов — чтобы потом развести помощников:
# продажи/маркетинг и финансы (управленка, контрагенты, договоры).
SALES_TOOLS = {"list_tables", "describe_table", "run_sql", "export_excel",
               "wb_sales", "margin_report", "cards_check", "stocks_report",
               "incidents_report", "fbs_orders_report"}
FINANCE_TOOLS = {"pl_report", "counterparty_info", "cf_report", "interest_report",
                 "cash_report", "wb_payouts_report", "loans_report", "fx_report",
                 "upd_report", "month_conclusions", "scenario_report",
                 "contracts_ending_report", "profit_vs_cash_report"}
for _n in ("loans_report", "fx_report", "upd_report", "month_conclusions", "scenario_report",
           "contracts_ending_report", "profit_vs_cash_report"):
    _DISPATCH[_n] = _fx_tool(_n)


def tools_for(profile: str = "sales") -> list:
    """Инструменты профиля: finance видит всё, sales — только продажи."""
    if profile == "finance":
        return TOOLS
    return [t for t in TOOLS if t["name"] in SALES_TOOLS]


def allowed(profile: str, name: str) -> bool:
    return profile == "finance" or name in SALES_TOOLS
