# contracts/accruals/registry.py

# contracts/accruals/registry.py

ACCRUAL_REGISTRY = {
    "fixed_payments": {
        "title": "Фиксированные платежи",
        "fields": [
            {"key": "amount", "label": "Сумма", "type": "decimal", "required": True},
            {
                "key": "vat_mode",
                "label": "НДС",
                "type": "choice",
                "required": True,
                "choices": [
                    {"value": "included", "label": "НДС включён"},
                    {"value": "excluded", "label": "НДС сверху"},
                    {"value": "exempt", "label": "Без НДС"},
                ],
            },
        ],
        "defaults": {"vat_mode": "included"},
    },

   
}


def accrual_choices():
    return [(k, v["title"]) for k, v in ACCRUAL_REGISTRY.items()]