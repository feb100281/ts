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
    
    def make_filter(self, cat_id=None, gender=None, brand=None):
        cat_id = cat_id or []
        gender = gender or []
        brand = brand or []
        
        cat_filter = ''   # <-- обязательно инициализировать
        gender_filter = ''
        brand_filter = ''

        if cat_id:
            if isinstance(cat_id, list):
                cat_filter = f"AND subject_id IN ({','.join(str(int(x)) for x in cat_id)})"
            else:
                cat_filter = f"AND subject_id = {int(cat_id)}"

        if gender:
            if isinstance(gender, list):
                gender_filter = f"AND gender IN ({','.join(f'\'{x}\'' for x in gender)})"
            else:
                gender_filter = f"AND gender = '{gender}'"

        if brand:
            if isinstance(brand, list):
                brand_filter = f"AND brand IN ({','.join(f'\'{x}\'' for x in brand)})"
            else:
                brand_filter = f"AND brand = '{brand}'"

        return f"{cat_filter} {gender_filter} {brand_filter}"
        
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

