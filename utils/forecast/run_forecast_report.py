# utils/forecast/run_forecast_report.py
import pandas as pd

from config import (
    START_DATE,
    FORECAST_DATE,
    FILL_MISSING_DATES,
    PROPHET_PARAMS,
    OUTPUT_EXCEL_FILE,
    OUTPUT_MD_FILE,
    CHARTS_DIR,
)
from db import connect_db
from data_loader import get_revenue_data, get_last_actual_date
from model import make_forecast
from transforms import (
    prepare_daily_sheet,
    prepare_monthly_sheet,
    prepare_yearly_sheet,
    prepare_quarterly_sheet,
)
from analysis import prepare_analysis_sheet, build_markdown_commentary
from charts import build_all_charts
from excel_export import export_to_excel
from markdown_report import build_full_markdown_report


def prepare_settings_sheet(last_actual_date):
    rows = [
        {"Параметр": "START_DATE", "Значение": START_DATE, "Комментарий": "Начало исторического периода"},
        {"Параметр": "LAST_ACTUAL_DATE", "Значение": str(pd.to_datetime(last_actual_date).date()), "Комментарий": "Последняя дата факта, определенная автоматически из БД"},
        {"Параметр": "FORECAST_DATE", "Значение": FORECAST_DATE, "Комментарий": "Дата окончания прогноза"},
        {"Параметр": "FILL_MISSING_DATES", "Значение": str(FILL_MISSING_DATES), "Комментарий": "Заполнение пропусков нулями"},
    ]

    for k, v in PROPHET_PARAMS.items():
        rows.append({
            "Параметр": f"PROPHET_PARAMS.{k}",
            "Значение": str(v),
            "Комментарий": "Параметр модели Prophet",
        })

    return pd.DataFrame(rows)


def main():
    conn = connect_db()

    try:
        last_actual_date = get_last_actual_date(conn=conn, start_date=START_DATE)

        data = get_revenue_data(
            conn=conn,
            start_date=START_DATE,
            end_date=last_actual_date,
            fill_missing_dates=FILL_MISSING_DATES,
        )

        if data.empty:
            raise ValueError("Нет данных для прогноза")

        model, forecast = make_forecast(
            data=data,
            end_date=last_actual_date,
            forecast_date=FORECAST_DATE,
            prophet_params=PROPHET_PARAMS,
            freq="D",
        )

        daily_sheet = prepare_daily_sheet(data, forecast, last_actual_date)
        monthly_sheet = prepare_monthly_sheet(daily_sheet, last_actual_date)
        yearly_sheet = prepare_yearly_sheet(
            monthly_sheet=monthly_sheet,
            current_year=pd.to_datetime(last_actual_date).year,
            last_actual_date=last_actual_date,
        )
        quarterly_sheet = prepare_quarterly_sheet(monthly_sheet)

        analysis_sheet = prepare_analysis_sheet(
            monthly_sheet=monthly_sheet,
            yearly_sheet=yearly_sheet,
            last_actual_date=last_actual_date,
        )

        settings_sheet = prepare_settings_sheet(last_actual_date)

        export_to_excel(
            daily_sheet=daily_sheet,
            monthly_sheet=monthly_sheet,
            yearly_sheet=yearly_sheet,
            analysis_sheet=analysis_sheet,
            settings_sheet=settings_sheet,
            file_name=OUTPUT_EXCEL_FILE,
        )

        chart_paths = build_all_charts(
            monthly_sheet=monthly_sheet,
            yearly_sheet=yearly_sheet,
            quarterly_sheet=quarterly_sheet,
            charts_dir=CHARTS_DIR,
            last_actual_date=last_actual_date,
            current_year=pd.to_datetime(last_actual_date).year,
        )

        commentary_text = build_markdown_commentary(
            monthly_sheet=monthly_sheet,
            yearly_sheet=yearly_sheet,
            last_actual_date=last_actual_date,
        )

        md_report = build_full_markdown_report(
            commentary_text=commentary_text,
            analysis_sheet=analysis_sheet,
            yearly_sheet=yearly_sheet,
            quarterly_sheet=quarterly_sheet,
            monthly_sheet=monthly_sheet,
            chart_paths=chart_paths,
        )

        with open(OUTPUT_MD_FILE, "w", encoding="utf-8") as f:
            f.write(md_report)

        print(f"Последняя дата факта: {pd.to_datetime(last_actual_date).date()}")
        print(f"Excel сохранен: {OUTPUT_EXCEL_FILE}")
        print(f"Markdown сохранен: {OUTPUT_MD_FILE}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()