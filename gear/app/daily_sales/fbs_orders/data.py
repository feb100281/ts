# gear/app/daily_sales/fbs_orders/data.py
"""
Данные для анализа заказов FBS.

Источник — витрины orders.* в analytics.duckdb, которые
обновляются ежедневной загрузкой из API WB.

Важное отличие от ручных запросов по паркетам: возраст заказа
считается не от CURRENT_TIMESTAMP, а от момента, на который
сделана выгрузка (максимальный loaded_at в текущем срезе).
Иначе на вчерашнем срезе все заказы выглядят просроченными,
хотя на момент выгрузки они были в норме.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

import pandas as pd

from conns import get_duckdb_conn_with_opt

from .config import (
    CANCELLED_WB_STATUSES,
    HOUR_BUCKETS,
    HOUR_BUCKET_OVERFLOW,
    IN_WORK_SUPPLIER_STATUS,
    IN_WORK_WB_STATUS,
    ORDERS_SOURCES,
    SLA_LIMIT_HOURS,
    OFFICES_SOURCE,
    SUPPLIES_SOURCES,
    WAREHOUSES_SOURCE,
    warehouse_title,
)


# ============================================================
# СЛУЖЕБНОЕ
# ============================================================

def _normalize_list(value: Any) -> list[Any]:
    """Приводит одиночное значение или коллекцию к списку."""
    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    if isinstance(value, Iterable):
        return [v for v in value if v not in (None, "")]

    return [value]


def _placeholders(values) -> str:
    return ", ".join("?" for _ in values)


def _table_exists(con, qualified_name: str) -> bool:
    """
    Проверяет наличие таблицы вида schema.table.

    Нужна, чтобы страница показывала понятное сообщение,
    а не падала с BinderException, если витрину ещё не залили.
    """
    if "." in qualified_name:
        schema, table = qualified_name.split(".", 1)
    else:
        schema, table = "main", qualified_name

    row = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = ?
          AND table_name = ?
        """,
        [schema, table],
    ).fetchone()

    return bool(row and row[0])


def _pick_source(con, candidates) -> str | None:
    for name in candidates:
        if _table_exists(con, name):
            return name
    return None


def _bucket_sql(column: str) -> tuple[str, str]:
    """
    Собирает CASE-выражения для корзины часов и её порядка.

    Возвращает пару (выражение названия, выражение сортировки),
    построенную из HOUR_BUCKETS — чтобы пороги задавались
    в одном месте, а не переписывались в каждом запросе.
    """
    name_parts = []
    sort_parts = []

    for index, (limit, label) in enumerate(HOUR_BUCKETS, start=1):
        name_parts.append(
            f"WHEN {column} < {limit} THEN '{label}'"
        )
        sort_parts.append(
            f"WHEN {column} < {limit} THEN {index}"
        )

    overflow_index = len(HOUR_BUCKETS) + 1

    name_sql = (
        "CASE "
        + " ".join(name_parts)
        + f" ELSE '{HOUR_BUCKET_OVERFLOW}' END"
    )

    sort_sql = (
        "CASE "
        + " ".join(sort_parts)
        + f" ELSE {overflow_index} END"
    )

    return name_sql, sort_sql


def _cancelled_sql(alias: str = "o") -> str:
    values = ", ".join(f"'{s}'" for s in CANCELLED_WB_STATUSES)
    return f"{alias}.wb_status IN ({values})"


# ============================================================
# КОНТЕКСТ ЗАПРОСА
# ============================================================

class FbsSourceMissing(Exception):
    """Витрины заказов FBS ещё нет в базе."""


class FbsData:
    """
    Контекст работы с витринами заказов FBS.

    При входе создаётся временная таблица fbs_base — текущий
    срез заказов, обогащённый карточкой товара и рассчитанным
    возрастом заказа. Все остальные запросы читают её.
    """

    def __enter__(self) -> "FbsData":
        self.con = get_duckdb_conn_with_opt(with_pg=False)

        self.orders_source = _pick_source(self.con, ORDERS_SOURCES)
        self.supplies_source = _pick_source(self.con, SUPPLIES_SOURCES)

        if self.orders_source is None:
            self.con.close()
            raise FbsSourceMissing(
                "Витрина заказов FBS не найдена. Ожидаются таблицы: "
                + ", ".join(ORDERS_SOURCES)
            )

        self.as_of = self._resolve_as_of()
        self._load_dictionaries()
        self._init_base()

        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if getattr(self, "con", None) is not None:
            self.con.close()

    # --------------------------------------------------------
    # Справочники складов
    # --------------------------------------------------------

    def _load_dictionaries(self) -> None:
        """
        Подтягивает названия складов, если справочники залиты.

        Пустые словари — рабочее состояние: вкладка покажет
        номера складов. Это заметно хуже, но лучше, чем
        падение из-за отсутствующей таблицы.
        """
        self.warehouse_names: dict[int, str] = {}
        self.office_names: dict[int, str] = {}

        if _table_exists(self.con, WAREHOUSES_SOURCE):
            rows = self.con.execute(
                f"""
                SELECT warehouse_id, warehouse_name
                FROM {WAREHOUSES_SOURCE}
                WHERE warehouse_id IS NOT NULL
                  AND NULLIF(TRIM(warehouse_name), '') IS NOT NULL
                """
            ).fetchall()

            self.warehouse_names = {
                int(row[0]): row[1] for row in rows
            }

        if _table_exists(self.con, OFFICES_SOURCE):
            rows = self.con.execute(
                f"""
                SELECT
                    office_id,
                    office_name,
                    city
                FROM {OFFICES_SOURCE}
                WHERE office_id IS NOT NULL
                  AND NULLIF(TRIM(office_name), '') IS NOT NULL
                """
            ).fetchall()

            # Город добавляем, только если его ещё нет
            # в названии: у WB склады часто уже названы
            # «Москва_Восток», и «Москва, Москва_Восток»
            # читалось бы глупо.
            self.office_names = {}

            for office_id, name, city in rows:
                if city and city not in name:
                    label = f"{name}, {city}"
                else:
                    label = name

                self.office_names[int(office_id)] = label

    def _warehouse_label(self, value) -> str:
        """Название склада отправления или его номер."""
        try:
            key = int(value)
        except (TypeError, ValueError):
            return "Склад не указан"

        name = self.warehouse_names.get(key)

        if name:
            return name

        return warehouse_title(key)

    def _office_label(self, value) -> str:
        """Название склада WB назначения или его номер."""
        try:
            key = int(value)
        except (TypeError, ValueError):
            return "Не указан"

        return self.office_names.get(key) or f"Пункт {key}"

    def _label_places(self, data: pd.DataFrame) -> pd.DataFrame:
        """Подставляет названия складов и пунктов назначения."""
        if data is None or data.empty:
            return data

        data = data.copy()

        if "warehouse_id" in data.columns:
            data["warehouse"] = data["warehouse_id"].map(
                self._warehouse_label
            )

        if "destination_office_id" in data.columns:
            data["destination_office"] = data[
                "destination_office_id"
            ].map(self._office_label)

        return data

    # --------------------------------------------------------
    # Момент, на который актуальны данные
    # --------------------------------------------------------

    def _resolve_as_of(self) -> datetime:
        """
        Момент выгрузки текущего среза.

        Берём максимальный loaded_at — это время обращения
        к API WB. Если колонки нет или она пустая, опираемся
        на snapshot_date, а в последнюю очередь на текущее время.
        """
        row = self.con.execute(
            f"""
            SELECT
                MAX(loaded_at) AS loaded_at,
                MAX(snapshot_date) AS snapshot_date
            FROM {self.orders_source}
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date) FROM {self.orders_source}
            )
            """
        ).fetchone()

        if row is None:
            return datetime.now()

        loaded_at, snapshot_date = row

        if loaded_at is not None:
            return pd.to_datetime(loaded_at).to_pydatetime()

        if snapshot_date is not None:
            return pd.to_datetime(snapshot_date).to_pydatetime()

        return datetime.now()

    # --------------------------------------------------------
    # Пункты выдачи
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Сумма заказа
    # --------------------------------------------------------

    #: Колонки-кандидаты. True — значение уже в рублях,
    #: False — в копейках: API WB отдаёт цену умноженной на 100.
    AMOUNT_CANDIDATES = (
        ("final_price_rub", True),
        ("sale_price_rub", True),
        ("price_rub", True),
        ("converted_final_price_rub", True),
        ("converted_price_rub", True),
        ("final_price", False),
        ("sale_price", False),
        ("price", False),
        ("converted_final_price", False),
        ("converted_price", False),
    )

    def _existing_columns(self) -> set:
        schema, table = self.orders_source.split(".", 1)

        rows = self.con.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = ?
              AND table_name = ?
            """,
            [schema, table],
        ).fetchall()

        return {row[0] for row in rows}

    def _amount_expression(self):
        """
        Подбирает колонку, в которой реально лежит сумма заказа.

        В выгрузке есть и «рублёвые» колонки, и исходные поля
        API, где цена умножена на 100. Какие из них заполнены,
        зависит от того, как отработала загрузка, поэтому
        смотрим фактические данные, а не имя колонки.

        Возвращает выражение и название выбранной колонки —
        его видно в отчёте, чтобы суммы можно было проверить.
        """
        columns = self._existing_columns()

        candidates = [
            (name, in_rubles)
            for name, in_rubles in self.AMOUNT_CANDIDATES
            if name in columns
        ]

        if not candidates:
            return "0", "в выгрузке нет колонок с суммой"

        checks = ", ".join(
            f"MAX(ABS(COALESCE({name}, 0)))"
            for name, _ in candidates
        )

        row = self.con.execute(
            f"""
            SELECT {checks}
            FROM {self.orders_source}
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date)
                FROM {self.orders_source}
            )
            """
        ).fetchone()

        for (name, in_rubles), value in zip(candidates, row or []):
            if value:
                if in_rubles:
                    return f"COALESCE(o.{name}, 0)", name
                return (
                    f"COALESCE(o.{name}, 0) / 100.0",
                    f"{name} ÷ 100",
                )

        return "0", "суммы пустые во всех колонках"

    def _office_expression(self) -> str:
        """
        Выражение для названия пункта выдачи.

        В выгрузке offices может лежать и как список, и как
        JSON-строка вида ["Москва", "Москва_Восток"] — зависит
        от того, как отработала загрузка. Смотрим фактический
        тип колонки и берём подходящее выражение, а не гадаем.
        """
        schema, table = self.orders_source.split(".", 1)

        row = self.con.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = ?
              AND table_name = ?
              AND column_name = 'offices'
            """,
            [schema, table],
        ).fetchone()

        data_type = (row[0] if row else "") or ""

        if "[]" in data_type or data_type.upper().startswith("LIST"):
            first_value = "o.offices[1]"
        else:
            first_value = (
                "trim("
                "  split_part("
                "    trim(CAST(o.offices AS VARCHAR), '[]'),"
                "    ',',"
                "    1"
                "  ),"
                "  ' \"'"
                ")"
            )

        return (
            "COALESCE("
            f"  NULLIF({first_value}, ''),"
            "  'Не указан'"
            ")"
        )

    # --------------------------------------------------------
    # Базовая витрина
    # --------------------------------------------------------

    def _init_base(self) -> None:
        bucket_name_sql, bucket_sort_sql = _bucket_sql("age_hours")
        office_expr = self._office_expression()
        as_of_literal = self.as_of.strftime("%Y-%m-%d %H:%M:%S")
        amount_expr, self.amount_source = self._amount_expression()

        self.con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE fbs_base AS

            WITH snapshot AS (
                SELECT *
                FROM {self.orders_source}
                WHERE snapshot_date = (
                    SELECT MAX(snapshot_date)
                    FROM {self.orders_source}
                )
            ),

            enriched AS (
                SELECT
                    /*
                    Колонки перечислены явно, а не через o.*:
                    в выгрузке есть payload с сырым ответом API
                    и ещё несколько служебных полей, которые в
                    анализе не нужны, а временную таблицу
                    раздувают в разы.
                    */
                    o.order_id,
                    o.created_at,
                    o.nm_id,
                    o.chrt_id,
                    o.article,
                    o.sku,
                    o.warehouse_id,
                    o.price_rub,
                    o.sale_price_rub,
                    o.final_price_rub,
                    {amount_expr} AS order_amount,
                    o.supplier_status,
                    o.wb_status,
                    o.supply_id,
                    o.supply_name,
                    o.supply_created_at,
                    o.supply_closed_at,
                    o.supply_scan_dt,
                    o.destination_office_id,
                    o.office_id,
                    o.is_zero_order,
                    o.hours_to_supply_close,
                    o.hours_to_supply_scan,
                    o.snapshot_date,

                    COALESCE(
                        UPPER(p.brand),
                        'БРЕНД НЕ УКАЗАН'
                    ) AS brand,

                    p.subject_id,

                    COALESCE(
                        p.subject_name,
                        'Категория не указана'
                    ) AS subject_name,

                    COALESCE(p.gender, 'Не указан') AS gender,
                    p.title,

                    /*
                    Возраст заказа на момент выгрузки.

                    Для закрытых заказов берём срок, который
                    посчитал WB, а если он не пришёл — считаем
                    сами по датам. Для остальных — время от
                    создания до момента выгрузки.
                    */
                    CASE
                        WHEN o.supply_closed_at IS NOT NULL
                            THEN COALESCE(
                                o.hours_to_supply_close,
                                EXTRACT(
                                    EPOCH FROM (
                                        o.supply_closed_at
                                        - o.created_at
                                    )
                                ) / 3600.0
                            )
                        ELSE
                            EXTRACT(
                                EPOCH FROM (
                                    TIMESTAMP '{as_of_literal}'
                                    - o.created_at
                                )
                            ) / 3600.0
                    END AS age_hours,

                    /*
                    Три состояния делят выборку без пересечений:
                    отменён / закрыт поставкой / открыт. Сумма
                    трёх всегда равна общему количеству заказов.
                    */
                    CASE
                        WHEN {_cancelled_sql('o')}
                            THEN 'cancelled'
                        WHEN o.supply_closed_at IS NOT NULL
                            THEN 'closed'
                        ELSE 'open'
                    END AS order_state,

                    /*
                    «На сборке» — подмножество открытых, а не
                    четвёртое состояние. Без условий на поставку
                    и отмену один и тот же заказ мог попасть и в
                    «закрыто поставкой», и в «на сборке», из-за
                    чего показатели не сходились с общим числом.
                    */
                    (
                        o.supplier_status = '{IN_WORK_SUPPLIER_STATUS}'
                        AND o.wb_status = '{IN_WORK_WB_STATUS}'
                        AND o.supply_closed_at IS NULL
                        AND NOT ({_cancelled_sql('o')})
                    ) AS is_in_work,

                    /*
                    offices — список пунктов, куда заказ можно
                    передать. Для отчётности берём первый,
                    основной. Выражение подбирается под реальный
                    тип колонки: список или JSON-строка.
                    */
                    {office_expr} AS office_name

                FROM snapshot o

                LEFT JOIN inventories.wb_product p
                    ON p.card_id = o.nm_id
            )

            SELECT
                *,
                {bucket_name_sql} AS time_group,
                {bucket_sort_sql} AS time_sort,
                (
                    age_hours >= {SLA_LIMIT_HOURS}
                    AND order_state = 'open'
                ) AS is_overdue
            FROM enriched
            """
        )

    # --------------------------------------------------------
    # Фильтры
    # --------------------------------------------------------

    def _build_filters(
        self,
        start=None,
        end=None,
        cat_list=None,
        brand_list=None,
        gender_list=None,
        alias: str = "fbs_base",
    ) -> tuple[str, list[Any]]:
        """
        Собирает условия отбора.

        alias обязателен: в запросе по поставкам к заказам
        присоединяется витрина поставок, и у обеих есть
        created_at. Без имени таблицы DuckDB справедливо
        ругается на неоднозначную колонку.
        """
        prefix = f"{alias}." if alias else ""

        clauses: list[str] = []
        parameters: list[Any] = []

        if start is not None and end is not None:
            clauses.append(
                f"{prefix}created_at::DATE "
                "BETWEEN ?::DATE AND ?::DATE"
            )
            parameters.extend([start, end])

        categories = _normalize_list(cat_list)
        brands = _normalize_list(brand_list)
        genders = _normalize_list(gender_list)

        if categories:
            ids = [int(v) for v in categories]
            clauses.append(
                f"{prefix}subject_id IN ({_placeholders(ids)})"
            )
            parameters.extend(ids)

        if brands:
            values = [str(v).upper() for v in brands]
            clauses.append(
                f"{prefix}brand IN ({_placeholders(values)})"
            )
            parameters.extend(values)

        if genders:
            values = [str(v) for v in genders]
            clauses.append(
                f"{prefix}gender IN ({_placeholders(values)})"
            )
            parameters.extend(values)

        if not clauses:
            return "TRUE", []

        return " AND ".join(clauses), parameters

    def _query(self, sql: str, filters: str, parameters, extra=None):
        params = list(parameters)

        if extra:
            params.extend(extra)

        return self.con.execute(
            sql.format(filters=filters),
            params,
        ).df()

    # ========================================================
    # 1. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ
    # ========================================================

    def get_kpi(self, **kwargs) -> dict:
        filters, parameters = self._build_filters(**kwargs)

        row = self.con.execute(
            f"""
            SELECT
                COUNT(*) AS orders_total,

                COUNT(*) FILTER (WHERE is_in_work)
                    AS orders_in_work,

                COUNT(*) FILTER (
                    WHERE is_in_work AND is_overdue
                ) AS orders_overdue,

                COUNT(*) FILTER (WHERE order_state = 'closed')
                    AS orders_closed,

                COUNT(*) FILTER (WHERE order_state = 'cancelled')
                    AS orders_cancelled,

                COUNT(*) FILTER (WHERE order_state = 'open')
                    AS orders_open,

                -- COUNT DISTINCT сам не считает NULL,
                -- отдельный FILTER тут не нужен
                COUNT(DISTINCT supply_id) AS supplies_total,

                COUNT(DISTINCT nm_id) AS nm_count,

                SUM(order_amount) AS amount,

                AVG(age_hours) FILTER (WHERE is_in_work)
                    AS avg_age_in_work,

                MAX(age_hours) FILTER (WHERE is_in_work)
                    AS max_age_in_work,

                AVG(hours_to_supply_close) FILTER (
                    WHERE order_state = 'closed'
                ) AS avg_hours_to_close

            FROM fbs_base
            WHERE {filters}
            """,
            parameters,
        ).fetchone()

        keys = [
            "orders_total",
            "orders_in_work",
            "orders_overdue",
            "orders_closed",
            "orders_cancelled",
            "orders_open",
            "supplies_total",
            "nm_count",
            "amount",
            "avg_age_in_work",
            "max_age_in_work",
            "avg_hours_to_close",
        ]

        result = dict(zip(keys, row or [0] * len(keys)))
        result["as_of"] = self.as_of
        result["amount_source"] = getattr(
            self, "amount_source", "—"
        )

        return result

    # ========================================================
    # 2. КОНТРОЛЬ СБОРКИ
    # ========================================================

    def get_assembly_buckets(self, only_in_work=True, **kwargs) -> pd.DataFrame:
        """
        Распределение заказов по корзинам времени.

        only_in_work=True — только то, что сейчас на сборке
        (оперативный контроль). False — все активные заказы,
        включая уже закрытые, для оценки среднего срока.
        """
        filters, parameters = self._build_filters(**kwargs)

        if only_in_work:
            scope = "is_in_work"
        else:
            scope = "order_state <> 'cancelled'"

        return self.con.execute(
            f"""
            WITH grouped AS (
                SELECT
                    time_group,
                    time_sort,
                    COUNT(*) AS orders,
                    COUNT(*) FILTER (
                        WHERE order_state = 'closed'
                    ) AS closed_orders,
                    COUNT(*) FILTER (
                        WHERE order_state = 'open'
                    ) AS open_orders,
                    ROUND(AVG(age_hours), 2) AS avg_hours,
                    ROUND(
                        SUM(order_amount),
                        2
                    ) AS amount
                FROM fbs_base
                WHERE {filters}
                  AND {scope}
                  AND age_hours >= 0
                GROUP BY time_group, time_sort
            )

            SELECT
                time_group,
                time_sort,
                orders,
                closed_orders,
                open_orders,
                ROUND(
                    100.0 * orders / SUM(orders) OVER (),
                    2
                ) AS share_pct,
                avg_hours,
                amount
            FROM grouped
            ORDER BY time_sort
            """,
            parameters,
        ).df()

    def get_overdue_orders(self, limit=500, **kwargs) -> pd.DataFrame:
        """Заказы на сборке, вышедшие за норматив."""
        filters, parameters = self._build_filters(**kwargs)

        data = self._query(
            f"""
            SELECT
                order_id,
                created_at,
                ROUND(age_hours, 1) AS age_hours,
                article,
                title,
                brand,
                subject_name,
                office_name,
                warehouse_id,
                supply_name,
                ROUND(order_amount, 2) AS amount
            FROM fbs_base
            WHERE {{filters}}
              AND is_in_work
              AND age_hours >= {SLA_LIMIT_HOURS}
            ORDER BY age_hours DESC
            LIMIT {int(limit)}
            """,
            filters,
            parameters,
        )

        return self._label_places(data)

    # ========================================================
    # 3. ЛОГИСТИКА: СКЛАДЫ И ОФИСЫ
    # ========================================================

    def get_logistics(self, **kwargs) -> pd.DataFrame:
        filters, parameters = self._build_filters(**kwargs)

        data = self._query(
            """
            SELECT
                warehouse_id,

                office_name,

                destination_office_id,

                COUNT(*) AS orders,

                COUNT(*) FILTER (WHERE is_in_work)
                    AS orders_in_work,

                COUNT(*) FILTER (
                    WHERE is_in_work AND is_overdue
                ) AS orders_overdue,

                COUNT(DISTINCT supply_id) AS supplies,

                ROUND(AVG(age_hours), 2) AS avg_hours,

                ROUND(
                    SUM(order_amount),
                    2
                ) AS amount

            FROM fbs_base
            WHERE {filters}
            GROUP BY 1, 2, 3
            ORDER BY orders DESC
            """,
            filters,
            parameters,
        )

        # В выгрузке заказов есть только номер склада. Название
        # подставляем из справочника, если оно там заведено.
        return self._label_places(data)

    # ========================================================
    # 4. ПОСТАВКИ
    # ========================================================

    def get_supplies(self, limit=1000, **kwargs) -> pd.DataFrame:
        """
        Жизненный цикл поставок с количеством заказов в каждой.

        Заказы берём из текущего среза, атрибуты поставки —
        из витрины поставок, если она есть.
        """
        filters, parameters = self._build_filters(alias="o", **kwargs)

        if self.supplies_source is None:
            supply_join = ""
            supply_columns = """
                NULL AS cargo_type,
                NULL AS is_b2b,
                NULL AS reject_dt
            """
        else:
            supply_join = f"""
            LEFT JOIN (
                SELECT *
                FROM {self.supplies_source}
                WHERE snapshot_date = (
                    SELECT MAX(snapshot_date)
                    FROM {self.supplies_source}
                )
            ) s ON s.supply_id = o.supply_id
            """
            supply_columns = """
                ANY_VALUE(s.cargo_type) AS cargo_type,
                ANY_VALUE(s.is_b2b) AS is_b2b,
                ANY_VALUE(s.reject_dt) AS reject_dt
            """

        return self._query(
            f"""
            SELECT
                o.supply_id,
                ANY_VALUE(o.supply_name) AS supply_name,
                MIN(o.supply_created_at) AS created_at,
                MAX(o.supply_closed_at) AS closed_at,
                MAX(o.supply_scan_dt) AS scan_dt,
                {supply_columns},

                COUNT(*) AS orders,

                COUNT(*) FILTER (
                    WHERE o.order_state = 'cancelled'
                ) AS cancelled_orders,

                ROUND(
                    AVG(o.hours_to_supply_close),
                    2
                ) AS avg_hours_to_close,

                ROUND(
                    AVG(o.hours_to_supply_scan),
                    2
                ) AS avg_hours_to_scan,

                ROUND(
                    SUM(o.order_amount),
                    2
                ) AS amount

            FROM fbs_base o
            {supply_join}
            WHERE {{filters}}
              AND o.supply_id IS NOT NULL
            GROUP BY o.supply_id
            ORDER BY MIN(o.supply_created_at) DESC
            LIMIT {int(limit)}
            """,
            filters,
            parameters,
        )

    # ========================================================
    # 5. ТОВАРЫ И ДЕНЬГИ
    # ========================================================

    def get_products(self, limit=500, **kwargs) -> pd.DataFrame:
        filters, parameters = self._build_filters(**kwargs)

        return self._query(
            f"""
            SELECT
                nm_id,
                ANY_VALUE(article) AS article,
                ANY_VALUE(title) AS title,
                ANY_VALUE(brand) AS brand,
                ANY_VALUE(subject_name) AS subject_name,

                COUNT(*) AS orders,

                COUNT(*) FILTER (WHERE is_in_work)
                    AS orders_in_work,

                COUNT(*) FILTER (
                    WHERE order_state = 'cancelled'
                ) AS cancelled_orders,

                COUNT(*) FILTER (WHERE is_zero_order)
                    AS zero_orders,

                ROUND(AVG(age_hours), 2) AS avg_hours,

                ROUND(
                    SUM(order_amount),
                    2
                ) AS amount

            FROM fbs_base
            WHERE {{filters}}
            GROUP BY nm_id
            ORDER BY orders DESC
            LIMIT {int(limit)}
            """,
            filters,
            parameters,
        )

    # ========================================================
    # 6. СТАТУСЫ
    # ========================================================

    def get_statuses(self, **kwargs) -> pd.DataFrame:
        filters, parameters = self._build_filters(**kwargs)

        return self._query(
            """
            SELECT
                COALESCE(supplier_status, '—') AS supplier_status,
                COALESCE(wb_status, '—') AS wb_status,
                COUNT(*) AS orders,
                ROUND(AVG(age_hours), 2) AS avg_hours,
                ROUND(
                    SUM(order_amount),
                    2
                ) AS amount
            FROM fbs_base
            WHERE {filters}
            GROUP BY 1, 2
            ORDER BY orders DESC
            """,
            filters,
            parameters,
        )

    # ========================================================
    # 7. ДИНАМИКА ПО ДНЯМ
    # ========================================================

    def get_daily(self, **kwargs) -> pd.DataFrame:
        filters, parameters = self._build_filters(**kwargs)

        return self._query(
            """
            SELECT
                created_at::DATE AS order_date,
                COUNT(*) AS orders,
                COUNT(*) FILTER (
                    WHERE order_state = 'cancelled'
                ) AS cancelled_orders,
                COUNT(*) FILTER (
                    WHERE order_state = 'closed'
                ) AS closed_orders,
                ROUND(AVG(age_hours), 2) AS avg_hours,
                ROUND(
                    SUM(order_amount),
                    2
                ) AS amount
            FROM fbs_base
            WHERE {filters}
            GROUP BY 1
            ORDER BY 1 DESC
            """,
            filters,
            parameters,
        )

    # ========================================================
    # 8. ПОСТРОЧНАЯ ВЫГРУЗКА
    # ========================================================

    def get_raw(self, limit=200000, **kwargs) -> pd.DataFrame:
        filters, parameters = self._build_filters(**kwargs)

        data = self._query(
            f"""
            SELECT
                order_id,
                created_at,
                supplier_status,
                wb_status,
                order_state,
                ROUND(age_hours, 2) AS age_hours,
                time_group,
                nm_id,
                chrt_id,
                article,
                title,
                brand,
                subject_name,
                gender,
                warehouse_id,
                office_name,
                destination_office_id,
                supply_id,
                supply_name,
                supply_created_at,
                supply_closed_at,
                supply_scan_dt,
                ROUND(hours_to_supply_close, 2) AS hours_to_supply_close,
                ROUND(hours_to_supply_scan, 2) AS hours_to_supply_scan,
                is_zero_order,
                ROUND(COALESCE(price_rub, 0), 2) AS price_rub,
                ROUND(COALESCE(sale_price_rub, 0), 2) AS sale_price_rub,
                ROUND(COALESCE(final_price_rub, 0), 2) AS final_price_rub,
                ROUND(order_amount, 2) AS order_amount
            FROM fbs_base
            WHERE {{filters}}
            ORDER BY created_at DESC
            LIMIT {int(limit)}
            """,
            filters,
            parameters,
        )

        return self._label_places(data)


# ============================================================
# ЕДИНАЯ ТОЧКА СБОРА
# ============================================================

def collect_fbs_analysis(
    start=None,
    end=None,
    cat_list=None,
    brand_list=None,
    gender_list=None,
) -> dict:
    """
    Собирает все срезы анализа за один заход.

    Открывать соединение по разу на блок дорого: временная
    таблица fbs_base пересобиралась бы каждый раз. Поэтому
    и дашборд, и Excel берут данные отсюда.
    """
    filters = {
        "start": start,
        "end": end,
        "cat_list": cat_list,
        "brand_list": brand_list,
        "gender_list": gender_list,
    }

    with FbsData() as fbs:
        return {
            "kpi": fbs.get_kpi(**filters),
            "buckets_in_work": fbs.get_assembly_buckets(
                only_in_work=True, **filters
            ),
            "buckets_all": fbs.get_assembly_buckets(
                only_in_work=False, **filters
            ),
            "overdue": fbs.get_overdue_orders(**filters),
            "logistics": fbs.get_logistics(**filters),
            "supplies": fbs.get_supplies(**filters),
            "products": fbs.get_products(**filters),
            "statuses": fbs.get_statuses(**filters),
            "daily": fbs.get_daily(**filters),
            "as_of": fbs.as_of,
            "source": fbs.orders_source,
            "amount_source": fbs.amount_source,
        }
