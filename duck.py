import duckdb
import pandas as pd

file = '/Users/daria/Desktop/ТРЕНДСЕТТЕР/Бух данные/ОСВ/сч 45/2026-01 ОСВ_45.xlsx'

# без создания файла базы: соединение только в памяти
con = duckdb.connect()

con.execute("INSTALL excel;")
con.execute("LOAD excel;")

rel = con.sql("""
    WITH src AS (
        SELECT
            *,
            row_number() OVER () AS rn
        FROM read_xlsx(
            ?,
            sheet = 'Лист_1',
            range = 'A13:G91254', -- меняй или находи автоматом
            header = false -- лучще не ставить
        )
    )
    SELECT
        LAST_VALUE(A IGNORE NULLS) OVER (ORDER BY rn) AS name, -- здесь тупа заполняем null предыдущими значениями
        B,
        C as bb_dt,
        D as bb_cr, 
        E as turover_dt,
        F as turover_cr,
        G as eb_dt 
       
    FROM src
""", params=[file])

rel.show() # Смотрим что получилось и время тупа засекай :))


# Тепреть магия покажем только количичество

quant = con.sql(
    "select * from rel where B='Кол.'"
)
quant.show() #Тоже что и принт но короче



# Тупа пишем в panda :))))
df = quant.df() 

### ЭТО 0.0000001 % что можно делать с этой штукой. главное понять что все rel quant и все остальное внутри 1 con объеденябтся и через обычный sql можно все делать.

