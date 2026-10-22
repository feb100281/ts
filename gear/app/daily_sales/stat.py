# # gear/app/daily_sales/stat.py
# from datetime import date
# import locale

# import pandas as pd
# import dash_mantine_components as dmc
# from dash_iconify import DashIconify
# from dash import dcc, Input, Output, State, ALL

# from .data import get_last_update
# from .filters import WbFilters
# from .grids import grid_date, day_details
# from ..misc.baners import in_construction_widjet
# from .summary import get_sales_summary
# from ..data.base import DashboardData


# try:
#     locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
# except locale.Error:
#     pass


# ## Делаем PL виджет




# def wrap_in_paper(icon,title,content):
#     return dmc.Paper(
#         withBorder=True,
#         shadow="md",
#         radius="md",
#         p="xl",
#         children = dmc.Stack(
#             [
#                 dmc.Group(
#                     [
#                         icon,
#                         dmc.Title(title,order=4)
#                     ]
#                 ),
#                 content
#             ]
#         )
#     )
    

# class StatWindow:
#     def __init__(self, 
#                  date_range = [date(2024,1,1),date.today()],
#                  cat = None,
#                  brand = None,
#                  gender = None
#                  ):
#         dr = [date(2024,1,1),date.today()] if not date_range else date_range
#         self.start, self.end = dr
#         self.cat = cat
#         self.brand = brand
#         self.gender = gender    
        
#         self.stat_container_id = 'stat_container_id'
        
    
    
#     def layout(self):
#         return dmc.Container(
#             [
#                 dmc.Stack(
#                     [
#                         dmc.Grid(
#                             [
#                                 dmc.GridCol(
#                                     [
#                                         wrap_in_paper(
#                                             DashIconify(icon='streamline-ultimate:accounting-calculator-1',width=24),
#                                             'P&L по выбраным фильтрам',
#                                             in_construction_widjet()
#                                         )
#                                     ],
#                                     span=4
#                                 ),
#                                 dmc.GridCol(
#                                     [
#                                         wrap_in_paper(
#                                             DashIconify(icon='material-symbols-light:area-chart-outline',width=24),
#                                             'График динамики показателей',
#                                             in_construction_widjet()
#                                         )
#                                     ],
#                                     span=8
#                                 ),
                                
#                             ]
                            
#                         ),
#                         dmc.SimpleGrid(
#                             [
#                                 wrap_in_paper(
#                                             DashIconify(icon='ri:pie-chart-fill',width=24),
#                                             'Структура доходов',
#                                             in_construction_widjet()
#                                         ),
#                                 wrap_in_paper(
#                                             DashIconify(icon='ri:pie-chart-line',width=24),
#                                             'Структура расходов',
#                                             in_construction_widjet()
#                                         )
#                             ],
#                             cols=2
#                         )
#                     ]
#                 )
#             ],
#             fluid=True,
#             id = self.stat_container_id,
#             # style={"display": "none"}
#         )

# # with DashboardData() as d:
# #     rel = d.con.register('daily_sales',d.get_dayly_sales_grid_data())
# #     rel.sql('select * from daily_sales').show()




# gear/app/daily_sales/stat.py

from datetime import date
import locale

import dash_mantine_components as dmc

from dash_iconify import (
    DashIconify,
)

from ..misc.baners import (
    in_construction_widjet,
)

from .revenue_structure.components import (
    build_revenue_structure,
)


try:
    locale.setlocale(
        locale.LC_ALL,
        "ru_RU.UTF-8",
    )
except locale.Error:
    pass


# =========================================================
# Универсальная карточка
# =========================================================

def wrap_in_paper(
    icon,
    title,
    content,
):

    return dmc.Paper(
        withBorder=True,

        shadow="sm",

        radius=0,

        p="lg",

        children=dmc.Stack(
            gap="md",

            children=[
                dmc.Group(
                    gap="sm",

                    children=[
                        dmc.ThemeIcon(
                            variant="light",

                            color="blue",

                            radius=0,

                            size=38,

                            children=icon,
                        ),

                        dmc.Title(
                            title,

                            order=4,

                            fw=800,
                        ),
                    ],
                ),

                content,
            ],
        ),
    )


# =========================================================
# Окно статистики
# =========================================================

class StatWindow:

    def __init__(
        self,
        date_range=None,
        cat=None,
        brand=None,
        gender=None,
    ):

        dr = (
            [
                date(
                    2024,
                    1,
                    1,
                ),

                date.today(),
            ]

            if not date_range

            else date_range
        )

        self.start = dr[0]

        self.end = dr[1]

        self.cat = cat

        self.brand = brand

        self.gender = gender

        self.stat_container_id = (
            "stat_container_id"
        )

    # =====================================================
    # Layout
    # =====================================================

    def layout(
        self,
    ):

        # -------------------------------------------------
        # Доходы и маржинальность
        # -------------------------------------------------

        revenue_structure = (
            build_revenue_structure(
                start_date=(
                    self.start
                ),

                end_date=(
                    self.end
                ),

                cat=(
                    self.cat
                ),

                brand=(
                    self.brand
                ),

                gender=(
                    self.gender
                ),
            )
        )

        return dmc.Container(
            fluid=True,

            px=0,

            id=(
                self.stat_container_id
            ),

            children=[
                dmc.Stack(
                    gap="xl",

                    children=[
                        # =====================================
                        # Верхний блок
                        # =====================================

                        dmc.Grid(
                            gutter="md",

                            children=[
                                # -----------------------------
                                # P&L
                                # -----------------------------

                                dmc.GridCol(
                                    span={
                                        "base": 12,
                                        "lg": 4,
                                    },

                                    children=[
                                        wrap_in_paper(
                                            DashIconify(
                                                icon=(
                                                    "streamline-ultimate:"
                                                    "accounting-"
                                                    "calculator-1"
                                                ),

                                                width=22,
                                            ),

                                            (
                                                "P&L по "
                                                "выбранным фильтрам"
                                            ),

                                            (
                                                in_construction_widjet()
                                            ),
                                        )
                                    ],
                                ),

                                # -----------------------------
                                # Динамика
                                # -----------------------------

                                dmc.GridCol(
                                    span={
                                        "base": 12,
                                        "lg": 8,
                                    },

                                    children=[
                                        wrap_in_paper(
                                            DashIconify(
                                                icon=(
                                                    "material-symbols-light:"
                                                    "area-chart-outline"
                                                ),

                                                width=24,
                                            ),

                                            (
                                                "Динамика "
                                                "показателей"
                                            ),

                                            (
                                                in_construction_widjet()
                                            ),
                                        )
                                    ],
                                ),
                            ],
                        ),

                        # =====================================
                        # Доходы и маржинальность
                        # =====================================

                        dmc.Paper(
                            withBorder=True,

                            shadow="sm",

                            radius=0,

                            p="lg",

                            children=(
                                revenue_structure
                            ),
                        ),

                        # =====================================
                        # Расходы
                        # =====================================

                        wrap_in_paper(
                            DashIconify(
                                icon=(
                                    "solar:"
                                    "pie-chart-3-"
                                    "bold-duotone"
                                ),

                                width=23,
                            ),

                            (
                                "Структура расходов"
                            ),

                            (
                                in_construction_widjet()
                            ),
                        ),
                    ],
                ),
            ],
        )

