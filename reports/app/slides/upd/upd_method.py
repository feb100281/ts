#reports/app/slides/upd/upd_method.py
import dash_mantine_components as dmc
from dash_iconify import DashIconify

""" 
Слайд с методикой обработки УПД
"""

# Листы в карточки

problems_list = dmc.List(
                spacing="sm",
                size='sm',
                children=[
                    dmc.ListItem(
                        (
                            "Невозможно корректно рассчитать "
                            "себестоимость продаж и "
                            "маржинальность."
                        )
                    ),
                    dmc.ListItem(
                        (
                            "Отсутствуют данные для "
                            "планирования и анализа."
                        )
                    ),
                    dmc.ListItem(
                        (
                            "Бухгалтерия не может корректно "
                            "списывать расходы."
                        )
                    ),
                    dmc.ListItem(
                        (
                            "Переплата налогов вследствие "
                            "ошибок учёта."
                        )
                    ),
                ],
            )

reasons_list =  dmc.List(
                    spacing="sm",
                    size='sm',
                    children=[

                        dmc.ListItem(
                            (
                                "Нет единой базы данных "
                                "номенклатур и связи между "
                                "каталогами поставщиков и WB."
                            )
                        ),
                        dmc.ListItem(
                            (
                                "Учёт ведётся в Excel. "
                                "Отсутствует единый источник "
                                "истины."
                            )
                        ),
                        dmc.ListItem(
                            (
                                "Департаменты работают "
                                "разрозненно без сквозной "
                                "системы учёта."
                            )
                        ),
                        dmc.ListItem(
                            (
                                "Нет процедур проверки данных "
                                "по приходам и списаниям."
                            )
                        ),
                        dmc.ListItem(
                            (
                                "Нет понимания работы c данными и API "
                                "маркетплейса."
                            )
                        ),
                        
                    ],
                )

method_list = dmc.List(
                        spacing="sm",
                        size='sm',
                        children=[

                            dmc.ListItem(
                                (
                                    "Создание БД по приходам, "
                                    "продажам и карточкам товаров."
                                )
                            ),

                            dmc.ListItem(
                                (
                                    "Интеграция через WB API, "
                                    "оцифровка УПД и связь "
                                    "с лотами."
                                )
                            ),

                            dmc.ListItem(
                                (
                                    "Алгоритм поиска ключей "
                                    "соответствия УПД и карточек."
                                )
                            ),

                            dmc.ListItem(
                                (
                                    "Списание товара по FIFO."
                                )
                            ),

                            dmc.ListItem(
                                (
                                    "Поиск ошибок и аномалий "
                                    "с ручной корректировкой."
                                )
                            ),
                        ],
                    )

pre_layout = dmc.Stack(
    [
        dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    dmc.Paper(
                        p="sm",
                        radius="md",
                        shadow="xs",
                        withBorder=True,
                        children= [
                            dmc.Group(
                                [
                                    DashIconify(
                                        icon="mdi:alert-circle-outline",
                                        width=28, color='red'
                                    ),

                                    dmc.Title(
                                        "Проблемы",
                                        order=3,
                                    ),
                                ],
                                mb="md",
                            ),
                            problems_list,
                        ]
                    ),
                    dmc.Paper(
                        p="sm",
                        radius="md",
                        shadow="xs",
                        withBorder=True,
                        children=[
                            dmc.Group(
                                [
                                    DashIconify(
                                        icon="mdi:database-alert-outline",
                                        width=28, color='orange'
                                    ),

                                    dmc.Title(
                                        "Причины",
                                        order=3,
                                    ),
                                ],
                                mb="md",
                            ),
                            reasons_list,                            
                        ]
                    ),
                    dmc.Paper(
                        p="sm",
                        radius="md",
                        shadow="xs",
                        withBorder=True,
                        children=[

                            dmc.Group(
                                [
                                    DashIconify(
                                        icon="mdi:cogs",
                                        width=28, color='olive'
                                    ),

                                    dmc.Title(
                                        "Реализованная методика",
                                        order=3,
                                    ),
                                ],
                                mb="md",
                            ),
                            method_list,
                            ]
                    ),
                    dmc.Paper(
                        p="sm",
                        radius="md",
                        shadow="xs",
                        withBorder=True,
                        children=[

                            dmc.Group(
                                [
                                    DashIconify(
                                        icon="mdi:information-outline",
                                        width=28, color ='brown'
                                    ),

                                    dmc.Title(
                                        "Ограничения метода",
                                        order=3, 
                                    ),
                                ],
                                mb="md",
                            ),

                            dmc.Text(
                                (
                                    "При изменении карточек товара "
                                    "или появлении новых УПД требуется "
                                    "пересчёт ключей, приходов и списаний."
                                ),
                                mb="sm",size='sm'
                            ),

                            dmc.Text(
                                (
                                    "Подход подходит для управленческого "
                                    "учёта и корректного расчёта "
                                    "себестоимости, но плохо применим "
                                    "для бухгалтерии и 1С."
                                ), size='sm'
                            ),
                        ],
                    )    
                ]
        )    
    ],  gap="xs"
)


def layout(report=None, filters=None):
    return [
        dmc.Container(pre_layout,fluid=True)
    ]