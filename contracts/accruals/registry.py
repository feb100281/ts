# contracts/accruals/registry.py

ACCRUAL_REGISTRY = {
    
    
"fixed_payments": {
        "title": "Фиксированные платежи",
        "fields": [
            {"key":"amount","label":"Сумма","type":"decimal","required":True},
            {"key":"amount_basis","label":"База суммы","type":"choice","required":True,
   },
        ],
        "defaults": {"amount_basis":"month"},
        },


 "by_bank_statement": {
        "title": "Cумма из оплаты",
        "fields": [],
        "defaults": {},
    },
 
 
}

def accrual_choices():
    return [(k, v["title"]) for k, v in ACCRUAL_REGISTRY.items()]