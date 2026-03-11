
#--------------------------
# Начисления CashBased
#--------------------------
import pandas as pd
import numpy as np

# распределяет по GL за 1 проход сf по счетам.
def cash_based_distibution(conn,**args):
    
    param = args['params_json']
    
    contract_id = args['contract_id']
    SQL = """
    SELECT 
    
    """
    
    
    return param['Игнорировать']


def main(conn, **args):    
    print(cash_based_distibution(conn, **args))
    

if __name__ == "__main__":
    main()
