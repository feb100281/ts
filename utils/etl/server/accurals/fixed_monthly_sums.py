# accurals/fixed_monthly_sums.py

import pandas as pd
import numpy as np


def get_vat(amount, vat_mode, vat_rate):
    if vat_mode == "included":
        return amount * vat_rate / (100 + vat_rate)

    if vat_mode == "excluded":
        return amount * vat_rate / 100

    if vat_mode == "exempt":
        return 0

    return 0


# Делаем начисления в месяц в зависимости от дней
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

    start_interval = pd.to_datetime(
        date_start
    ).normalize()

    end_interval = pd.to_datetime(
        date_finish
    ).normalize()

    month_starts = pd.date_range(
        start=start_interval.to_period("M").to_timestamp(),
        end=end_interval.to_period("M").to_timestamp(),
        freq="MS",
    )

    ms = month_starts.to_numpy(copy=True)

    me = (
        month_starts + pd.offsets.MonthEnd(0)
    ).to_numpy(copy=True)

    # Первый и последний месяцы могут быть неполными
    ms[0] = np.datetime64(start_interval)
    me[-1] = np.datetime64(end_interval)

    # Количество дней в каждом полном месяце
    days_in_month = (
        month_starts.days_in_month.to_numpy()
    )

    # Фактическое количество дней начисления
    days = (
        (me - ms)
        .astype("timedelta64[D]")
        .astype(int)
        + 1
    )

    # Количество месяцев
    n = len(me)

    # Фиксированная месячная сумма
    fix_monthly_payment = np.full(
        n,
        fixed_amount,
    )

    # Режим НДС
    vat_mode = np.full(
        n,
        vat_mode,
    )

    # Формируем массив ставок НДС
    vat_items = sorted(
        (
            pd.Timestamp(k).to_datetime64(),
            v,
        )
        for k, v in vat_json.items()
    )

    vat_dates = np.array(
        [x[0] for x in vat_items]
    )

    vat_rates = np.array(
        [x[1] for x in vat_items]
    )

    # Для каждого месяца выбираем ставку НДС,
    # действующую на начало расчётного периода
    idx = (
        np.searchsorted(
            vat_dates,
            ms,
            side="right",
        )
        - 1
    )

    vat_rates = vat_rates[idx]

    # ---------------------------------------------------------
    # РАСЧЁТ НДС
    # ---------------------------------------------------------

    vat_func = np.vectorize(get_vat)

    # НДС за полный месяц в рублях.
    # Ставка берётся из vat_rates:
    # это может быть 20%, 22% или любая другая указанная ставка.
    vat_monthly = vat_func(
        fix_monthly_payment,
        vat_mode,
        vat_rates,
    )

    # Если НДС начисляется сверху, добавляем месячный НДС
    # к месячной сумме.
    #
    # Здесь всё ещё рубли, поэтому единицы измерения совпадают.
    fix_monthly_payment_with_vat = np.where(
        vat_mode == "excluded",
        fix_monthly_payment + vat_monthly,
        fix_monthly_payment,
    )

    # Полное начисление с НДС за фактические дни.
    # В конце переводим рубли в копейки.
    cr_st = (
        fix_monthly_payment_with_vat
        / days_in_month
        * days
        * 100
    )

    dt_st = fix_monthly_payment_with_vat * 0

    # НДС также считаем только за фактические дни.
    # В конце переводим рубли в копейки.
    vat = (
        vat_monthly
        / days_in_month
        * days
        * 100
    )

    # Счёт НДС ставим только при наличии НДС
    acc_vat = np.full(
        n,
        None,
    )

    acc_vat = np.where(
        vat != 0,
        84,
        acc_vat,
    )

    dt_vat = vat
    cr_vat = vat * 0

    # В P&L попадает сумма без НДС
    dt_pl = cr_st - dt_vat
    cr_pl = dt_st - cr_vat

    # Сохраняем прежнюю логику балансового счёта
    dt_bs = cr_st - dt_vat
    cr_bs = dt_st - cr_vat

    ms = pd.to_datetime(ms)
    me = pd.to_datetime(me)

    desciption_st = np.array(
        [
            (
                f"Начисления за период с "
                f"{pd.to_datetime(s):%d.%m.%Y} "
                f"по {pd.to_datetime(e):%d.%m.%Y}. "
                f"Ставка {fixed_amount:,.2f} / "
                f"{dim} * {d} = {cr / 100:,.2f}"
            )
            for s, e, dim, d, cr in zip(
                ms,
                me,
                days_in_month,
                days,
                cr_st,
            )
        ],
        dtype=object,
    )

    # Округляем до целых копеек
    dt_st = np.floor(
        dt_st + 0.5
    ).astype(np.int64)

    cr_st = np.floor(
        cr_st + 0.5
    ).astype(np.int64)

    dt_vat = np.floor(
        dt_vat + 0.5
    ).astype(np.int64)

    cr_vat = np.floor(
        cr_vat + 0.5
    ).astype(np.int64)

    dt_pl = np.floor(
        dt_pl + 0.5
    ).astype(np.int64)

    cr_pl = np.floor(
        cr_pl + 0.5
    ).astype(np.int64)

    dt_bs = np.floor(
        dt_bs + 0.5
    ).astype(np.int64)

    cr_bs = np.floor(
        cr_bs + 0.5
    ).astype(np.int64)

    with conn.cursor() as cur:
        with cur.copy(
            """
            COPY gl.accural_distribution (
                p_fn_id,
                pid,
                date_from,
                contract_id,
                condition_id,
                company_id,
                acc_st,
                dt_st,
                cr_st,
                vat_rate,
                acc_vat,
                dt_vat,
                cr_vat,
                acc_pl,
                subconto_pl,
                dt_pl,
                cr_pl,
                acc_bs,
                subconto_bs,
                dt_bs,
                cr_bs,
                description_st
            )
            FROM STDIN
            """
        ) as copy:

            for i in range(n):
                copy.write_row(
                    [
                        int(args["fn_id"]),
                        None,
                        pd.to_datetime(me[i]).date(),
                        int(args["contract_id"]),
                        int(args["condition_id"]),
                        int(args.get("company_id") or 1),
                        args["acc_st_id"],
                        int(round(dt_st[i])),
                        int(round(cr_st[i])),
                        (
                            int(vat_rates[i])
                            if pd.notna(vat_rates[i])
                            else None
                        ),
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
                    ]
                )

    conn.commit()

    return "good"


def main(conn, **args):
    print(
        fixed_monthly_sums(
            conn,
            **args,
        )
    )


if __name__ == "__main__":
    main()