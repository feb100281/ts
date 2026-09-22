from pathlib import Path
from conns import get_duckdb_conn_with_opt

folder_path = '/Users/pavelustenko/Downloads/УПД с правками'

# Получить все .xlsx файлы
files = list(Path(folder_path).glob('*.xlsx'))

def update_upd_income(file):
    query = f""" 
    WITH a AS (
    select 
    ID::bigint as id,
    round(Себестоимость::double,2)::double as man_cost_per_unit
    from read_xlsx(
        '{file}',
        header = True,
        all_varchar = true,
        range = 'A9:N'
        )
    where ID is not null 
    and ID != 'ИТОГО:'
    )
    UPDATE pg.public.upd_income_lines AS t
    SET man_cost_per_unit = a.man_cost_per_unit::NUMERIC  -- приводим к числу
    FROM a
    WHERE t.id = a.id::BIGINT;  -- приводим id к числовому типу
    """
    with get_duckdb_conn_with_opt() as con:
        con.execute(
            query
            
        )
    
    return f"{file} - done"
    
for file in files:
    print(file)
    print(update_upd_income(file))