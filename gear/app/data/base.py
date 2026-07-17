# # gear/app/data/base.py
# import duckdb
# from conns import get_duckdb_conn_with_opt
# from .queries import (
#     BASE_QUERY,
#     BASE_STOCKS,
#     BASE_WB_COSTS,
#     DAILY_SALES_AGG,
#     DETAILS_DAY,
#     DETAILS_PERIOD,
# )
# from datetime import date


# class DashboardData:

#     def __enter__(self):
#         self.con = get_duckdb_conn_with_opt()

#         self._init_base()
#         self._init_stocks()
#         self._init_wb_costs()

#         return self
    
#     def _init_stocks(self):
#         self.con.execute(BASE_STOCKS)

#     def __exit__(self, exc_type, exc, tb):
#         self.con.close()
    
#     def _init_base(self):
#         self.con.execute(BASE_QUERY)
    
#     def _init_wb_costs(self):
#         self.con.execute(BASE_WB_COSTS)
    
#     def make_filter(self, cat_id=None, gender=None, brand=None):
#         cat_filter = ''
#         gender_filter = ''
#         brand_filter = ''

#         if cat_id:
#             if isinstance(cat_id, list):
#                 cat_filter = f"AND subject_id IN ({','.join(str(int(x)) for x in cat_id)})"
#             else:
#                 cat_filter = f"AND subject_id = {int(cat_id)}"

#         if gender:
#             if isinstance(gender, list):
#                 gender_filter = f"AND gender IN ({','.join(f'\'{x}\'' for x in gender)})"
#             else:
#                 gender_filter = f"AND gender = '{gender}'"

#         if brand:
#             if isinstance(brand, list):
#                 brand_filter = f"AND brand IN ({','.join(f'\'{x}\'' for x in brand)})"
#             else:
#                 brand_filter = f"AND brand = '{brand}'"

#         return f"{cat_filter} {gender_filter} {brand_filter}"
        
#     def get_dayly_sales_grid_data(
#         self,
#         start = date(2024,1,1),
#         end = date.today(),
#         cats_list = [],
#         brand_list = None,
#         gender_list = None        
#         ):
#         sql = DAILY_SALES_AGG.format(filters = self.make_filter(cats_list,gender_list,brand_list))
        
#         return self.con.execute(sql,parameters=[start,end]).df()
    
#     def get_day_details(self,date,cat_list=[],brand_list = None,gender_list = None):
#         sql = DETAILS_DAY.format(filters = self.make_filter(cat_list,gender_list,brand_list))
#         return self.con.execute(sql,parameters=[date,]).df()
    
#     def get_period_details(
#         self,
#         start,
#         end,
#         cat_list=None,
#         brand_list=None,
#         gender_list=None,
#     ):
#         sql = DETAILS_PERIOD.format(
#             filters=self.make_filter(
#                 cat_list,
#                 gender_list,
#                 brand_list,
#             )
#         )

#         return self.con.execute(
#             sql,
#             parameters=[
#                 # Период продаж
#                 start,
#                 end,

#                 # Период ежедневных остатков
#                 start,
#                 end,

#                 # Остаток на конец периода
#                 end,
#             ],
#         ).df()




# gear/app/data/base.py

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

import pandas as pd

from conns import get_duckdb_conn_with_opt

from .queries import (
    BASE_QUERY,
    BASE_STOCKS,
    BASE_WB_COSTS,
    DAILY_SALES_AGG,
    DETAILS_DAY,
    DETAILS_PERIOD,
)


class DashboardData:
    """
    Работа с данными дашборда продаж.

    При входе в контекст создаются временные таблицы:

    - base — продажи и себестоимость;
    - stocks_daily — ежедневные остатки;
    - wb_costs — расходы WB.
    """

    def __enter__(self) -> "DashboardData":
        self.con = get_duckdb_conn_with_opt()

        self._init_base()
        self._init_stocks()
        self._init_wb_costs()

        return self

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        if getattr(self, "con", None) is not None:
            self.con.close()

    # ------------------------------------------------------------------
    # Инициализация временных таблиц
    # ------------------------------------------------------------------

    def _init_base(self) -> None:
        self.con.execute(BASE_QUERY)

    def _init_stocks(self) -> None:
        self.con.execute(BASE_STOCKS)

    def _init_wb_costs(self) -> None:
        self.con.execute(BASE_WB_COSTS)

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_list(
        value: Any,
    ) -> list[Any]:
        """
        Приводит одиночное значение или коллекцию к списку.

        None, пустая строка и пустая коллекция превращаются
        в пустой список.
        """
        if value is None:
            return []

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return []

            return [value]

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
                pd.Series,
            ),
        ):
            return [
                item
                for item in value
                if item is not None
                and str(item).strip() != ""
            ]

        return [value]

    @staticmethod
    def _placeholders(
        values: Iterable[Any],
    ) -> str:
        """
        Создаёт строку плейсхолдеров:

        ?, ?, ?
        """
        values = list(values)

        return ", ".join(
            "?"
            for _ in values
        )

    def _build_sales_filters(
        self,
        cat_list=None,
        gender_list=None,
        brand_list=None,
        alias: str = "t",
    ) -> tuple[str, list[Any]]:
        """
        Формирует фильтры для таблицы base.

        В base доступны:

        - subject_id;
        - gender;
        - brand.

        Возвращает:

        - SQL-фрагмент;
        - список параметров.
        """
        clauses: list[str] = []
        parameters: list[Any] = []

        categories = self._normalize_list(
            cat_list
        )

        genders = self._normalize_list(
            gender_list
        )

        brands = self._normalize_list(
            brand_list
        )

        if categories:
            category_ids = [
                int(value)
                for value in categories
            ]

            clauses.append(
                f"{alias}.subject_id IN "
                f"({self._placeholders(category_ids)})"
            )

            parameters.extend(
                category_ids
            )

        if genders:
            gender_values = [
                str(value)
                for value in genders
            ]

            clauses.append(
                f"{alias}.gender IN "
                f"({self._placeholders(gender_values)})"
            )

            parameters.extend(
                gender_values
            )

        if brands:
            brand_values = [
                str(value).upper()
                for value in brands
            ]

            clauses.append(
                f"UPPER({alias}.brand) IN "
                f"({self._placeholders(brand_values)})"
            )

            parameters.extend(
                brand_values
            )

        if not clauses:
            return "", []

        sql_filter = "\nAND " + "\nAND ".join(
            clauses
        )

        return sql_filter, parameters

    def _build_stock_filters(
        self,
        cat_list=None,
        gender_list=None,
        brand_list=None,
        alias: str = "t",
    ) -> tuple[str, list[Any]]:
        """
        Формирует фильтры для stocks_daily.

        Фильтрация выполняется через inventories.wb_product,
        поэтому метод работает даже в том случае, если в
        stocks_daily нет subject_id.

        Связь:

            inventories.wb_product.card_id = stocks_daily.usk
        """
        conditions: list[str] = []
        parameters: list[Any] = []

        categories = self._normalize_list(
            cat_list
        )

        genders = self._normalize_list(
            gender_list
        )

        brands = self._normalize_list(
            brand_list
        )

        if categories:
            category_ids = [
                int(value)
                for value in categories
            ]

            conditions.append(
                "wp.subject_id IN "
                f"({self._placeholders(category_ids)})"
            )

            parameters.extend(
                category_ids
            )

        if genders:
            gender_values = [
                str(value)
                for value in genders
            ]

            conditions.append(
                "COALESCE("
                "wp.gender, "
                "'Не указан'"
                ") IN "
                f"({self._placeholders(gender_values)})"
            )

            parameters.extend(
                gender_values
            )

        if brands:
            brand_values = [
                str(value).upper()
                for value in brands
            ]

            conditions.append(
                "UPPER(wp.brand) IN "
                f"({self._placeholders(brand_values)})"
            )

            parameters.extend(
                brand_values
            )

        if not conditions:
            return "", []

        exists_filter = f"""
AND EXISTS (
    SELECT 1
    FROM inventories.wb_product wp
    WHERE wp.card_id = {alias}.usk
      AND {" AND ".join(conditions)}
)
"""

        return exists_filter, parameters

    # ------------------------------------------------------------------
    # Основная таблица по дням
    # ------------------------------------------------------------------

    def get_dayly_sales_grid_data(
        self,
        start: date = date(2024, 1, 1),
        end: date | None = None,
        cats_list=None,
        brand_list=None,
        gender_list=None,
    ) -> pd.DataFrame:
        """
        Возвращает агрегированные продажи по дням.

        Дополнительно возвращаются остатки на соответствующий день.
        """
        if end is None:
            end = date.today()

        sales_filter, sales_parameters = (
            self._build_sales_filters(
                cat_list=cats_list,
                gender_list=gender_list,
                brand_list=brand_list,
                alias="t",
            )
        )

        stock_filter, stock_parameters = (
            self._build_stock_filters(
                cat_list=cats_list,
                gender_list=gender_list,
                brand_list=brand_list,
                alias="t",
            )
        )

        sql = DAILY_SALES_AGG.format(
            filters=sales_filter,
            stock_filters=stock_filter,
        )

        parameters = [
            # sales_by_day:
            start,
            end,
            *sales_parameters,

            # stock_by_day:
            start,
            end,
            *stock_parameters,
        ]

        return self.con.execute(
            sql,
            parameters=parameters,
        ).df()

    # ------------------------------------------------------------------
    # Детализация одного дня
    # ------------------------------------------------------------------

    def get_day_details(
        self,
        date_value,
        cat_list=None,
        brand_list=None,
        gender_list=None,
    ) -> pd.DataFrame:
        """
        Возвращает детализацию по товарам за один день.

        В результат включаются:

        - товары с продажами;
        - товары с остатками, но без продаж;
        - остатки на последнюю доступную дату,
          которая не превышает выбранную дату.
        """
        sales_filter, sales_parameters = (
            self._build_sales_filters(
                cat_list=cat_list,
                gender_list=gender_list,
                brand_list=brand_list,
                alias="t",
            )
        )

        stock_filter, stock_parameters = (
            self._build_stock_filters(
                cat_list=cat_list,
                gender_list=gender_list,
                brand_list=brand_list,
                alias="t",
            )
        )

        sql = DETAILS_DAY.format(
            filters=sales_filter,
            stock_filters=stock_filter,
        )

        parameters = [
            # sales_agg:
            date_value,
            *sales_parameters,

            # stock_date:
            date_value,

            # stock_end:
            *stock_parameters,
        ]

        return self.con.execute(
            sql,
            parameters=parameters,
        ).df()

    # ------------------------------------------------------------------
    # Детализация периода
    # ------------------------------------------------------------------

    def get_period_details(
        self,
        start,
        end,
        cat_list=None,
        brand_list=None,
        gender_list=None,
    ) -> pd.DataFrame:
        """
        Возвращает детализацию по товарам за выбранный период.

        В результат включаются:

        - продажи за период;
        - сумма ежедневных остатков;
        - количество дней с остатками;
        - оборачиваемость;
        - остаток на последнюю доступную дату;
        - товары с остатками, но без продаж.
        """
        sales_filter, sales_parameters = (
            self._build_sales_filters(
                cat_list=cat_list,
                gender_list=gender_list,
                brand_list=brand_list,
                alias="t",
            )
        )

        stock_period_filter, stock_period_parameters = (
            self._build_stock_filters(
                cat_list=cat_list,
                gender_list=gender_list,
                brand_list=brand_list,
                alias="t",
            )
        )

        stock_end_filter, stock_end_parameters = (
            self._build_stock_filters(
                cat_list=cat_list,
                gender_list=gender_list,
                brand_list=brand_list,
                alias="t",
            )
        )

        # В DETAILS_PERIOD один и тот же шаблон
        # {stock_filters} используется два раза:
        #
        # 1. в stock_period;
        # 2. в stock_end.
        #
        # Поэтому создаём два отдельных маркера,
        # чтобы параметры передавались в правильном порядке.
        sql = DETAILS_PERIOD

        sql = sql.replace(
            "{filters}",
            sales_filter,
        )

        sql = sql.replace(
            "{stock_filters}",
            stock_period_filter,
            1,
        )

        sql = sql.replace(
            "{stock_filters}",
            stock_end_filter,
            1,
        )

        parameters = [
            # sales_agg:
            start,
            end,
            *sales_parameters,

            # stock_period:
            start,
            end,
            *stock_period_parameters,

            # stock_end_date:
            end,

            # stock_end:
            *stock_end_parameters,
        ]

        return self.con.execute(
            sql,
            parameters=parameters,
        ).df()
        
        
        # to do fuc 
def donothing():
    pass

