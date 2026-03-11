import pandas as pd
import numpy as np

# распределяет по GL за 1 проход сf по счетам.
def fixed_monthly_sums(conn,**args):
    contract_id = args['fn_id']
    return contract_id


def main(conn, **args):    
    print(fixed_monthly_sums(conn, **args))
    

if __name__ == "__main__":
    main()