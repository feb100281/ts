# budget/reporting/pdf/utils/math_utils.py

import math


def safe_pct_change(current, previous):
    if previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def calc_pct_changes(values: list[float]) -> list[float | None]:
    result = [None]
    for i in range(1, len(values)):
        prev = values[i - 1]
        cur = values[i]
        if prev is None or abs(prev) < 0.0001:
            result.append(None)
        else:
            result.append((cur / prev - 1) * 100)
    return result


def safe_corr(x_values: list[float], y_values: list[float]) -> float | None:
    pairs = [
        (float(x), float(y))
        for x, y in zip(x_values, y_values)
        if x is not None and y is not None
    ]

    if len(pairs) < 2:
        return None

    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]

    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)

    num = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))

    if den_x == 0 or den_y == 0:
        return None

    return num / (den_x * den_y)