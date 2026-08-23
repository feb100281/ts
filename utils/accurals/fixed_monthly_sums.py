import pandas as pd
import numpy as np

def get_vat(amount, vat_mode, vat_rate):
    if vat_mode == "included":
        return amount * vat_rate / (100 + vat_rate)
    if vat_mode == "excluded":
        return amount * vat_rate / 100
    if vat_mode == "exempt":
        return 0
    else:
        return 0


# делаем начисления в месяц в зависимости от дней
def fixed_monthly_sums(conn, **args):

    params: dict = args["params_json"]
    if not params:
        return "No JSON PARAMS"

    fixed_amount = params.get("Сумма по договору")
    day_accural = params.get("День начислений")
    date_start = args.get("date_start")
    date_finish = args.get("date_finish")
    vat_mode = args["vat_mode"]
    vat_json = args["vat_json"]

    # if not fixed_amount or not date_start or not date_finish:
    #    return

    start_interval = pd.to_datetime(date_start).date()
    end_interval = pd.to_datetime(date_finish).date()

    start_interval = pd.to_datetime(date_start).normalize()
    end_interval = pd.to_datetime(date_finish).normalize()

    month_starts = pd.date_range(
        start=start_interval.to_period("M").to_timestamp(),
        end=end_interval.to_period("M").to_timestamp(),
        freq="MS",
    )

    ms = month_starts.to_numpy()
    me = (month_starts + pd.offsets.MonthEnd(0)).to_numpy()

    ms[0] = np.datetime64(start_interval)
    me[-1] = np.datetime64(end_interval)

    days_in_month = month_starts.days_in_month.to_numpy()
    days = (me - ms).astype("timedelta64[D]").astype(int) + 1

    # Считаем размер массива
    n = len(me)

    # Добавляем фиксированные платежи
    fix_monthly_payment = np.full(n, fixed_amount)

    # Добавляем vat_mode
    vat_mode = np.full(n, vat_mode)

    # делаем массив НДС
    vat_items = sorted(
        (pd.Timestamp(k).to_datetime64(), v) for k, v in vat_json.items()
    )

    vat_dates = np.array([x[0] for x in vat_items])
    vat_rates = np.array([x[1] for x in vat_items])

    idx = np.searchsorted(vat_dates, ms, side="right") - 1
    vat_rates = vat_rates[idx]

    # Cчитаем НДС

    vat_func = np.vectorize(get_vat)
    vat = vat_func(fix_monthly_payment, vat_mode, vat_rates)
    vat = vat * 100
    
    # Ставим None если НДС 0
    acc_vat = np.full(n,None)
    acc_vat = np.where(vat != 0,86,acc_vat)

    # Теперь проверяем нет ли у нас НДС сверху если есть добавляем к ставке
    fix_monthly_payment_with_vat = np.where(
        vat_mode == "excluded", fix_monthly_payment + vat, fix_monthly_payment
    )

    # Начисления
    cr_st = fix_monthly_payment_with_vat / days_in_month * days * 100
    dt_st = fix_monthly_payment_with_vat * 0

    dt_vat = vat
    cr_vat = vat * 0

    dt_pl = cr_st - dt_vat
    cr_pl = dt_st - cr_vat

    dt_bs = cr_st - dt_vat
    cr_bs = dt_st - cr_vat
    
    ms = pd.to_datetime(ms)
    me = pd.to_datetime(me)
    
    desciption_st = np.array(
    [
        f"Начисления за период с {pd.to_datetime(s):%d.%m.%Y} по {pd.to_datetime(e):%d.%m.%Y}. "
        f"Ставка {fixed_amount:,.2f} / {dim} * {d} = {cr/100:,.2f}"
        for s, e, dim, d, cr in zip(ms, me, days_in_month, days, cr_st)
    ],
    dtype=object
    )
    
    with conn.cursor() as cur:
        with cur.copy("""
            COPY gl.accural_distribution (
                p_fn_id, pid, date_from, contract_id, condition_id, company_id,
                acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat, cr_vat,
                acc_pl, subconto_pl, dt_pl, cr_pl,
                acc_bs, subconto_bs, dt_bs, cr_bs,
                description_st
            )
            FROM STDIN
        """) as copy:
            for i in range(n):
                copy.write_row([
                    int(args["fn_id"]),
                    None,
                    pd.to_datetime(me[i]).date(),
                    int(args["contract_id"]),
                    int(args["condition_id"]),
                    1,
                    args["acc_st_id"],
                    int(round(dt_st[i])),
                    int(round(cr_st[i])),
                    int(vat_rates[i]) if pd.notna(vat_rates[i]) else None,
                    acc_vat[i],
                    int(round(dt_vat[i])),
                    int(round(cr_vat[i])),
                    args["acc_pl_id"],
                    args["subconto_pl_id"],
                    int(round(dt_pl[i])),
                    int(round(cr_pl[i])),
                    args["acc_bs_id"],
                    args["subconto_bs_id"],
                    int(round(dt_bs[i])),
                    int(round(cr_bs[i])),
                    desciption_st[i],
                ])

    conn.commit()
    return 'good'
    
    # INSERT INTO gl.accural_distribution(
	# p_fn_id, pid, date_from, contract_id, condition_id, 
    # company_id, acc_st, dt_st, cr_st, vat_rate, acc_vat, dt_vat, 
    # cr_vat, acc_pl, subconto_pl, dt_pl, cr_pl, acc_bs, 
    # subconto_bs, dt_bs, cr_bs)
    
    # args["contract_id"],
    # args["acc_st_id"],
    # 84,
    # args["acc_pl_id"],
    # args["acc_bs_id"],
    # Jsonb(args["vat_json"] or {}),   # dict
    # args["vat_mode"],    
    # args["subconto_bs_id"],
    # args["subconto_pl_id"],
    # 1,   
    # args["condition_id"],    
    # args["fn_id"],
    # args["date_start"],    
    # args["date_finish"]  
    
    # # Финализируем расчеты в df что бы записать в accurals destribution
    # rows = list(zip(
    # np.full(n,args['fn_id']),
    # np.full(n,None),
    # me,
    # np.full(n,args['contract_id']),
    # np.full(n,args['condition_id']),
    # np.full(n,1),
    # np.full(n,args['acc_st_id']),
    # dt_st.round(0),
    # cr_st.round(0),
    # vat_rates,
    # acc_vat,
    # dt_vat.round(0),
    # cr_vat.round(0),
    # np.full(n,args['acc_pl_id']),
    # np.full(n,args['subconto_pl_id']),
    # dt_pl.round(0),
    # cr_pl.round(0),
    # np.full(n,args['acc_bs_id']),
    # np.full(n,args['subconto_bs_id']),
    # dt_bs.round(0),
    # cr_bs.round(0),
    # desciption_st
    # ))

    


def main(conn, **args):
    print(fixed_monthly_sums(conn, **args))


if __name__ == "__main__":
    main()
