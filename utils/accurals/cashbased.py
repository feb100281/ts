# # utils/accurals/cashbased.py
# #--------------------------
# # Начисления CashBased
# #--------------------------
# import pandas as pd
# import numpy as np
# from psycopg.types.json import Jsonb

# # распределяет по GL за 1 проход сf по счетам.
# def cash_based_distibution(conn,**args):
    
#     param = args['params_json']        
#     ignored = param.get('Игнорировать', False)
#     where = param.get('Фильтр', "")
    
#     if ignored:
#         return
   
    
#     SQL = """
#     INSERT INTO gl.accural_distribution(
# 	p_fn_id, pid, date_from, contract_id, condition_id, 
#     company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat, 
#     cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl, acc_bs, 
#     subconto_bs, dt_bs, cr_bs)
#     SELECT 
#     p_fn_id, pid, date_from, contract_id, condition_id, 
#     company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat, 
#     cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl, acc_bs, 
#     subconto_bs, dt_bs, cr_bs   
     
#     FROM gl.cash_based_distribution(
#         %s,
#         %s,
#         %s,
#         %s,
#         %s,
#         %s::jsonb,        
#         %s,
#         %s,
#         %s,
#         %s,
#         %s,
#         %s,        
#         %s,
#         %s
#     );
    
#     """    
    
#     params = (
#     args["contract_id"],
#     args["acc_st_id"],
#     84, # РАСЧЕТЫ ПО НДС с arccurals
#     args["acc_pl_id"],
#     args["acc_bs_id"],
#     Jsonb(args["vat_json"] or {}),   # dict
#     args["vat_mode"],    
#     args["subconto_bs_id"],
#     args["subconto_pl_id"],
#     1,   # id Company
#     args["condition_id"],    
#     args["fn_id"],
#     args["date_start"],    
#     args["date_finish"]  
#     )
    
#     with conn.cursor() as cur:
#         cur.execute(SQL,params)
#     conn.commit()
    
#     return 'pd.read_sql(SQL,params=params,con=conn)'


# def main(conn, **args):    
#     print(cash_based_distibution(conn, **args))
    

# if __name__ == "__main__":
#     main()





# utils/accurals/cashbased.py
# --------------------------
# Начисления CashBased
# --------------------------

import pandas as pd
from psycopg.types.json import Jsonb


def build_sql_params(args):
    return (
        args["contract_id"],
        args["acc_st_id"],
        84,  # РАСЧЕТЫ ПО НДС с accruals
        args["acc_pl_id"],
        args["acc_bs_id"],
        Jsonb(args["vat_json"] or {}),
        args["vat_mode"],
        args["subconto_bs_id"],
        args["subconto_pl_id"],
        1,  
        args["condition_id"],
        args["fn_id"],
        args["date_start"],
        args["date_finish"],
    )




def preview(conn, **args):
    """
    Preview для кнопки 'Показать начисления'.
    Ничего не пишет в БД.
    """
    param = args.get("params_json") or {}
    ignored = param.get("Игнорировать", False)

    if ignored:
        return {
            "rows": [],
            "total": 0,
            "total_net": 0,
            "total_vat": 0,
            "total_gross": 0,
            "vat_rate": None,
            "vat_mode": args.get("vat_mode"),
            "period": {
                "from": args.get("date_start"),
                "to": args.get("date_finish"),
            },
            "note": "Начисления отключены параметром 'Игнорировать'.",
        }

    sql = """
    SELECT *
    FROM gl.cash_based_distribution(
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::jsonb,
        %s::text,
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::date,
        %s::date
    );
    """

    params = build_sql_params(args)
    
    df = pd.read_sql(sql, con=conn, params=params)
    raw_rows = df.to_dict("records")

    rows = []
    for row in raw_rows:
        debit_amount = (
            row.get("dt_st")

            or 0
        )

        credit_amount = (
            row.get("cr_st")

            or 0
        )

        amount = debit_amount if debit_amount else credit_amount
        amount = round(amount / 100, 2)

        period_from = row.get("date_from") or args.get("date_start")
        period_to = row.get("date_to") or row.get("date_from") or args.get("date_finish")

        days = None
        if period_from and period_to:
            days = (period_to - period_from).days + 1
        
        article = row.get("acc_st")
        

        rows.append({
            "period_from": period_from,
            "period_to": period_to,
            "days": days,
            "amount_net": amount,
            "vat_amount": 0,
            "amount_gross": amount,
            "amount": amount,
            "comment": f"Cash based • статья {article}",
        })

    total = sum((r.get("amount_gross") or 0) for r in rows)

    return {
        "rows": rows,
        "total": total,
        "total_net": total,
        "total_vat": 0,
        "total_gross": total,
        "vat_rate": None,
        "vat_mode": args.get("vat_mode"),
        "period": {
            "from": args.get("date_start"),
            "to": args.get("date_finish"),
        },
    }


def execute(conn, **args):
    """
     начисление: пишет в gl.accural_distribution.
    """
    param = args.get("params_json") or {}
    ignored = param.get("Игнорировать", False)

    if ignored:
        return

    sql = """
    INSERT INTO gl.accural_distribution(
        p_fn_id, pid, date_from, contract_id, condition_id,
        company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat,
        cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl, acc_bs,
        subconto_bs, dt_bs, cr_bs
    )
    SELECT
        p_fn_id, pid, date_from, contract_id, condition_id,
        company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat,
        cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl, acc_bs,
        subconto_bs, dt_bs, cr_bs
    FROM gl.cash_based_distribution(
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::jsonb,
        %s::text,
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::int,
        %s::date,
        %s::date
    );
    """

    params = build_sql_params(args)

    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


def main(conn, **args):
    return preview(conn, **args)
