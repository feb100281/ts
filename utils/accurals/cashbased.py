
#--------------------------
# Начисления CashBased
#--------------------------
import pandas as pd
import numpy as np
from psycopg.types.json import Jsonb

# распределяет по GL за 1 проход сf по счетам.
def cash_based_distibution(conn,**args):
    
    param = args['params_json']        
    ignored = param.get('Игнорировать', False)
    where = param.get('Фильтр', "")
    
    if ignored:
        return
   
    
    SQL = """
    INSERT INTO gl.accural_distribution(
	p_fn_id, pid, date_from, contract_id, condition_id, 
    company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat, 
    cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl, acc_bs, 
    subconto_bs, dt_bs, cr_bs)
    SELECT 
    p_fn_id, pid, date_from, contract_id, condition_id, 
    company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat, 
    cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl, acc_bs, 
    subconto_bs, dt_bs, cr_bs    
    FROM gl.cash_based_distribution(
        %s,
        %s,
        %s,
        %s,
        %s,
        %s::jsonb,        
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,        
        %s,
        %s
    );
    
    """    
    
    params = (
    args["contract_id"],
    args["acc_st_id"],
    84,
    args["acc_pl_id"],
    args["acc_bs_id"],
    Jsonb(args["vat_json"] or {}),   # dict
    args["vat_mode"],    
    args["subconto_bs_id"],
    args["subconto_pl_id"],
    1,   
    args["condition_id"],    
    args["fn_id"],
    args["date_start"],    
    args["date_finish"]  
    )
    
    with conn.cursor() as cur:
        cur.execute(SQL,params)
    conn.commit()
    
    return 'pd.read_sql(SQL,params=params,con=conn)'


def main(conn, **args):    
    print(cash_based_distibution(conn, **args))
    

if __name__ == "__main__":
    main()
