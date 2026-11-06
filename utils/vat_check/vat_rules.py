# # utils/vat_check/vat_rules.py
# from typing import Any

# REDUCED_VAT_RATE = 10.0

# # Для внутренней эвристики по ТН ВЭД
# CHILDREN_10_VAT_TNVED_RULES: list[dict[str, Any]] = [
#     {"name": "Игрушки детские", "prefixes": ["950300"], "exclude_prefixes": []},
#     {"name": "Коляски детские", "prefixes": ["871500"], "exclude_prefixes": []},
#     {"name": "Одежда и принадлежности для детей младшего возраста, трикотажные", "prefixes": ["6111"], "exclude_prefixes": []},
#     {"name": "Одежда и принадлежности для детей младшего возраста, текстильные", "prefixes": ["6209"], "exclude_prefixes": []},

#     # спорные/расширенные группы — только если ты осознанно хочешь их включать
#     # {"name": "Детская одежда, верхняя трикотажная", "prefixes": ["6103", "6104", "6105", "6106", "6107", "6108"], "exclude_prefixes": []},
#     # {"name": "Детская обувь", "prefixes": ["6401", "6402", "6403", "6404", "6405"], "exclude_prefixes": []},
# ]

# # Можно сразу отметить, какие правила “жесткие”, а какие “эвристика”
# STRICT_CHILDREN_PREFIXES = {"950300", "871500", "6111", "6209"}
# HEURISTIC_CHILDREN_PREFIXES = {"6103", "6104", "6105", "6106", "6107", "6108", "6401", "6402", "6403", "6404", "6405"}




# utils/vat_check/vat_rules.py
from typing import Any

REDUCED_VAT_RATE = 10.0

# Для внутренней эвристики по ТН ВЭД
CHILDREN_10_VAT_TNVED_RULES: list[dict[str, Any]] = [
    {"name": "Игрушки детские", "prefixes": ["950300"], "exclude_prefixes": []},
    {"name": "Коляски детские", "prefixes": ["871500"], "exclude_prefixes": []},
    {"name": "Одежда и принадлежности для детей младшего возраста, трикотажные", "prefixes": ["6111"], "exclude_prefixes": []},
    {"name": "Одежда и принадлежности для детей младшего возраста, текстильные", "prefixes": ["6209"], "exclude_prefixes": []},
]

# Детские значения поля "Пол" из характеристик
CHILDREN_GENDER_VALUES = {"детский", "детская", "детское", "для детей", "мальчик", "девочка", "унисекс детский"}

def is_children_by_gender(characteristics: list[dict[str, Any]]) -> bool:
    """
    Проверяет, является ли товар детским по характеристике "Пол".
    """
    if not characteristics:
        return False
    
    for char in characteristics:
        name = str(char.get("name", "")).strip().lower()
        if name != "пол":
            continue
        
        value = char.get("value", [])
        if not value:
            continue
        
        # value может быть строкой или списком
        if isinstance(value, list):
            values = [str(v).strip().lower() for v in value]
        else:
            values = [str(value).strip().lower()]
        
        for v in values:
            if v in CHILDREN_GENDER_VALUES:
                return True
    
    return False


def is_children_product_by_tnved(tnved_code: str | None) -> bool:
    """
    Проверяет, является ли товар детским по ТН ВЭД.
    """
    if not tnved_code:
        return False
    
    from budget.reporting.pdf.services.vat_validation_service import _normalize_tnved_code, _match_tnved_rule
    
    normalized = _normalize_tnved_code(tnved_code)
    if not normalized:
        return False
    
    matched = _match_tnved_rule(normalized, CHILDREN_10_VAT_TNVED_RULES)
    return matched is not None


def should_have_reduced_vat_rate(
    tnved_code: str | None,
    characteristics: list[dict[str, Any]] | None,
) -> bool:
    """
    Определяет, должен ли товар облагаться по льготной ставке 10%.
    """
    # Если ТН ВЭД явно детский
    if is_children_product_by_tnved(tnved_code):
        return True
    
    # Если характеристика "Пол" указывает на детский
    if characteristics and is_children_by_gender(characteristics):
        return True
    
    return False