from conns import get_duckdb_conn

def get_ag_grid_data(option):
    if option == 'dates':
        with get_duckdb_conn() as con:
            df = con.execute(
                """ 
                select
                x.sales_date,
                round(x.amount/100.00,2) as amount,
                round(x.vat_amount/100.00,2) as vat_amount,
                round(x.amount_vatless/100,2) as amount_vatless,
                round(x.dt/100,2) as dt,
                x.total_net_sales,
                x.no_cost
                from(
                select  
                sales_date::date as sales_date,
                sum(cr_rev) as amount,
                sum(cr_rev) -
                sum(cr_rev / (100+vat_rate) * 100) as vat_amount,
                sum(cr_rev / (100+vat_rate) * 100) as amount_vatless,
                sum(cr) as dt,
                count(cr_rev) as total_net_sales,
                sum(case when cr = 0 then 1 else 0 end) as no_cost
                from inventories.gl_main
                group by sales_date) x
                order by x.sales_date desc
                """                
            ).df()
            df["sales_date"] = (

            df["sales_date"]

            .dt.date

            )
    else:
        return
    
    return df.to_dict(orient='records')