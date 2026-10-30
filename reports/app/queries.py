from conns import get_duckdb_conn_with_opt
from datetime import date

class BaseQueries:
    def __init__(self,report_type=None,date_from=None,date_to=None):
        
        self.report_type = 'AD' if not report_type else report_type
        self.date_from = date_from if date_from else date(2023,1,1)
        self.date_to = date_to if date_to else date.today()
        
    # Возвращает данные по всем УПД
    def upd_documents(self):        
        with get_duckdb_conn_with_opt(with_pg=True) as con:
            rel = con.execute(
                """ 
                select 
                t.id,
                p.brand,
                t.nm_id as usk,
                u.date,
                u.number,
                u.contract_id,
                t.upd_document_id,
                cp.name,
                CONCAT('№', COALESCE(c.number,'б/н'), ' от ', COALESCE(c.date::text,'б/д') ) as contract_name,
                t.upd_qty,
                t.upd_price_vatless,
                t.upd_amount_vatless
                from pg.public.upd_income_lines t 
                left join pg.public.wb_products p on p.nm_id = t.nm_id
                left join pg.public.cards_upddocument u on u.id = t.upd_document_id
                left join pg.public.contracts_contracts c on c.id = u.contract_id
                left join pg.public.counterparties_counterparty cp on cp.id = u.counterparty_id                
                """
            ).df()
        return rel
        
        