import dash_mantine_components as dmc
import pandas as pd
import numbers
from typing import Literal, Optional


TableClass = Literal[
    "classic-table",
    "fancy-table",
    "booktabs-table",
    "compact-table",
]

def format_value(col, ind, v, FORMATERS):
    if v is None or pd.isna(v):
        return "—"

    # 2) форматер по колонке
    if col in FORMATERS:
        try:
            return FORMATERS[col](float(v))
        except Exception:
            return v

    # 1) форматер по строке (индексу)
    if ind in FORMATERS:
        try:
            return FORMATERS[ind](float(v))
        except Exception:
            return v

    # 3) дефолт для чисел
    if isinstance(v, (int, float)):
        return f"{float(v):,.2f}"

    return v


def cell_class(v):
    classes = []

    if isinstance(v, numbers.Number) and not pd.isna(v):
        classes.append("num")
        if float(v) < 0:
            classes.append("neg")

    return " ".join(classes)


def df_dmc_table(df: pd.DataFrame, 
                 formaters: dict={},
                 className: TableClass = "classic-table",
                 withTableBorder = False,
                 withColumnBorders = False,
                 striped=False,
                 highlightOnHover = True,
                 
                 ):

    head = []
    c = [df.index.name or ""] + list(df.columns)

    for i in c:
        head.append(dmc.TableTh(i))
            
        
    body = []

    for ind in df.index:
        row = []

        # индекс (первая колонка)
        row.append(dmc.TableTd(ind))

        for col in df.columns:
            v = df.loc[ind, col]  # <-- ФИКС
            cl = cell_class(v)
            v = format_value(col, ind, v, formaters)  # <-- ФИКС
            row.append(dmc.TableTd(v, className=cl))

        body.append(dmc.TableTr(row))

    return dmc.Table(
        withTableBorder=withTableBorder,
        withColumnBorders=withColumnBorders,
        striped=striped,
	    highlightOnHover=highlightOnHover,
        className=className,
        children=[
            dmc.TableThead(dmc.TableTr(head)),
            dmc.TableTbody(body)
            ],  
    )
