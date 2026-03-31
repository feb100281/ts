from conns import connect_db
from psycopg.rows import dict_row
from psycopg import Connection
from pprint import pprint
from budget.fns import sales_forecast, cf_forecast

def get_budget_params(conn:Connection,instance_id:int):
    sql = """
    SELECT * from public.budget_budgetversion
    where id = %s    
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (instance_id,))
        return cur.fetchone()    


def main(instance_id):
    conn = connect_db()    
    args = get_budget_params(conn,instance_id)
    sales_forecast.main(conn,**args)
    cf_forecast.main(conn,**args)
    
    
    conn.close()
if __name__ == "__main__":
    main()

