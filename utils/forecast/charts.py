# utils/forecast/charts.py
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import pandas as pd


def rub_mln_formatter(x, pos):
    return f"{x / 1_000_000:,.0f}".replace(",", " ") + " млн"


def _setup_axes(ax, title, subtitle=None, ylabel="млн руб."):
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold")
    if subtitle:
        ax.text(
            0, 1.02, subtitle,
            transform=ax.transAxes,
            fontsize=9,
            color="#6b7280"
        )
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(FuncFormatter(rub_mln_formatter))


def save_plan_fact_chart(monthly_sheet, output_path, last_actual_date):
    df = monthly_sheet.copy().sort_values("Месяц_dt").reset_index(drop=True)
    last_actual_date = pd.to_datetime(last_actual_date)
    cutoff = last_actual_date.replace(day=1)

    fig, ax = plt.subplots(figsize=(15, 6.5))

    total_series = pd.to_numeric(df["Итог"], errors="coerce").astype(float)
    fact_series = pd.to_numeric(df["Факт"], errors="coerce").astype(float).replace(0, float("nan"))
    forecast_series = pd.to_numeric(df["Прогноз"], errors="coerce").astype(float).replace(0, float("nan"))

    ax.plot(df["Месяц_dt"], total_series, linewidth=2.8, label="Итог")
    ax.plot(df["Месяц_dt"], fact_series, linewidth=2.0, linestyle="--", label="Факт")
    ax.plot(df["Месяц_dt"], forecast_series, linewidth=2.0, linestyle=":", label="Прогноз")

    future_mask = df["Месяц_dt"] >= cutoff
    if future_mask.any():
        ax.axvspan(
            cutoff,
            df["Месяц_dt"].max(),
            alpha=0.08
        )

    ax.axvline(last_actual_date, linestyle="--", linewidth=1.2)

    _setup_axes(
        ax,
        "Помесячная динамика выручки: факт и прогноз",
        f"Вертикальная линия показывает последнюю фактическую дату: {last_actual_date.date()}"
    )

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    if not df.empty and pd.notna(total_series.iloc[-1]):
        last_row = df.iloc[-1]
        last_val = float(total_series.iloc[-1])
        ax.annotate(
            f"{last_val/1_000_000:,.0f} млн".replace(",", " "),
            xy=(last_row["Месяц_dt"], last_val),
            xytext=(10, 10),
            textcoords="offset points",
            fontsize=9
        )

    ax.legend(frameon=False, ncol=3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()
    
    
    
def save_yoy_chart(monthly_sheet, output_path):
    df = monthly_sheet.copy().sort_values("Месяц_dt")
    df = df.dropna(subset=["Изменение к тому же месяцу прошлого года, ₽"]).copy()

    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(15, 6))

    bars = ax.bar(
        df["Месяц_dt"],
        df["Изменение к тому же месяцу прошлого года, ₽"],
        width=20
    )

    ax.axhline(0, linewidth=1)
    _setup_axes(
        ax,
        "Изменение выручки к аналогичному месяцу прошлого года",
        "Положительные значения означают рост к прошлому году"
    )

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    for rect, val in zip(bars, df["Изменение к тому же месяцу прошлого года, ₽"]):
        if pd.notna(val):
            ax.annotate(
                f"{val / 1_000_000:,.0f}".replace(",", " "),
                xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
                xytext=(0, 3 if val >= 0 else -12),
                textcoords="offset points",
                ha="center",
                fontsize=8
            )

    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()


def save_waterfall_current_year_chart(monthly_sheet, output_path, current_year):
    df = monthly_sheet.copy()
    df = df[df["Год"] == current_year].sort_values("Месяц_dt").copy()

    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(15, 6))

    labels = df["Месяц"].tolist()
    values = df["Итог"].tolist()
    ax.bar(labels, values)

    _setup_axes(
        ax,
        f"Формирование ожидаемого итога {current_year} года по месяцам",
        "Столбцы показывают вклад каждого месяца в годовой итог"
    )

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    for i, v in enumerate(values):
        ax.annotate(
            f"{v / 1_000_000:,.0f}".replace(",", " "),
            xy=(i, v),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            fontsize=8
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()


def save_quarterly_chart(quarterly_sheet, output_path):
    df = quarterly_sheet.copy()
    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(14, 5.8))
    ax.bar(df["Квартал"], df["Итог"])

    _setup_axes(
        ax,
        "Квартальная динамика выручки",
        "Позволяет увидеть более устойчивый тренд без месячного шума"
    )

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()


def build_all_charts(monthly_sheet, yearly_sheet, quarterly_sheet, charts_dir, last_actual_date, current_year):
    charts_dir = Path(charts_dir)
    charts_dir.mkdir(parents=True, exist_ok=True)

    chart_1 = charts_dir / "plan_fact_monthly.png"
    chart_2 = charts_dir / "yoy_change_monthly.png"
    chart_3 = charts_dir / "waterfall_current_year.png"
    chart_4 = charts_dir / "quarterly_revenue.png"

    save_plan_fact_chart(monthly_sheet, chart_1, last_actual_date)
    save_yoy_chart(monthly_sheet, chart_2)
    save_waterfall_current_year_chart(monthly_sheet, chart_3, current_year)
    save_quarterly_chart(quarterly_sheet, chart_4)

    return {
        "plan_fact_monthly": chart_1,
        "yoy_change_monthly": chart_2,
        "waterfall_current_year": chart_3,
        "quarterly_revenue": chart_4,
    }