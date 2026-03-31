import pandas as pd
import numpy as np
from pprint import pprint

def insert_results(conn, rows):
    with conn.cursor() as cur:
        with cur.copy(
            """
            COPY public.budget_gl (
                "date",
                dt,
                cr,
                description,
                chapter,
                acc_id,
                contract_id,
                subconto_id,
                version_id
            )
            FROM STDIN
            """
        ) as copy:
            for row in rows:
                copy.write_row(row)

    conn.commit()


def make_forecast(conn, date_from, date_to, d: dict, instance_id):
    dates = pd.date_range(date_from, date_to, freq="ME")
    rows = []

    def append_rows(acc_id, subconto_id, mean_name, value, subitem_name):
        def split_amount(amount):
            amt = int(round(float(amount) * 100, 0))
            dt = amt if amt > 0 else 0
            cr = -amt if amt < 0 else 0
            return dt, cr

        if mean_name == "Manual":
            # value может быть:
            # 1) dict: {"2026-01-31": 0.0, "2026-02-28": 10.0}
            # 2) list: [{"2026-01-31": 0.0}, {"2026-02-28": 10.0}]
            if isinstance(value, dict):
                for dt_raw, amount in value.items():
                    dt, cr = split_amount(amount)
                    rows.append(
                        (
                            str(pd.Timestamp(dt_raw).date()),
                            dt,
                            cr,
                            str(subitem_name),
                            "Прогноз расходов",
                            int(acc_id),
                            None,
                            int(subconto_id),
                            int(instance_id),
                        )
                    )

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for dt_raw, amount in item.items():
                            dt, cr = split_amount(amount)
                            rows.append(
                                (
                                    str(pd.Timestamp(dt_raw).date()),
                                    dt,
                                    cr,
                                    str(subitem_name),
                                    "Прогноз расходов",
                                    int(acc_id),
                                    None,
                                    int(subconto_id),
                                    int(instance_id),
                                )
                            )

        else:
            # value = одно число, размазываем по всем месяцам
            dt, cr = split_amount(value)

            rows.extend(
                (
                    str(date.date()),
                    dt,
                    cr,
                    str(subitem_name),
                    "Прогноз расходов",
                    int(acc_id),
                    None,
                    int(subconto_id),
                    int(instance_id),
                )
                for date in dates
            )

    for item_name, item_data in d["cf_params"].items():
        if not item_data.get("use"):
            continue

        for subitem_name, subitem_data in item_data.get("subitems", {}).items():
            if not subitem_data.get("use"):
                continue

            for mean_name, mean_data in subitem_data.get("means", {}).items():
                if not mean_data.get("use"):
                    continue

                value = mean_data.get("value")
                acc_id = subitem_data.get("acc_id")
                subconto_id = subitem_data.get("subconto_id")

                append_rows(acc_id, subconto_id, mean_name, value, subitem_name)

    insert_results(conn, rows)
    return rows


def main(conn,**args):
    
    
    DATE_FROM = args['date_from']
    DATE_TO = args['date_to']
    instance = args['id']    
    
    
    make_forecast(conn, DATE_FROM, DATE_TO, args, instance)

    conn.close()

