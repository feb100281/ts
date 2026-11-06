# utils/forecast/transforms.py
import numpy as np
import pandas as pd


def prepare_daily_sheet(data, forecast, last_actual_date):
    last_actual_date = pd.to_datetime(last_actual_date)

    daily = forecast[["ds", "trend", "yhat", "yhat_lower", "yhat_upper"]].copy()
    daily = daily.merge(data[["ds", "y"]], on="ds", how="left")

    # Сразу приводим к float, чтобы дальше не было object/NAType проблем
    for col in ["yhat", "yhat_lower", "yhat_upper", "trend", "y"]:
        if col in daily.columns:
            daily[col] = pd.to_numeric(daily[col], errors="coerce").astype(float)

    daily["Тип"] = np.where(daily["ds"] <= last_actual_date, "Факт", "Прогноз")

    daily["Факт"] = daily["y"].astype(float)
    daily["Прогноз"] = np.where(
        daily["ds"] > last_actual_date,
        daily["yhat"],
        np.nan
    ).astype(float)

    daily["Итог"] = np.where(
        daily["ds"] <= last_actual_date,
        daily["Факт"],
        daily["Прогноз"]
    ).astype(float)

    daily["Отклонение факт-прогноз"] = np.where(
        daily["ds"] <= last_actual_date,
        daily["Факт"] - daily["yhat"],
        np.nan
    ).astype(float)

    daily["Отклонение %"] = np.where(
        (daily["ds"] <= last_actual_date) & (daily["yhat"] != 0),
        (daily["Факт"] - daily["yhat"]) / daily["yhat"],
        np.nan
    ).astype(float)

    daily["Дата"] = pd.to_datetime(daily["ds"]).dt.date
    daily["Месяц_dt"] = pd.to_datetime(daily["ds"]).dt.to_period("M").dt.to_timestamp()

    daily = daily.rename(columns={
        "yhat_lower": "Нижняя граница прогноза",
        "yhat_upper": "Верхняя граница прогноза",
        "trend": "Тренд",
    })

    numeric_cols = [
        "Факт",
        "Прогноз",
        "Нижняя граница прогноза",
        "Верхняя граница прогноза",
        "Тренд",
        "Итог",
        "Отклонение факт-прогноз",
        "Отклонение %",
    ]
    for col in numeric_cols:
        daily[col] = pd.to_numeric(daily[col], errors="coerce").astype(float)

    return daily[
        [
            "Дата",
            "Месяц_dt",
            "Тип",
            "Факт",
            "Прогноз",
            "Нижняя граница прогноза",
            "Верхняя граница прогноза",
            "Тренд",
            "Итог",
            "Отклонение факт-прогноз",
            "Отклонение %",
        ]
    ]


def prepare_monthly_sheet(daily_sheet, last_actual_date):
    last_actual_date = pd.to_datetime(last_actual_date)
    current_month_start = last_actual_date.replace(day=1)

    df = daily_sheet.copy()
    df["Дата"] = pd.to_datetime(df["Дата"])
    df["Год"] = df["Дата"].dt.year
    df["Месяц_номер"] = df["Дата"].dt.month

    numeric_cols = [
        "Факт",
        "Прогноз",
        "Итог",
        "Нижняя граница прогноза",
        "Верхняя граница прогноза",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    monthly = (
        df.groupby(["Месяц_dt", "Год", "Месяц_номер"], as_index=False)
        .agg({
            "Факт": "sum",
            "Прогноз": "sum",
            "Итог": "sum",
            "Нижняя граница прогноза": "sum",
            "Верхняя граница прогноза": "sum",
        })
        .sort_values("Месяц_dt")
        .reset_index(drop=True)
    )

    monthly["Месяц"] = monthly["Месяц_dt"].dt.strftime("%Y-%m")

    def get_month_status(x):
        if x < current_month_start:
            return "Факт"
        if x == current_month_start:
            return "Текущий месяц"
        return "Прогноз"

    monthly["Статус месяца"] = monthly["Месяц_dt"].apply(get_month_status)

    # В закрытых месяцах не показываем прогноз
    monthly.loc[monthly["Статус месяца"] == "Факт", "Прогноз"] = 0.0

    for col in ["Факт", "Прогноз", "Итог", "Нижняя граница прогноза", "Верхняя граница прогноза"]:
        monthly[col] = pd.to_numeric(monthly[col], errors="coerce").astype(float)

    monthly["Изменение к пред. месяцу, ₽"] = monthly["Итог"].diff().astype(float)
    monthly["Изменение к пред. месяцу, %"] = monthly["Итог"].pct_change(fill_method=None).astype(float)

    monthly["Изменение к тому же месяцу прошлого года, ₽"] = (
        monthly["Итог"] - monthly["Итог"].shift(12)
    ).astype(float)
    monthly["Изменение к тому же месяцу прошлого года, %"] = (
        monthly["Итог"] / monthly["Итог"].shift(12) - 1
    ).astype(float)

    monthly["Доля факта в месяце, %"] = (
        monthly["Факт"] / monthly["Итог"].replace(0, np.nan)
    ).astype(float)
    monthly["Доля прогноза в месяце, %"] = (
        monthly["Прогноз"] / monthly["Итог"].replace(0, np.nan)
    ).astype(float)

    return monthly[
        [
            "Месяц",
            "Месяц_dt",
            "Год",
            "Месяц_номер",
            "Статус месяца",
            "Факт",
            "Прогноз",
            "Итог",
            "Нижняя граница прогноза",
            "Верхняя граница прогноза",
            "Доля факта в месяце, %",
            "Доля прогноза в месяце, %",
            "Изменение к пред. месяцу, ₽",
            "Изменение к пред. месяцу, %",
            "Изменение к тому же месяцу прошлого года, ₽",
            "Изменение к тому же месяцу прошлого года, %",
        ]
    ]


def prepare_yearly_sheet(monthly_sheet, current_year, last_actual_date):
    df = monthly_sheet.copy()

    for col in ["Факт", "Прогноз", "Итог"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    yearly = (
        df.groupby("Год", as_index=False)
        .agg({
            "Факт": "sum",
            "Прогноз": "sum",
            "Итог": "sum",
        })
        .sort_values("Год")
        .reset_index(drop=True)
    )

    yearly.loc[yearly["Год"] < current_year, "Прогноз"] = np.nan
    yearly.loc[yearly["Год"] < current_year, "Итог"] = yearly.loc[yearly["Год"] < current_year, "Факт"]

    for col in ["Факт", "Прогноз", "Итог"]:
        yearly[col] = pd.to_numeric(yearly[col], errors="coerce").astype(float)

    yearly["Статус года"] = yearly["Год"].apply(
        lambda y: (
            "Факт"
            if y < current_year
            else "Текущий год: факт + прогноз"
            if y == current_year
            else "Прогноз"
        )
    )

    yearly["Изменение к пред. году, ₽"] = yearly["Итог"].diff().astype(float)
    yearly["Изменение к пред. году, %"] = yearly["Итог"].pct_change(fill_method=None).astype(float)

    yearly["Комментарий"] = yearly["Год"].apply(
        lambda y: (
            "Закрытый год, отражен только факт"
            if y < current_year
            else f"По состоянию на {pd.to_datetime(last_actual_date).date()} отражены факт YTD и прогноз на остаток года"
            if y == current_year
            else "Будущий период"
        )
    )

    return yearly[
        [
            "Год",
            "Факт",
            "Прогноз",
            "Итог",
            "Статус года",
            "Изменение к пред. году, ₽",
            "Изменение к пред. году, %",
            "Комментарий",
        ]
    ]


def prepare_quarterly_sheet(monthly_sheet):
    df = monthly_sheet.copy()
    df["Квартал"] = df["Месяц_dt"].dt.to_period("Q").astype(str)

    for col in ["Факт", "Прогноз", "Итог"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    quarterly = (
        df.groupby(["Год", "Квартал"], as_index=False)
        .agg({
            "Факт": "sum",
            "Прогноз": "sum",
            "Итог": "sum",
        })
        .sort_values(["Год", "Квартал"])
        .reset_index(drop=True)
    )

    quarterly["Изменение к пред. кварталу, ₽"] = quarterly["Итог"].diff().astype(float)
    quarterly["Изменение к пред. кварталу, %"] = quarterly["Итог"].pct_change(fill_method=None).astype(float)

    return quarterly