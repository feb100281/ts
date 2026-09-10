# # inventories/reporting/map/map_config.py
# from __future__ import annotations
# from pathlib import Path

# # Цветовая схема
# COLOR_BG = "#F4F8F6"
# COLOR_BASE = "#E6ECE9"
# COLOR_TEXT = "#18352F"
# COLOR_MUTED = "#60746D"
# COLOR_PRIMARY = "#006B4F"

# # Российские складские регионы
# WAREHOUSE_REGIONS = [
#     "Центральный",
#     "Приволжский",
#     "Уральский",
#     "Южный и Северо-Кавказский",
#     "Дальневосточный и Сибирский",
#     "Северо-Западный",
# ]

# # Координаты для подписей регионов (x, y)
# LABEL_POINTS = {
#     "Центральный": (38, 55),
#     "Приволжский": (50, 55),
#     "Уральский": (63, 60),
#     "Южный и Северо-Кавказский": (43, 45),
#     "Дальневосточный и Сибирский": (105, 61),
#     "Северо-Западный": (32, 61),  # Санкт-Петербург
# }

# # Ключевые слова для определения регионов из shapefile
# DISTRICT_KEYWORDS = {
#     "Центральный": [
#         "moscow", "moskva", "belgorod", "bryansk", "vladimir", "voronezh",
#         "ivanovo", "kaluga", "kostroma", "kursk", "lipetsk", "oryol",
#         "orel", "ryazan", "smolensk", "tambov", "tver", "tula", "yaroslavl",
#     ],
#     "Приволжский": [
#         "bashkortostan", "mari", "mordovia", "tatarstan", "udmurt",
#         "chuvash", "perm", "kirov", "nizhny", "novgorod", "orenburg",
#         "penza", "samara", "saratov", "ulyanovsk",
#     ],
#     "Уральский": [
#         "kurgan", "sverdlovsk", "tyumen", "chelyabinsk",
#         "khanty", "mansiy", "yamal", "nenets",
#     ],
#     "Южный и Северо-Кавказский": [
#         "adygey", "adygea", "kalmyk", "crimea", "krasnodar", "astrakhan",
#         "volgograd", "rostov", "dagestan", "ingush", "kabardin",
#         "balkar", "karachay", "cherkess", "ossetia", "chechnya",
#         "stavropol",
#     ],
#     "Дальневосточный и Сибирский": [
#         "altay", "altai", "buryat", "tuva", "tyva", "khakass",
#         "krasnoyarsk", "irkutsk", "kemerovo", "novosibirsk", "omsk",
#         "tomsk", "zabaykal", "transbaikal", "sakha", "yakutia",
#         "kamchatka", "primorye", "primorsky", "khabarovsk", "amur",
#         "magadan", "sakhalin", "jewish", "chukotka",
#     ],
#     "Северо-Западный": [
#         "st. petersburg", "saint petersburg", "leningrad", "kaliningrad",
#         "murmansk", "arkhangelsk", "novgorod", "pskov", "karelia",
#         "komi", "vologda",
#     ],
# }

# # Страны для отображения (сопоставление названий в данных и в shapefile)
# COUNTRIES_CONFIG = {
#     "Армения": {
#         "name_en": "Armenia",
#         "center": (45, 40.5),
#     },
#     "Беларусь": {
#         "name_en": "Belarus",
#         "center": (28, 53.5),
#     },
#     "Грузия": {
#         "name_en": "Georgia",
#         "center": (43.5, 42.2),
#     },
#     "Казахстан": {
#         "name_en": "Kazakhstan",
#         "center": (67, 48),
#     },
#     "Узбекистан": {
#         "name_en": "Uzbekistan",
#         "center": (66, 41.5),
#     },
#     "Таджикистан": {
#         "name_en": "Tajikistan",
#         "center": (71, 38.5),
#     },
# }

# # Пути к shapefile
# def get_russia_shapefile_path() -> Path:
#     current_file = Path(__file__).resolve()
#     # Из папки map поднимаемся на уровень выше (в reporting)
#     # и затем идем в assets/maps/russia_regions
#     return (
#         current_file.parent.parent
#         / "assets"
#         / "maps"
#         / "russia_regions"
#         / "ne_10m_admin_1_states_provinces.shp"
#     )

# def get_world_shapefile_path() -> Path:
#     current_file = Path(__file__).resolve()
#     return (
#         current_file.parent.parent
#         / "assets"
#         / "maps"
#         / "world"
#         / "ne_110m_admin_0_countries.shp"
#     )




# inventories/reporting/map/map_config.py
from __future__ import annotations
from pathlib import Path

COLOR_BG = "#F4F8F6"
COLOR_BASE = "#E3ECE8"
COLOR_TEXT = "#18352F"
COLOR_MUTED = "#60746D"
COLOR_PRIMARY = "#006B4F"
COLOR_BORDER = "#C5D2CC"
COLOR_BORDER_DARK = "#8FA59C"
COLOR_LABEL_BG = "#FAFCFA"

WAREHOUSE_REGIONS = [
    "Центральный",
    "Приволжский",
    "Уральский",
    "Южный и Северо-Кавказский",
    "Дальневосточный и Сибирский",
    "Северо-Западный",
]

LABEL_POINTS = {
    "Северо-Западный": (31.5, 60.5),
    "Центральный": (39.0, 56.2),
    "Приволжский": (51.0, 54.6),
    "Уральский": (64.5, 59.6),
    "Южный и Северо-Кавказский": (42.0, 44.5),
    "Дальневосточный и Сибирский": (107.0, 61.0),
}

COUNTRIES_CONFIG = {
    "Беларусь": {
        "name_en": "Belarus",
        "center": (27.0, 53.0),
    },
    "Грузия": {
        "name_en": "Georgia",
        "center": (43.0, 42.4),
    },
    "Армения": {
        "name_en": "Armenia",
        "center": (45.2, 40.2),
    },
    "Казахстан": {
        "name_en": "Kazakhstan",
        "center": (66.0, 48.8),
    },
    "Узбекистан": {
        "name_en": "Uzbekistan",
        "center": (64.8, 41.3),
    },
    "Таджикистан": {
        "name_en": "Tajikistan",
        "center": (72.3, 38.9),
    },
}

DISTRICT_KEYWORDS = {
    "Центральный": [
        "moscow", "moskva", "belgorod", "bryansk", "vladimir", "voronezh",
        "ivanovo", "kaluga", "kostroma", "kursk", "lipetsk", "oryol",
        "orel", "ryazan", "smolensk", "tambov", "tver", "tula", "yaroslavl",
    ],
    "Приволжский": [
        "bashkortostan", "mari", "mordovia", "tatarstan", "udmurt",
        "chuvash", "perm", "kirov", "nizhny", "novgorod", "orenburg",
        "penza", "samara", "saratov", "ulyanovsk",
    ],
    "Уральский": [
        "kurgan", "sverdlovsk", "tyumen", "chelyabinsk",
        "khanty", "mansiy", "yamal", "nenets",
    ],
    "Южный и Северо-Кавказский": [
        "adygey", "adygea", "kalmyk", "crimea", "krasnodar", "astrakhan",
        "volgograd", "rostov", "dagestan", "ingush", "kabardin",
        "balkar", "karachay", "cherkess", "ossetia", "chechnya",
        "stavropol",
    ],
    "Дальневосточный и Сибирский": [
        "altay", "altai", "buryat", "tuva", "tyva", "khakass",
        "krasnoyarsk", "irkutsk", "kemerovo", "novosibirsk", "omsk",
        "tomsk", "zabaykal", "transbaikal", "sakha", "yakutia",
        "kamchatka", "primorye", "primorsky", "khabarovsk", "amur",
        "magadan", "sakhalin", "jewish", "chukotka",
    ],
    "Северо-Западный": [
        "st. petersburg", "saint petersburg", "leningrad", "kaliningrad",
        "murmansk", "arkhangelsk", "novgorod", "pskov", "karelia",
        "komi", "vologda",
    ],
}


def get_russia_shapefile_path() -> Path:
    current_file = Path(__file__).resolve()
    return (
        current_file.parent.parent
        / "assets"
        / "maps"
        / "russia_regions"
        / "ne_10m_admin_1_states_provinces.shp"
    )


def get_world_shapefile_path() -> Path:
    current_file = Path(__file__).resolve()
    return (
        current_file.parent.parent
        / "assets"
        / "maps"
        / "world"
        / "ne_110m_admin_0_countries.shp"
    )