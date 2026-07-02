import duckdb
from conns import get_duckdb_conn_with_opt
from .queries import BASE_QUERY, DAILY_SALES_AGG
from datetime import date


class DashboardData:

    def __enter__(self):
        self.con = get_duckdb_conn_with_opt()    
        self._init_base()
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self.con.close()
    
    def _init_base(self):
        self.con.execute(BASE_QUERY)
    
    def make_filter(self, cat_id=None, gender=None, brand=None):
        cat_filter = ''
        gender_filter = ''
        brand_filter = ''

        if cat_id:
            if isinstance(cat_id, list):
                cat_filter = f"AND subject_id IN ({','.join(str(int(x)) for x in cat_id)})"
            else:
                cat_filter = f"AND subject_id = {int(cat_id)}"

        if gender:
            if isinstance(gender, list):
                gender_filter = f"AND gender IN ({','.join(f'\'{x}\'' for x in gender)})"
            else:
                gender_filter = f"AND gender = '{gender}'"

        if brand:
            if isinstance(brand, list):
                brand_filter = f"AND brand IN ({','.join(f'\'{x}\'' for x in brand)})"
            else:
                brand_filter = f"AND brand = '{brand}'"

        return f"{cat_filter} {gender_filter} {brand_filter}"
        
    def get_dayly_sales_grid_data(
        self,
        start = date(2024,1,1),
        end = date.today(),
        cats_list = [],
        brand_list = None,
        gender_list = None        
        ):
        sql = DAILY_SALES_AGG.format(filters = self.make_filter(cats_list,gender_list,brand_list))
        
        return self.con.execute(sql,parameters=[start,end]).df()


        
   

        
