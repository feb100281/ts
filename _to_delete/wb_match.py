PAYOUT_MATCH_DAYS = 15      # окно поиска поступления после вывода
PAYOUT_MATCH_EPS = 1.0      # допуск по сумме, рублей


def match_wb_payouts(outs, ins):
    """Сопоставляет вывод с баланса WB и поступление на расчётный счёт.

    Проход первый — по совпадению суммы: поступление ищется в окне
    PAYOUT_MATCH_DAYS дней после вывода, берётся самое раннее подходящее.
    Проход второй — остаток по порядку: деньги приходят в той же
    последовательности, в которой выводились.

    Нужно только для того, чтобы у каждой суммы вывода была дата, которой
    деньги реально пришли на расчётный счёт. Пара без поступления
    (kind = transit) на лист не попадает: это деньги в пути.
    """
    used = [False] * len(ins)
    pairs = []

    def take(i, out, kind):
        used[i] = True
        inc = ins[i]
        pairs.append({
            "out_dt": out["dt"], "out_amount": out["amount"],
            "in_dt": inc["dt"], "in_amount": inc["amount"],
            "cp_name": inc["cp_name"],
            "days": (inc["dt"] - out["dt"]).days,
            "kind": kind,
        })

    rest = []
    for out in outs:
        hit = None
        for i, inc in enumerate(ins):
            if inc["dt"] < out["dt"]:
                continue
            if (inc["dt"] - out["dt"]).days > PAYOUT_MATCH_DAYS:
                break
            if used[i]:
                continue
            if abs(inc["amount"] - out["amount"]) <= PAYOUT_MATCH_EPS:
                hit = i
                break
        if hit is None:
            rest.append(out)
        else:
            take(hit, out, "exact")

    for out in rest:
        hit = None
        for i, inc in enumerate(ins):
            if not used[i] and inc["dt"] >= out["dt"]:
                hit = i
                break
        if hit is None:
            pairs.append({
                "out_dt": out["dt"], "out_amount": out["amount"],
                "in_dt": None, "in_amount": 0.0, "cp_name": "",
                "days": None, "kind": "transit",
            })
        else:
            take(hit, out, "order")

    pairs.sort(key=lambda p: (p["out_dt"], p["in_dt"] or date.max))
    return pairs
