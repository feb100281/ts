import pandas as pd
import numpy as np
from pprint import pprint
import datetime
from conns import connect_db

TEST = {
    "cf_params": {
        "410200 Валютные операции": {
            "use": False,
            "subitems": {
                "61 | 410201 Валютная конвертация": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "410201 Валютная конвертация",
                    "subconto_id": 61,
                },
                "135 | 410202 Отражение курсовых разниц": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "410202 Отражение курсовых разниц",
                    "subconto_id": 135,
                },
            },
        },
        "311000 Взносы учредителей": {
            "use": False,
            "subitems": {
                "9 | 311100 Взносы в уставной капитал": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "311100 Взносы в уставной капитал",
                    "subconto_id": 9,
                },
                "70 | 311210 Взносы в добавочный капитал": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "311210 Взносы в добавочный капитал",
                    "subconto_id": 70,
                },
                "10 | 311200 Прочие взносы на безвозмездной основе": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "311200 Прочие взносы на безвозмездной основе",
                    "subconto_id": 10,
                },
            },
        },
        "124000 Затраты на персонал": {
            "use": True,
            "subitems": {
                "22 | 124100 Заработная плата": {
                    "use": True,
                    "means": {
                        "1M": {"use": True, "value": -796483.0},
                        "3M": {"use": False, "value": -1254554.54},
                        "6M": {"use": False, "value": -1470342.99},
                        "Manual": {"use": False, "value": [{"2026-05-01": 500.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "124100 Заработная плата",
                    "subconto_id": 22,
                },
                "34 | 124300 Подбор персонала / HR-сервисы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -637559.5},
                        "3M": {"use": False, "value": -213205.5},
                        "6M": {"use": False, "value": -111396.75},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "124300 Подбор персонала / HR-сервисы",
                    "subconto_id": 34,
                },
                "50 | 124200 Обучение и развитие персонала": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -650000.0},
                        "3M": {"use": False, "value": -216666.67},
                        "6M": {"use": False, "value": -141733.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "124200 Обучение и развитие персонала",
                    "subconto_id": 50,
                },
            },
        },
        "125000 Оплаты налогов и сборов": {
            "use": False,
            "subitems": {
                "19 | 125400 НДС": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -200000.0},
                        "3M": {"use": False, "value": -815967.67},
                        "6M": {"use": False, "value": -52830.17},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "125400 НДС",
                    "subconto_id": 19,
                },
                "16 | 125100 НДФЛ": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -576907.0},
                        "3M": {"use": False, "value": -340093.0},
                        "6M": {"use": False, "value": -399611.5},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "125100 НДФЛ",
                    "subconto_id": 16,
                },
                "18 | 125300 Соц взносы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": -168850.0},
                        "6M": {"use": False, "value": -271536.14},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "125300 Соц взносы",
                    "subconto_id": 18,
                },
                "32 | 125500 Соц взносы от НС": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -3444.11},
                        "3M": {"use": False, "value": -2273.7},
                        "6M": {"use": False, "value": -3323.73},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "125500 Соц взносы от НС",
                    "subconto_id": 32,
                },
                "20 | 125200 Налог на прибыль": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "125200 Налог на прибыль",
                    "subconto_id": 20,
                },
                "47 | 125600 Пени и штрафы по налогам": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -2712.0},
                        "3M": {"use": False, "value": -904.0},
                        "6M": {"use": False, "value": -452.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "125600 Пени и штрафы по налогам",
                    "subconto_id": 47,
                },
            },
        },
        "111000 Выручка от продажи товаров": {
            "use": False,
            "subitems": {
                "52 | 111100 Продажи через маркетплейсы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 120405997.98},
                        "3M": {"use": False, "value": 104969365.32},
                        "6M": {"use": False, "value": 98277926.19},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "111100 Продажи через маркетплейсы",
                    "subconto_id": 52,
                },
                "87 | 111200 Выкуп товара маркетплэйсом": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 3634312.75},
                        "3M": {"use": False, "value": 3345214.06},
                        "6M": {"use": False, "value": 3527300.29},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "111200 Выкуп товара маркетплэйсом",
                    "subconto_id": 87,
                },
            },
        },
        "321000 Погашение кредитов и займов": {
            "use": False,
            "subitems": {
                "28 | 321100 Погашение тела кредитов и займов": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -74857927.07},
                        "3M": {"use": False, "value": -86785967.99},
                        "6M": {"use": False, "value": -50212690.83},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "321100 Погашение тела кредитов и займов",
                    "subconto_id": 28,
                },
                "31 | 321200 Оплата процентов по кредитам и займам": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -1146397.26},
                        "3M": {"use": False, "value": -3285556.59},
                        "6M": {"use": False, "value": -4403971.73},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "321200 Оплата процентов по кредитам и займам",
                    "subconto_id": 31,
                },
                "29 | 321300 Комиссии за выдачу и использование займа": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": -3312.17},
                        "6M": {"use": False, "value": 6223.97},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "321300 Комиссии за выдачу и использование займа",
                    "subconto_id": 29,
                },
                "30 | 321400 Прочие платежи за обслуживания займов и кредитов": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": -17.84},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "321400 Прочие платежи за обслуживания займов и кредитов",
                    "subconto_id": 30,
                },
            },
        },
        "312000 Привлечение заемных средств": {
            "use": False,
            "subitems": {
                "24 | 312100 Кредиты и займы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 62000000.0},
                        "6M": {"use": False, "value": 34164819.48},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "312100 Кредиты и займы",
                    "subconto_id": 24,
                }
            },
        },
        "314000 Возврат размещённых средств": {
            "use": False,
            "subitems": {
                "45 | 314100 Возврат тела депозита": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 475328251.72},
                        "3M": {"use": False, "value": 215609866.79},
                        "6M": {"use": False, "value": 111721600.06},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "314100 Возврат тела депозита",
                    "subconto_id": 45,
                },
                "56 | 314200 Возврат выданных займов": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "314200 Возврат выданных займов",
                    "subconto_id": 56,
                },
            },
        },
        "322000 Размещение денежных средств": {
            "use": False,
            "subitems": {
                "42 | 322100 Депозиты": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -430650000.0},
                        "3M": {"use": False, "value": -213480000.0},
                        "6M": {"use": False, "value": -111731666.67},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "322100 Депозиты",
                    "subconto_id": 42,
                },
                "55 | 322200 Выданные процентные займы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -700000.0},
                        "3M": {"use": False, "value": -761666.67},
                        "6M": {"use": False, "value": -603333.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "322200 Выданные процентные займы",
                    "subconto_id": 55,
                },
            },
        },
        "410100 Перевод собственных средств": {
            "use": False,
            "subitems": {
                "40 | 410101 Перевод собственных средств": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "410101 Перевод собственных средств",
                    "subconto_id": 40,
                }
            },
        },
        "313000 Проценты по депозитам / займам": {
            "use": False,
            "subitems": {
                "57 | 313200 Проценты по займам": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "313200 Проценты по займам",
                    "subconto_id": 57,
                },
                "46 | 313100 Начисленные проценты по депозитам": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 325557.58},
                        "3M": {"use": False, "value": 169297.34},
                        "6M": {"use": False, "value": 89500.27},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "313100 Начисленные проценты по депозитам",
                    "subconto_id": 46,
                },
            },
        },
        "122000 Зачет расходов на реализацию WB": {
            "use": False,
            "subitems": {
                "82 | 122601 Штрафы с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -294771.38},
                        "3M": {"use": False, "value": -311208.81},
                        "6M": {"use": False, "value": -181449.57},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122601 Штрафы с продаж",
                    "subconto_id": 82,
                },
                "79 | 122300 Хранение с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": -2736907.93},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122300 Хранение с продаж",
                    "subconto_id": 79,
                },
                "78 | 122201 Логистика с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -409121.57},
                        "3M": {"use": False, "value": -335560.18},
                        "6M": {"use": False, "value": -10647499.38},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122201 Логистика с продаж",
                    "subconto_id": 78,
                },
                "81 | 122501 Удержания с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -7912461.24},
                        "3M": {"use": False, "value": -7313696.49},
                        "6M": {"use": False, "value": -8827944.52},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122501 Удержания с продаж",
                    "subconto_id": 81,
                },
                "97 | 122202 Логистика с выкупов": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": -428529.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122202 Логистика с выкупов",
                    "subconto_id": 97,
                },
                "83 | 122701 Корректировки с прожаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 79877563.28},
                        "3M": {"use": False, "value": 49317791.5},
                        "6M": {"use": False, "value": 24658895.75},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122701 Корректировки с прожаж",
                    "subconto_id": 83,
                },
                "80 | 122401 Приемка товара с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122401 Приемка товара с продаж",
                    "subconto_id": 80,
                },
                "77 | 122101 Комиссия маркетплэйса с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -41012731.93},
                        "3M": {"use": False, "value": -35352659.78},
                        "6M": {"use": False, "value": -32841400.9},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122101 Комиссия маркетплэйса с продаж",
                    "subconto_id": 77,
                },
                "96 | 122102 Комиссия маркетплэйса с выкупа": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -1213098.4},
                        "3M": {"use": False, "value": -1117333.59},
                        "6M": {"use": False, "value": -1177750.18},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122102 Комиссия маркетплэйса с выкупа",
                    "subconto_id": 96,
                },
                "86 | 122901 Измеение срока перечисления с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": -22862.5},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122901 Измеение срока перечисления с продаж",
                    "subconto_id": 86,
                },
                "85 | 122910 Балы по программе лояльности с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -61284.0},
                        "3M": {"use": False, "value": -55911.0},
                        "6M": {"use": False, "value": -65913.83},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122910 Балы по программе лояльности с продаж",
                    "subconto_id": 85,
                },
                "84 | 122801 Участие в программе лояльности с продаж": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -6128.4},
                        "3M": {"use": False, "value": -5591.1},
                        "6M": {"use": False, "value": -6591.38},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 45,
                    "subitem": "122801 Участие в программе лояльности с продаж",
                    "subconto_id": 84,
                },
            },
        },
        "202020 Приобретение основных средств": {
            "use": False,
            "subitems": {
                "72 | 202021 Серверы и IT-инфраструктура": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "202021 Серверы и IT-инфраструктура",
                    "subconto_id": 72,
                }
            },
        },
        "121000 Оплаты товаров для перепродажи": {
            "use": False,
            "subitems": {
                "36 | 121100 Закупка товара": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -63374991.03},
                        "3M": {"use": False, "value": -30458330.34},
                        "6M": {"use": False, "value": -19528001.01},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "121100 Закупка товара",
                    "subconto_id": 36,
                },
                "48 | 121200 Логистика и доставка товара": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -59000.0},
                        "3M": {"use": False, "value": -19666.67},
                        "6M": {"use": False, "value": -123023.78},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "121200 Логистика и доставка товара",
                    "subconto_id": 48,
                },
                "54 | 121300 Упаковка и расходные материалы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": -6966.67},
                        "6M": {"use": False, "value": -3483.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "121300 Упаковка и расходные материалы",
                    "subconto_id": 54,
                },
                "58 | 121400 Таможенные платежи и оформление": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "121400 Таможенные платежи и оформление",
                    "subconto_id": 58,
                },
            },
        },
        "123000 Накладные и корпоративные расходы": {
            "use": False,
            "subitems": {
                "21 | 123100 Комисии банков": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -177119.55},
                        "3M": {"use": False, "value": -92910.41},
                        "6M": {"use": False, "value": -58370.99},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123100 Комисии банков",
                    "subconto_id": 21,
                },
                "37 | 123500 Аренда помещений": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -308000.0},
                        "3M": {"use": False, "value": -400666.67},
                        "6M": {"use": False, "value": -288833.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123500 Аренда помещений",
                    "subconto_id": 37,
                },
                "49 | 123700 Цифровые сервисы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -32360.0},
                        "3M": {"use": False, "value": -71149.65},
                        "6M": {"use": False, "value": -78552.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123700 Цифровые сервисы",
                    "subconto_id": 49,
                },
                "33 | 123200 Бухгалтерские услуги": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -303000.0},
                        "3M": {"use": False, "value": -324666.67},
                        "6M": {"use": False, "value": -318160.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123200 Бухгалтерские услуги",
                    "subconto_id": 33,
                },
                "62 | 123920 Оборудование и техника": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": 0.0},
                        "6M": {"use": False, "value": 0.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123920 Оборудование и техника",
                    "subconto_id": 62,
                },
                "53 | 123900 Маркетинг и продвижение": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -45000.0},
                        "3M": {"use": False, "value": -71733.33},
                        "6M": {"use": False, "value": -139925.83},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123900 Маркетинг и продвижение",
                    "subconto_id": 53,
                },
                "59 | 123910 Транспортные расходы (ГСМ)": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -50000.0},
                        "3M": {"use": False, "value": -16666.67},
                        "6M": {"use": False, "value": -8333.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123910 Транспортные расходы (ГСМ)",
                    "subconto_id": 59,
                },
                "63 | 123930 Хоз. материалы и канцтовары": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -6690.0},
                        "3M": {"use": False, "value": -4010.0},
                        "6M": {"use": False, "value": -2005.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123930 Хоз. материалы и канцтовары",
                    "subconto_id": 63,
                },
                "69 | 123940 Операции по корпоративной карте": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -389094.57},
                        "3M": {"use": False, "value": -170561.18},
                        "6M": {"use": False, "value": -95806.92},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123940 Операции по корпоративной карте",
                    "subconto_id": 69,
                },
                "38 | 123600 Подотчётные суммы и командировки": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": -100000.0},
                        "6M": {"use": False, "value": -179711.67},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123600 Подотчётные суммы и командировки",
                    "subconto_id": 38,
                },
                "35 | 123400 Консалтинг и аналитические услуги": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -300000.0},
                        "3M": {"use": False, "value": -504266.67},
                        "6M": {"use": False, "value": -386733.33},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123400 Консалтинг и аналитические услуги",
                    "subconto_id": 35,
                },
                "75 | 123950 Штрафы и компенсации по претензиям": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": 0.0},
                        "3M": {"use": False, "value": -5000.0},
                        "6M": {"use": False, "value": -2500.0},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123950 Штрафы и компенсации по претензиям",
                    "subconto_id": 75,
                },
                "60 | 123010 Юридические / регистрационные расходы": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -134000.0},
                        "3M": {"use": False, "value": -119516.67},
                        "6M": {"use": False, "value": -75061.67},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "123010 Юридические / регистрационные расходы",
                    "subconto_id": 60,
                },
            },
        },
        "202010 Инвестиции в нематериальные активы": {
            "use": False,
            "subitems": {
                "68 | 202011 Разработка собственного ПО": {
                    "use": False,
                    "means": {
                        "1M": {"use": False, "value": -53297250.0},
                        "3M": {"use": False, "value": -20415305.55},
                        "6M": {"use": False, "value": -10707652.78},
                        "Manual": {"use": False, "value": [{"2026-01-01": 0.0}]},
                        "M fixed": {"use": False, "value": 0.0},
                    },
                    "acc_id": 3,
                    "subitem": "202011 Разработка собственного ПО",
                    "subconto_id": 68,
                }
            },
        },
    }
}


def insert_results(conn, rows):
    with conn.cursor() as cur:
        with cur.copy(
            """
            COPY public.budget_gl (
                "date",
                dt,
                cr,
                description,
                chapter,
                acc_id,
                contract_id,
                subconto_id,
                version_id
            )
            FROM STDIN
            """
        ) as copy:
            for row in rows:
                copy.write_row(row)

    conn.commit()


def make_forecast(conn, date_from, date_to, d: dict, instance_id):
    dates = pd.date_range(date_from, date_to, freq="ME")
    rows = []

    def append_rows(acc_id, subconto_id, mean_name, value, subitem_name):
        if mean_name == "Manual":
            # ожидаем value вида:
            # {"2026-01-31": 0.0, "2026-02-28": 10.0}
            # или список [{"2026-01-31": 0.0}]
            if isinstance(value, dict):
                for dt, amount in value.items():
                    rows.append(
                        (
                            str(pd.Timestamp(dt).date()),
                            0,
                            int(round(float(amount) * 100, 0)),
                            str(subitem_name),
                            "Прогноз расходов",
                            int(acc_id),
                            None,
                            int(subconto_id),
                            int(instance_id),
                        )
                    )

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for dt, amount in item.items():
                            rows.append(
                                (
                                    str(pd.Timestamp(dt).date()),
                                    0,
                                    int(round(float(amount) * 100, 0)),
                                    str(subitem_name),
                                    "Прогноз расходов",
                                    int(acc_id),
                                    None,
                                    int(subconto_id),
                                    int(instance_id),
                                )
                            )
        else:
            # value = одно число, размазываем по всем месяцам
            amount = abs(int(round(float(value) * 100, 0)))

            rows.extend(
                (
                    str(dt.date()),
                    0,
                    amount,
                    str(subitem_name),
                    "Прогноз расходов",
                    int(acc_id),
                    None,
                    int(subconto_id),
                    int(instance_id),
                )
                for dt in dates
            )

    for item_name, item_data in d["cf_params"].items():
        if not item_data.get("use"):
            continue

        for subitem_name, subitem_data in item_data.get("subitems", {}).items():
            if not subitem_data.get("use"):
                continue

            for mean_name, mean_data in subitem_data.get("means", {}).items():
                if not mean_data.get("use"):
                    continue

                value = mean_data.get("value")
                acc_id = subitem_data.get("acc_id")
                subconto_id = subitem_data.get("subconto_id")

                append_rows(acc_id, subconto_id, mean_name, value, subitem_name)

    insert_results(conn, rows)
    return rows


def main(conn,**args):
    
    DATE_FROM = args['date_from']
    DATE_TO = args['date_to']
    instance = args['id']    
    make_forecast(conn, DATE_FROM, DATE_TO, TEST, instance)

    conn.close()

