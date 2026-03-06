# contracts/accruals/registry.py
from decimal import Decimal

ACCRUAL_REGISTRY = {
    
# ✅  ФИКСИРОВАННЫЕ ПЛАТЕЖИ
"fixed_payments": {
        "title": "Фиксированные платежи",
        "fields": [
            {"key":"amount","label":"Сумма","type":"decimal","required":True},
            {"key":"amount_basis","label":"База суммы","type":"choice","required":True,},
            {"key": "vat_rate", "label": "Ставка НДС, %", "type": "decimal", "required": False},
        ],
        "defaults": {"amount_basis":"month"},
        "vat_rate": Decimal("0"),
        },

# ✅  CASH BASED
 "by_bank_statement": {
        "title": "Cумма из оплаты",
        "fields": [],
        "defaults": {},
    },
 
 # ✅  АРЕНДА ПОМЕЩЕНИЙ
 "rent_premises": {
        "title": "Аренда помещений (cтавка мес.)",
        "fields": [
            {"key": "bap", "label": "БАП", "type": "decimal", "required": True},
            {"key": "ep", "label": "ЭП", "type": "decimal", "required": False},
            {"key": "calc_area", "label": "Расч. площадь", "type": "decimal", "required": True},
            {"key": "vat_rate", "label": "Ставка НДС, %", "type": "decimal", "required": False},

            {"key": "indexation_percent", "label": "Процент индексации, %", "type": "decimal", "required": False},
            {"key": "indexation_start_date", "label": "Дата начала индексации", "type": "date", "required": False},
        ],
        "defaults": {
            "ep": Decimal("0"),
             "vat_rate": Decimal("0"),
            "indexation_percent": Decimal("0"),
            "indexation_start_date": "",
        },
    },
 
 
}

def accrual_choices():
    return [(k, v["title"]) for k, v in ACCRUAL_REGISTRY.items()]