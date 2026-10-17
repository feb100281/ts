# utils/forecast/analysis.py
import pandas as pd


def fmt_money(x):
    if pd.isna(x):
        return "—"
    return f"{x:,.0f}".replace(",", " ")


def fmt_pct(x):
    if pd.isna(x):
        return "—"
    return f"{x:.1%}".replace(".", ",")


def get_key_metrics(monthly_sheet, yearly_sheet, last_actual_date):
    last_actual_date = pd.to_datetime(last_actual_date)
    current_year = last_actual_date.year
    current_month = last_actual_date.strftime("%Y-%m")

    result = {}

    hist = yearly_sheet[yearly_sheet["Год"] < current_year].sort_values("Год")
    if not hist.empty:
        last_hist = hist.iloc[-1]
        result["last_year"] = {
            "year": int(last_hist["Год"]),
            "revenue": last_hist["Итог"],
            "delta_abs": last_hist["Изменение к пред. году, ₽"],
            "delta_pct": last_hist["Изменение к пред. году, %"],
        }

    cur = yearly_sheet[yearly_sheet["Год"] == current_year]
    if not cur.empty:
        cur = cur.iloc[0]
        forecast_share = cur["Прогноз"] / cur["Итог"] if cur["Итог"] else None
        result["current_year"] = {
            "year": int(cur["Год"]),
            "fact_ytd": cur["Факт"],
            "forecast_rest": cur["Прогноз"],
            "expected_total": cur["Итог"],
            "delta_abs": cur["Изменение к пред. году, ₽"],
            "delta_pct": cur["Изменение к пред. году, %"],
            "forecast_share": forecast_share,
        }

    ltm = monthly_sheet.sort_values("Месяц_dt").tail(12).copy()
    if not ltm.empty:
        best_row = ltm.loc[ltm["Итог"].idxmax()]
        worst_row = ltm.loc[ltm["Итог"].idxmin()]
        result["ltm"] = {
            "sum": ltm["Итог"].sum(),
            "avg": ltm["Итог"].mean(),
            "best_month": best_row["Месяц"],
            "best_value": best_row["Итог"],
            "worst_month": worst_row["Месяц"],
            "worst_value": worst_row["Итог"],
        }

    cur_month = monthly_sheet[monthly_sheet["Месяц"] == current_month]
    if not cur_month.empty:
        cur_month = cur_month.iloc[0]
        result["current_month"] = {
            "month": cur_month["Месяц"],
            "fact_mtd": cur_month["Факт"],
            "forecast_to_month_end": cur_month["Прогноз"],
            "expected_month_total": cur_month["Итог"],
            "forecast_share": cur_month["Доля прогноза в месяце, %"],
        }

    forecast_months = monthly_sheet[monthly_sheet["Статус месяца"].isin(["Текущий месяц", "Прогноз"])].copy()
    if not forecast_months.empty:
        top3 = forecast_months.sort_values("Итог", ascending=False).head(3)
        result["future_profile"] = {
            "months_count": len(forecast_months),
            "sum": forecast_months["Итог"].sum(),
            "avg": forecast_months["Итог"].mean(),
            "top_months": top3[["Месяц", "Итог"]].to_dict("records"),
        }

    return result


def prepare_analysis_sheet(monthly_sheet, yearly_sheet, last_actual_date):
    metrics = get_key_metrics(monthly_sheet, yearly_sheet, last_actual_date)
    rows = []

    if "last_year" in metrics:
        x = metrics["last_year"]
        rows.extend([
            {
                "Блок": "Закрытый год",
                "Показатель": f"Выручка {x['year']}",
                "Значение": x["revenue"],
                "Комментарий": "Фактическая выручка за полностью завершенный год",
            },
            {
                "Блок": "Закрытый год",
                "Показатель": "Изменение к предыдущему году, ₽",
                "Значение": x["delta_abs"],
                "Комментарий": "Абсолютное изменение выручки год к году",
            },
            {
                "Блок": "Закрытый год",
                "Показатель": "Изменение к предыдущему году, %",
                "Значение": x["delta_pct"],
                "Комментарий": "Темп роста / снижения год к году",
            },
        ])

    if "current_year" in metrics:
        x = metrics["current_year"]
        rows.extend([
            {
                "Блок": "Текущий год",
                "Показатель": f"Факт YTD {x['year']}",
                "Значение": x["fact_ytd"],
                "Комментарий": "Фактическая выручка с начала года по последнюю дату факта",
            },
            {
                "Блок": "Текущий год",
                "Показатель": f"Прогноз на остаток {x['year']}",
                "Значение": x["forecast_rest"],
                "Комментарий": "Прогнозная выручка после последней фактической даты",
            },
            {
                "Блок": "Текущий год",
                "Показатель": f"Ожидаемый итог {x['year']}",
                "Значение": x["expected_total"],
                "Комментарий": "Сумма факта YTD и прогноза до конца года",
            },
            {
                "Блок": "Текущий год",
                "Показатель": "Доля прогнозной части в годе, %",
                "Значение": x["forecast_share"],
                "Комментарий": "Часть ожидаемого годового результата, которая еще не подтверждена фактом",
            },
            {
                "Блок": "Текущий год",
                "Показатель": "Изменение к предыдущему году, ₽",
                "Значение": x["delta_abs"],
                "Комментарий": "Отклонение ожидаемого итога текущего года от полного предыдущего года",
            },
            {
                "Блок": "Текущий год",
                "Показатель": "Изменение к предыдущему году, %",
                "Значение": x["delta_pct"],
                "Комментарий": "Темп роста / снижения ожидаемого итога текущего года",
            },
        ])

    if "current_month" in metrics:
        x = metrics["current_month"]
        rows.extend([
            {
                "Блок": "Текущий месяц",
                "Показатель": f"Факт MTD {x['month']}",
                "Значение": x["fact_mtd"],
                "Комментарий": "Факт с начала месяца по последнюю дату факта",
            },
            {
                "Блок": "Текущий месяц",
                "Показатель": f"Прогноз до конца месяца {x['month']}",
                "Значение": x["forecast_to_month_end"],
                "Комментарий": "Оценка дохода до конца текущего месяца",
            },
            {
                "Блок": "Текущий месяц",
                "Показатель": f"Ожидаемый итог месяца {x['month']}",
                "Значение": x["expected_month_total"],
                "Комментарий": "Полный ожидаемый итог текущего месяца",
            },
        ])

    if "ltm" in metrics:
        x = metrics["ltm"]
        rows.extend([
            {
                "Блок": "Последние 12 месяцев",
                "Показатель": "Выручка LTM",
                "Значение": x["sum"],
                "Комментарий": "Сумма выручки за последние 12 месяцев",
            },
            {
                "Блок": "Последние 12 месяцев",
                "Показатель": "Среднемесячная выручка LTM",
                "Значение": x["avg"],
                "Комментарий": "Средний месячный уровень выручки",
            },
            {
                "Блок": "Последние 12 месяцев",
                "Показатель": f"Лучший месяц: {x['best_month']}",
                "Значение": x["best_value"],
                "Комментарий": "Максимальная месячная выручка",
            },
            {
                "Блок": "Последние 12 месяцев",
                "Показатель": f"Худший месяц: {x['worst_month']}",
                "Значение": x["worst_value"],
                "Комментарий": "Минимальная месячная выручка",
            },
        ])

    if "future_profile" in metrics:
        x = metrics["future_profile"]
        rows.extend([
            {
                "Блок": "Будущая доходная часть",
                "Показатель": "Сумма прогнозной части",
                "Значение": x["sum"],
                "Комментарий": "Совокупный ожидаемый доход по месяцам, где есть прогноз",
            },
            {
                "Блок": "Будущая доходная часть",
                "Показатель": "Средний прогнозный месяц",
                "Значение": x["avg"],
                "Комментарий": "Средняя ожидаемая выручка по будущим месяцам",
            },
            {
                "Блок": "Будущая доходная часть",
                "Показатель": "Количество месяцев с прогнозом",
                "Значение": x["months_count"],
                "Комментарий": "Месяцы, содержащие текущий месяц и будущие периоды",
            },
        ])

    return pd.DataFrame(rows)


def build_markdown_commentary(monthly_sheet, yearly_sheet, last_actual_date):
    last_actual_date = pd.to_datetime(last_actual_date)
    metrics = get_key_metrics(monthly_sheet, yearly_sheet, last_actual_date)

    parts = []
    parts.append("# Прогноз выручки")
    parts.append("")
    parts.append(f"**Дата последнего факта:** {last_actual_date.date()}")
    parts.append("")

    parts.append("## 1. Executive summary")
    parts.append("")

    if "last_year" in metrics:
        x = metrics["last_year"]
        parts.append(f"- Выручка **{x['year']}** года составила **{fmt_money(x['revenue'])} руб.**")
        if pd.notna(x["delta_abs"]):
            parts.append(
                f"- Изменение к предыдущему году: **{fmt_money(x['delta_abs'])} руб.** "
                f"(**{fmt_pct(x['delta_pct'])}**)."
            )

    if "current_year" in metrics:
        x = metrics["current_year"]
        parts.append(f"- Факт **{x['year']} YTD**: **{fmt_money(x['fact_ytd'])} руб.**")
        parts.append(f"- Прогноз на остаток **{x['year']}**: **{fmt_money(x['forecast_rest'])} руб.**")
        parts.append(f"- Ожидаемый итог **{x['year']}**: **{fmt_money(x['expected_total'])} руб.**")
        parts.append(f"- Доля прогнозной части в ожидаемом результате года: **{fmt_pct(x['forecast_share'])}**.")
        if pd.notna(x["delta_abs"]):
            parts.append(
                f"- Ожидаемое изменение к предыдущему году: **{fmt_money(x['delta_abs'])} руб.** "
                f"(**{fmt_pct(x['delta_pct'])}**)."
            )

    if "current_month" in metrics:
        x = metrics["current_month"]
        parts.append(
            f"- По текущему месяцу **{x['month']}**: факт MTD — **{fmt_money(x['fact_mtd'])} руб.**, "
            f"прогноз до конца месяца — **{fmt_money(x['forecast_to_month_end'])} руб.**, "
            f"ожидаемый итог месяца — **{fmt_money(x['expected_month_total'])} руб.**"
        )

    if "ltm" in metrics:
        x = metrics["ltm"]
        parts.append(
            f"- За последние 12 месяцев выручка составила **{fmt_money(x['sum'])} руб.**, "
            f"среднемесячный уровень — **{fmt_money(x['avg'])} руб.**"
        )
        parts.append(
            f"- Максимальный месяц: **{x['best_month']}** "
            f"(**{fmt_money(x['best_value'])} руб.**), "
            f"минимальный месяц: **{x['worst_month']}** "
            f"(**{fmt_money(x['worst_value'])} руб.**)."
        )

    if "future_profile" in metrics:
        x = metrics["future_profile"]
        parts.append(
            f"- Совокупная будущая доходная часть по месяцам с прогнозом составляет "
            f"**{fmt_money(x['sum'])} руб.**, средний прогнозный месяц — **{fmt_money(x['avg'])} руб.**."
        )
        if x["top_months"]:
            top_str = "; ".join([f"{i['Месяц']} — {fmt_money(i['Итог'])} руб." for i in x["top_months"]])
            parts.append(f"- Наиболее сильные прогнозные месяцы: **{top_str}**.")

    parts.append("")
    parts.append("## 2. Подход к отражению данных")
    parts.append("")
    parts.append("- Для завершенных лет в отчете отражается только фактическая выручка.")
    parts.append("- Для текущего года отражается факт с начала года плюс прогноз на остаток периода.")
    parts.append("- Для текущего месяца используется комбинированный подход: факт MTD + прогноз до конца месяца.")
    parts.append("- Для будущих месяцев и лет отражается прогнозная выручка.")

    parts.append("")
    parts.append("## 3. Комментарий по динамике")
    parts.append("")

    yoy = monthly_sheet.dropna(subset=["Изменение к тому же месяцу прошлого года, ₽"]).copy()
    yoy = yoy.sort_values("Изменение к тому же месяцу прошлого года, ₽", ascending=False)

    if not yoy.empty:
        top_growth = yoy.head(3)
        parts.append("Наиболее сильные месяцы по приросту к аналогичному месяцу прошлого года:")
        parts.append("")
        for _, row in top_growth.iterrows():
            parts.append(
                f"- **{row['Месяц']}**: {fmt_money(row['Изменение к тому же месяцу прошлого года, ₽'])} руб. "
                f"({fmt_pct(row['Изменение к тому же месяцу прошлого года, %'])})."
            )

    weak = monthly_sheet.dropna(subset=["Изменение к тому же месяцу прошлого года, ₽"]).copy()
    weak = weak.sort_values("Изменение к тому же месяцу прошлого года, ₽", ascending=True).head(3)
    if not weak.empty:
        parts.append("")
        parts.append("Наиболее слабые месяцы по сравнению с аналогичным месяцем прошлого года:")
        parts.append("")
        for _, row in weak.iterrows():
            parts.append(
                f"- **{row['Месяц']}**: {fmt_money(row['Изменение к тому же месяцу прошлого года, ₽'])} руб. "
                f"({fmt_pct(row['Изменение к тому же месяцу прошлого года, %'])})."
            )

    # parts.append("")
    # parts.append("## 4. Управленческий вывод")
    # parts.append("")
    # parts.append(
    #     "Ключевой ориентир для принятия решений — ожидаемый итог текущего года, "
    #     "в котором отдельно видны уже подтвержденный факт и еще не реализованная прогнозная часть."
    # )
    # parts.append(
    #     "Для управления доходной частью важно смотреть не только на итог за год, "
    #     "но и на структуру этого итога: насколько текущий результат уже подтвержден, "
    #     "какова доля будущих месяцев, и какие месяцы формируют основной вклад в рост."
    # )
    # parts.append(
    #     "Следующий шаг развития модели — добавить backtesting, сценарии base / downside / upside "
    #     "и при необходимости декомпозицию по каналам, магазинам, арендаторам или категориям."
    # )
    # parts.append("")

    return "\n".join(parts)