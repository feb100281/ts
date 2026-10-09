# utils/forecast/config.py
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
CHARTS_DIR = OUTPUT_DIR / "charts"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

DB_CONFIG = {
    "dbname": "ts_db",
    "user": "ts_user",
    "password": "Dec8108079",
    "host": "127.0.0.1",
    "port": "5433",
    "connect_timeout": 10,
}

START_DATE = "2024-01-01"
FORECAST_DATE = "2026-12-31"

OUTPUT_EXCEL_FILE = OUTPUT_DIR / "forecast_revenue.xlsx"
OUTPUT_MD_FILE = OUTPUT_DIR / "forecast_report.md"

FILL_MISSING_DATES = True

PROPHET_PARAMS = {
    "seasonality_mode": "multiplicative",
    "changepoint_prior_scale": 0.08,
    "seasonality_prior_scale": 10.0,
    "holidays_prior_scale": 10.0,
    "interval_width": 0.8,
    "yearly_seasonality": True,
    "weekly_seasonality": True,
    "daily_seasonality": False,
    "add_monthly_seasonality": True,
    "monthly_period": 30.5,
    "monthly_fourier_order": 5,
}

REPORT_TITLE = "Прогноз выручки"
CURRENCY_LABEL = "руб."

MARKDOWN_STYLE = """
<style>
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 12px;
    line-height: 1.45;
    color: #1f2937;
    margin: 22px;
}

h1, h2, h3 {
    color: #111827;
    margin-top: 18px;
    margin-bottom: 8px;
}

h1 {
    font-size: 22px;
    border-bottom: 2px solid #d1d5db;
    padding-bottom: 6px;
}

h2 {
    font-size: 16px;
    border-left: 4px solid #374151;
    padding-left: 8px;
}

h3 {
    font-size: 13px;
}

p, li {
    margin: 5px 0;
}

.small-note {
    color: #6b7280;
    font-size: 10px;
}

table.report-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 18px 0;
    font-size: 10.5px;
    table-layout: fixed;
}

table.report-table th,
table.report-table td {
    border: 1px solid #d1d5db;
    padding: 6px 7px;
    vertical-align: middle;
    word-wrap: break-word;
}

table.report-table th {
    background: #f3f4f6;
    text-align: center;
    font-weight: 700;
}

table.report-table td.num {
    text-align: right;
    white-space: nowrap;
}

table.report-table td.center {
    text-align: center;
}

table.report-table tr:nth-child(even) {
    background: #fafafa;
}

.kpi-grid {
    width: 100%;
    margin: 14px 0 18px 0;
    border-collapse: separate;
    border-spacing: 10px;
}

.kpi-card {
    border: 1px solid #d1d5db;
    background: #f9fafb;
    padding: 10px 12px;
    border-radius: 8px;
}

.kpi-title {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    margin-bottom: 4px;
}

.kpi-value {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
}

.page-break {
    page-break-before: always;
}

.chart-caption {
    font-size: 10px;
    color: #6b7280;
    margin-top: -4px;
    margin-bottom: 8px;
}
</style>
"""