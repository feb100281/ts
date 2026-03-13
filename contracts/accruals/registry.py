# contracts/accruals/registry.py
from decimal import Decimal

ACCRUAL_REGISTRY = {


    "fixed_payments": {
        "title": "Фиксированные платежи",
        "fields": [
            {"key": "amount", "label": "Сумма", "type": "decimal", "required": True},
            {"key": "amount_basis", "label": "База суммы", "type": "choice", "required": True},
            {"key": "vat_rate", "label": "Ставка НДС, %", "type": "decimal", "required": False},
        ],
        "defaults": {
            "amount_basis": "month",
            "vat_rate": Decimal("0"),
        },
    },



    
    "by_bank_statement": {
    "title": "Cумма из оплаты",
    "fields": [
        {"key": "vat_rate", "label": "Ставка НДС, %", "type": "decimal", "required": False},
    ],
    "defaults": {
        "vat_rate": Decimal("0"),
    },
},
    
    
    

    "rent_premises": {
        "title": "Аренда помещений (ставка мес.)",
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
    
    
    
    "deposit_by_bank_statement": {
        "title": "Депозит / по выписке",
        "fields": [],
        "defaults": {
            "placement_cf_code": "322100",
            "interest_cf_code": "313100",
            "return_cf_code": "314100",
        },
    },
    
    
    "own_funds_transfer": {
            "title": "Перевод собственных средств",
            "fields": [],
            "defaults": {},
        },
    
    
    "annual_payment": {
        "title": "Ежегодный платеж",
        "fields": [
            {"key": "amount", "label": "Сумма", "type": "decimal", "required": True},
            {"key": "payment_month", "label": "Месяц начисления", "type": "integer", "required": True},
            {"key": "vat_rate", "label": "Ставка НДС, %", "type": "decimal", "required": False},
        ],
        "defaults": {
            "payment_month": 1,
            "vat_rate": Decimal("0"),
        },
    },
    
    
    "fixed_total_by_period": {
            "title": "Фиксированная сумма за весь период",
            "fields": [
                {"key": "amount", "label": "Сумма за весь период", "type": "decimal", "required": True},
                {"key": "vat_rate", "label": "Ставка НДС, %", "type": "decimal", "required": False},
            ],
            "defaults": {
                "vat_rate": Decimal("0"),
            },
        },
    
    
    
    "loan_by_bank_statement": {
            "title": "Заем / по выписке + начисление процентов",
            "fields": [
                {"key": "annual_rate", "label": "Ставка, % годовых", "type": "decimal", "required": True},
                {"key": "vat_rate", "label": "Ставка НДС, %", "type": "decimal", "required": False},
                {"key": "withholding_ndfl", "label": "Удерживать НДФЛ", "type": "boolean", "required": False},

                {"key": "issue_cf_code", "label": "CF код выдачи займа", "type": "string", "required": True},
                {"key": "principal_return_cf_code", "label": "CF код возврата тела займа", "type": "string", "required": True},
                {"key": "interest_payment_cf_code", "label": "CF код оплаты процентов", "type": "string", "required": False},

                {"key": "interest_start_mode", "label": "Начало начисления процентов", "type": "choice", "required": True},
                {"key": "day_count_basis", "label": "База дней", "type": "choice", "required": True},
            ],
            "defaults": {
                "annual_rate": Decimal("14.5"),
                "vat_rate": Decimal("0"),
                "withholding_ndfl": False,
                "issue_cf_code": "312100",
                "principal_return_cf_code": "321100",
                "interest_payment_cf_code": "321200",
                "interest_start_mode": "next_day",
                "day_count_basis": "365",
            },
        },

            
    
}


def accrual_choices():
    return [(k, v["title"]) for k, v in ACCRUAL_REGISTRY.items()]