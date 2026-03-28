# utils/forecast/markdown_report.py
from config import MARKDOWN_STYLE
import pandas as pd


def fmt_money(x):
    if pd.isna(x):
        return "—"
    return f"{x:,.0f}".replace(",", " ")


def fmt_pct(x):
    if pd.isna(x):
        return "—"
    return f"{x:.1%}".replace(".", ",")


def format_value(col, val):
    if pd.isna(val):
        return "—"

    if isinstance(val, (int, float)):
        if "%" in col:
            return fmt_pct(val)
        return fmt_money(val)

    return str(val)


def dataframe_to_html_table(df):
    if df.empty:
        return "<p><i>Нет данных</i></p>"

    html = ['<table class="report-table">']
    html.append("<thead><tr>")
    for col in df.columns:
        html.append(f"<th>{col}</th>")
    html.append("</tr></thead>")
    html.append("<tbody>")

    for _, row in df.iterrows():
        html.append("<tr>")
        for col in df.columns:
            val = format_value(col, row[col])
            cls = "num" if isinstance(row[col], (int, float)) and not pd.isna(row[col]) else ""
            if col in ["Год", "Месяц", "Статус месяца", "Статус года", "Квартал"]:
                cls = "center" if col in ["Год"] else ""
            html.append(f'<td class="{cls}">{val}</td>')
        html.append("</tr>")

    html.append("</tbody></table>")
    return "".join(html)


def build_kpi_cards(analysis_sheet):
    if analysis_sheet.empty:
        return ""

    top = analysis_sheet.head(6).copy()
    parts = ['<table class="kpi-grid"><tr>']

    for _, row in top.iterrows():
        parts.append(
            f"""
            <td class="kpi-card">
                <div class="kpi-title">{row['Показатель']}</div>
                <div class="kpi-value">{format_value(row['Показатель'], row['Значение'])}</div>
            </td>
            """
        )

    parts.append("</tr></table>")
    return "".join(parts)


def build_full_markdown_report(
    commentary_text,
    analysis_sheet,
    yearly_sheet,
    quarterly_sheet,
    monthly_sheet,
    chart_paths,
):
    parts = [MARKDOWN_STYLE, ""]

    parts.append(commentary_text)
    parts.append("")

    # parts.append("## 5. Ключевые показатели")
    # parts.append("")
    # parts.append(build_kpi_cards(analysis_sheet))
    # parts.append("")
    # parts.append(dataframe_to_html_table(analysis_sheet))
    # parts.append("")

    # parts.append('<div class="page-break"></div>')
    parts.append("")
    parts.append("## 4. Графики")
    parts.append("")

    if "plan_fact_monthly" in chart_paths:
        parts.append("### 4.1. Помесячная динамика факта и прогноза")
        parts.append(f'![]({chart_paths["plan_fact_monthly"]})')
        parts.append('<div class="chart-caption">Основной график для оценки уровня выручки, перехода от факта к прогнозу и общей траектории.</div>')
        parts.append("")

    if "yoy_change_monthly" in chart_paths:
        parts.append("### 4.2. Изменение к аналогичному месяцу прошлого года")
        parts.append(f'![]({chart_paths["yoy_change_monthly"]})')
        parts.append('<div class="chart-caption">Показывает месяцы, формирующие рост или просадку относительно прошлого года.</div>')
        parts.append("")

    if "waterfall_current_year" in chart_paths:
        parts.append("### 4.3. Формирование итога текущего года по месяцам")
        parts.append(f'![]({chart_paths["waterfall_current_year"]})')
        parts.append('<div class="chart-caption">Показывает вклад каждого месяца в ожидаемый годовой результат.</div>')
        parts.append("")

    if "quarterly_revenue" in chart_paths:
        parts.append("### 4.4. Квартальная динамика")
        parts.append(f'![]({chart_paths["quarterly_revenue"]})')
        parts.append('<div class="chart-caption">Сглаженный взгляд на динамику без избыточного месячного шума.</div>')
        parts.append("")

    parts.append('<div class="page-break"></div>')
    parts.append("")
    parts.append("## 5. Сводка по годам")
    parts.append("")
    parts.append(dataframe_to_html_table(
        yearly_sheet[[
            "Год",
            "Факт",
            "Прогноз",
            "Итог",
            "Статус года",
            "Изменение к пред. году, ₽",
            "Изменение к пред. году, %",
        ]]
    ))
    parts.append("")

    parts.append("## 6. Сводка по кварталам")
    parts.append("")
    parts.append(dataframe_to_html_table(
        quarterly_sheet[[
            "Квартал",
            "Факт",
            "Прогноз",
            "Итог",
            "Изменение к пред. кварталу, ₽",
            "Изменение к пред. кварталу, %",
        ]]
    ))
    parts.append("")

    parts.append('<div class="page-break"></div>')
    parts.append("")
    parts.append("## 7. Сводка по месяцам")
    parts.append("")
    parts.append(dataframe_to_html_table(
        monthly_sheet[[
            "Месяц",
            "Статус месяца",
            "Факт",
            "Прогноз",
            "Итог",
            "Доля факта в месяце, %",
            "Доля прогноза в месяце, %",
        ]]
    ))
    parts.append("")

    parts.append("## 8. Сводка по месяцам: динамика")
    parts.append("")
    parts.append(dataframe_to_html_table(
        monthly_sheet[[
            "Месяц",
            "Изменение к пред. месяцу, ₽",
            "Изменение к пред. месяцу, %",
            "Изменение к тому же месяцу прошлого года, ₽",
            "Изменение к тому же месяцу прошлого года, %",
        ]]
    ))
    parts.append("")

    return "\n".join(parts)