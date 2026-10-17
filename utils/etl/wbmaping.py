# MAPPING ОПЕРАЦИЙ WB

FIELD = {
    "retail_price": {
        "acc_ws":46,
        "acc_pl":48,
        "acc_vat":80,
        "subconto_ws":(52,87),
        "sunconto_pl":(90,91),
        "sunconto_vat":(52,87),
        "ns":"11111111-1111-1111-1111-111111111111"        
    },
    "retail_amount": {
        "acc_ws":91,        
        "subconto_ws":(52,87),        
        "ns":"11111111-1111-1111-1111-111111111113"    
    },
    "ppvz_for_pay": {
        "acc_ws":92,        
        "subconto_ws":(52,87),        
        "ns":"11111111-1111-1111-1111-111111111114"    
    },
    "comission": {
        "acc_ws":46,
        "acc_pl":59,
        "acc_vat":81,
        "subconto_ws":(52,87),
        "sunconto_pl":(90,91),
        "sunconto_vat":(52,87),
        "ns":"11111111-1111-1111-1111-111111111115"        
    },
    "delivery_rub": {
        "acc_ws":46,
        "acc_pl":60,
        "acc_vat":82,
        "subconto_ws":(78,97),
        "sunconto_pl":(108,109),
        "sunconto_vat":(78,97),
        "ns":"11111111-1111-1111-1111-111111111116"        
    },
    "storage_fee": {
        "acc_ws":46,
        "acc_pl":60,
        "acc_vat":82,
        "subconto_ws":(79,98),
        "sunconto_pl":(111,112),
        "sunconto_vat":(79,98),
        "ns":"11111111-1111-1111-1111-111111111117"        
    },
    "acceptance": {
        "acc_ws":46,
        "acc_pl":60,
        "acc_vat":82,
        "subconto_ws":(80,99),
        "sunconto_pl":(114,115),
        "sunconto_vat":(80,99),
        "ns":"11111111-1111-1111-1111-111111111118"        
    },
    "deduction": {
        "acc_ws":46,
        "acc_pl":62,
        "acc_vat":82,
        "subconto_ws":(81,100),
        "sunconto_pl":(118,119),
        "sunconto_vat":(81,100),
        "ns":"11111111-1111-1111-1111-111111111119"        
    },
    "penalty": {
        "acc_ws":46,
        "acc_pl":60,        
        "subconto_ws":(82,101),
        "sunconto_pl":(121,122),
        "ns":"11111111-1111-1111-1111-111111111120"        
    },
    "additional_payment": {
        "acc_ws":46,
        "acc_pl":49,        
        "subconto_ws":(83,102),
        "sunconto_pl":(125,126),
        "ns":"11111111-1111-1111-1111-111111111121"        
    },
    "cashback_commission_change": {
        "acc_ws":46,
        "acc_pl":62,
        "acc_vat":82,
        "subconto_ws":(84,103),
        "sunconto_pl":(127,128),
        "sunconto_vat":(84,103),
        "ns":"11111111-1111-1111-1111-111111111122"     
    },
    "cashback_amount": {
        "acc_ws":46,
        "acc_pl":62,
        # "acc_vat":82,
        "subconto_ws":(85,104),
        "sunconto_pl":(129,130),
        # "sunconto_vat":(84,103),
        "ns":"11111111-1111-1111-1111-111111111123"     
    },
    "payment_schedule": {
        "acc_ws":46,
        "acc_pl":62,        
        "subconto_ws":(86,95),
        "sunconto_pl":(132,133),
        "ns":"11111111-1111-1111-1111-111111111124"        
    },
    
}




CTEs = {
   
    "sale_wb": {
        "field": "retail_price",
        "ns": "11111111-1111-1111-1111-111111111111",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 46,
        "description": "Продажи / Возвраты",
        "parent": None,      
        "subconto":52  
    },
    "sale_pl": {
        "field": "retail_price",
        "ns": "11111111-1111-1111-1111-111111111112",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 50,
        "description": "Отражение выручки в PL",
        "parent": "sale_wb",
        "subconto":None          
    },
    "sale_vat": {
        "field": "retail_price",
        "ns": "11111111-1111-1111-1111-111111111113",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 80,
        "description": "Выделение НДС с продаж / возвратов",
        "parent": "sale_wb",   
        "subconto":None      
    },
    
    "comission_wb": {
        "field": "ppvz_for_pay",
        "ns": "11111111-1111-1111-1111-111111111114",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 46,
        "description": "Комиссия WB",
        "parent": "sale_wb",
        "subconto":77  
        
    },
    "comission_pl": {
        "field": "ppvz_for_pay",
        "ns": "11111111-1111-1111-1111-111111111115",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 59,
        "description": "Отражение комисии WB в PL",
        "parent": "comission_wb",
        "subconto":None
       
    },
    "comission_vat": {
        "field": "ppvz_for_pay",
        "ns": "11111111-1111-1111-1111-111111111116",
        "agg": ["report_type", "dtn_id"],
        "acc_id": 31,
        "description": "Выделение НДС с комиссии WB ",
        "parent": "comission_wb",
        "subconto":None 
    },
   
    "logistic_wb": {
        "field": "delivery_rub",
        "ns": "11111111-1111-1111-1111-111111111117",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Логистика WB",
        "parent": "sale_wb",
        "subconto":78
       
    },
    "logistic_pl": {
        "field": "delivery_rub",
        "ns": "11111111-1111-1111-1111-111111111118",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов на логистику в PL",
        "parent": "logistic_wb",
        "subconto":None 
        
    },
    "logistic_vat": {
        "field": "delivery_rub",
        "ns": "11111111-1111-1111-1111-111111111119",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "Выделение НДС с логистики",
        "parent": "logistic_wb",
        "subconto":None
    },
   
    "storage_wb": {
        "field": "storage_fee",
        "ns": "11111111-1111-1111-1111-111111111120",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Хранение WB",
        "parent": "sale_wb",
        "subconto":79
    },
    "storage_pl": {
        "field": "storage_fee",
        "ns": "11111111-1111-1111-1111-111111111121",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов WB по хранению в PL",
        "parent": "storage_wb",
        "subconto":None
    },
    "storage_vat": {
        "field": "storage_fee",
        "ns": "11111111-1111-1111-1111-111111111122",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "Выделение НДС с Хранения WB",
        "parent": "storage_wb",
        "subconto":None
    },
   
    "acceptance_wb": {
        "field": "acceptance",
        "ns": "11111111-1111-1111-1111-111111111123",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Приемка WB",
        "parent": "sale_wb",
        "subconto":80 
    },
    "acceptance_pl": {
        "field": "acceptance",
        "ns": "11111111-1111-1111-1111-111111111124",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по приемки WB в PL",
        "parent": "acceptance_wb",
        "subconto":None
    },
    "acceptance_vat": {
        "field": "acceptance",
        "ns": "11111111-1111-1111-1111-111111111125",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "Выделение НДС с расходов по приемке WB",
        "parent": "acceptance_wb",
        "subconto":None 
    },
   
    "deduction_wb": {
        "field": "deduction",
        "ns": "11111111-1111-1111-1111-111111111126",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Ужержания WB",
        "parent": "sale_wb",
        "subconto":81 
    },
    "deduction_pl": {
        "field": "deduction",
        "ns": "11111111-1111-1111-1111-111111111127",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по Удержаниям WB в PL",
        "parent": "deduction_wb",
        "subconto":None 
    },
    "deduction_vat": {
        "field": "deduction",
        "ns": "11111111-1111-1111-1111-111111111128",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "НДС с удержаний WB",
        "parent": "deduction_wb",
        "subconto":None 
    },
    
    "penalty_wb": {
        "field": "penalty",
        "ns": "11111111-1111-1111-1111-111111111129",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Штрафы WB",
        "parent": "sale_wb",
        "subconto":82
    },
    "penalty_pl": {
        "field": "penalty",
        "ns": "11111111-1111-1111-1111-111111111130",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по штрафам WB в pl",
        "parent": "penalty_wb",
        "subconto":None
    },
    
    "correction_wb": {
        "field": "additional_payment",
        "ns": "11111111-1111-1111-1111-111111111131",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Корректировки WB",
        "parent": "sale_wb",
        "subconto":83
    },
    "correction_pl": {
        "field": "additional_payment",
        "ns": "11111111-1111-1111-1111-111111111132",
        "agg": [
            "report_type",
        ],
        "acc_id": 52,
        "description": "Отражение корректировок WB в pl",
        "parent": "correction_wb",
        "subconto":None
    },
    
    "cashbackcommissionchange_wb": {
        "field": "cashback_commission_change",
        "ns": "11111111-1111-1111-1111-111111111133",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Программа лояльности участие WB",
        "parent": "sale_wb",
        "subconto":84 
    },
    "cashbackcommissionchange_pl": {
        "field": "cashback_commission_change",
        "ns": "11111111-1111-1111-1111-111111111134",
        "agg": [
            "report_type",
        ],
        "acc_id": 60,
        "description": "Отражение расходов по участию в ПЛ WB в PL",
        "parent": "cashbackcommissionchange_wb",
        "subconto":None 
    },
    "cashbackcommissionchange_vat": {
        "field": "cashback_commission_change",
        "ns": "11111111-1111-1111-1111-111111111135",
        "agg": [
            "report_type",
        ],
        "acc_id": 31,
        "description": "НДС по участию в ПЛ WB",
        "parent": "cashbackcommissionchange_wb",
        "subconto":None 
    },
    
    "cashbackamount_wb": {
        "field": "cashback_amount",
        "ns": "11111111-1111-1111-1111-111111111136",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Балы за ПЛ WB",
        "parent": "sale_wb",
        "subconto":85
    },
    "cashbackamount_pl": {
        "field": "cashback_amount",
        "ns": "11111111-1111-1111-1111-111111111137",
        "agg": [
            "report_type",
        ],
        "acc_id": 52,
        "description": "Отражение удержания баллов за ПЛ  WB в pl",
        "parent": "cashbackamount_wb",
        "subconto":None
    },
    
    "paymentschedule_wb": {
        "field": "payment_schedule",
        "ns": "11111111-1111-1111-1111-111111111138",
        "agg": [
            "report_type",
        ],
        "acc_id": 46,
        "description": "Комиссия за досрочный перевод",
        "parent": "sale_wb",
        "subconto":86
    },
    "paymentschedule_pl": {
        "field": "payment_schedule",
        "ns": "11111111-1111-1111-1111-111111111139",
        "agg": [
            "report_type",
        ],
        "acc_id": 52,
        "description": "Отражение комиссии за досроч перевод  WB в pl",
        "parent": "paymentschedule_wb",
        "subconto":None
    },
}