# budget/reporting/pdf/charts/ytd_waterfall_chart.py
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
from datetime import datetime

from budget.reporting.pdf.charts.base import fig_to_base64, remove_inner_frame
from budget.reporting.pdf.charts.helpers import format_price_axis_ru
from budget.reporting.pdf.charts.styles import (
    COLOR_BG, COLOR_GRID, COLOR_POSITIVE, COLOR_NEGATIVE, 
    COLOR_TEXT, COLOR_MUTED, COLOR_PRIMARY, COLOR_TREND
)


def build_ytd_plan_fact_chart_base64(ytd_data, title="Накопленные итоги (YTD): План vs Факт"):
    """Строит график накопленных план/факт"""
    if not ytd_data:
        return None
    
    months = [item["month_label"] for item in ytd_data]
    plan_values = [item["plan"] for item in ytd_data]
    fact_values = [item["fact"] for item in ytd_data]
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    
    x = np.arange(len(months))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, plan_values, width, label='План WB', 
                   color='#2E7D32', alpha=0.7, edgecolor='white')
    bars2 = ax.bar(x + width/2, fact_values, width, label='Факт', 
                   color='#1976D2', alpha=0.7, edgecolor='white')
    
    # Добавляем значения на столбцы
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   format_price_axis_ru(height, 0),
                   ha='center', va='bottom', fontsize=7, rotation=45)
    
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   format_price_axis_ru(height, 0),
                   ha='center', va='bottom', fontsize=7, rotation=45)
    
    ax.set_title(title, fontsize=12, color=COLOR_TEXT, pad=12, fontweight='bold')
    ax.set_ylabel("Сумма, руб.", fontsize=10, color=COLOR_TEXT)
    ax.set_xlabel("Период", fontsize=10, color=COLOR_TEXT)
    ax.set_xticks(x)
    ax.set_xticklabels(months, rotation=45, ha='right')
    ax.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax.legend(loc='upper left', fontsize=10, frameon=True, fancybox=True, shadow=True)
    ax.tick_params(axis='both', labelsize=9, colors=COLOR_TEXT)
    ax.grid(True, linestyle='--', linewidth=0.5, color=COLOR_GRID, alpha=0.3, axis='y')
    remove_inner_frame(ax, keep_bottom=True)
    
    fig.tight_layout()
    return fig_to_base64(fig)


def build_ytd_waterfall_chart_base64(ytd_data, title="Накопленное отклонение (YTD)"):
    """Строит водопадный график накопленных отклонений"""
    if not ytd_data:
        return None
    
    months = [item["month_label"] for item in ytd_data]
    deltas = [item["delta"] for item in ytd_data]
    
    fig, ax = plt.subplots(figsize=(12, 5), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    
    colors = [COLOR_POSITIVE if d >= 0 else COLOR_NEGATIVE for d in deltas]
    
    bars = ax.bar(months, deltas, color=colors, edgecolor='white', linewidth=0.8, alpha=0.8)
    
    # Добавляем значения на столбцы
    for bar, delta in zip(bars, deltas):
        height = bar.get_height()
        va = 'bottom' if height >= 0 else 'top'
        offset = abs(height) * 0.05
        y_pos = height + offset if height >= 0 else height - offset
        
        ax.text(bar.get_x() + bar.get_width()/2., y_pos,
                format_price_axis_ru(delta, 0),
                ha='center', va=va, fontsize=8, color=COLOR_TEXT, fontweight='bold')
    
    ax.axhline(y=0, color=COLOR_MUTED, linestyle='-', linewidth=0.8, alpha=0.5)
    ax.set_title(title, fontsize=12, color=COLOR_TEXT, pad=12, fontweight='bold')
    ax.set_ylabel("Отклонение, руб.", fontsize=10, color=COLOR_TEXT)
    ax.set_xlabel("Месяц", fontsize=10, color=COLOR_TEXT)
    ax.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax.tick_params(axis='both', labelsize=9, colors=COLOR_TEXT)
    ax.grid(True, linestyle='--', linewidth=0.5, color=COLOR_GRID, alpha=0.3, axis='y')
    remove_inner_frame(ax, keep_bottom=True)
    
    plt.xticks(rotation=45, ha='right')
    fig.tight_layout()
    
    return fig_to_base64(fig)


def build_ytd_speedometer_chart_base64(execution_pct, report_date):
    """Строит спидометр выполнения плана YTD"""
    fig, ax = plt.subplots(figsize=(8, 6), dpi=180, subplot_kw={'projection': 'polar'})
    fig.patch.set_facecolor(COLOR_BG)
    
    # Настройки для полукруга
    theta = np.linspace(0, np.pi, 100)
    
    # Цветовые зоны
    colors_zones = [
        (0, 0.7, '#C62828'),      # 0-70% - красный
        (0.7, 0.9, '#FFA726'),    # 70-90% - оранжевый
        (0.9, 1.0, '#2E7D32'),    # 90-100% - зеленый
        (1.0, 1.2, '#1B5E20')     # 100%+ - темно-зеленый
    ]
    
    # Рисуем зоны
    for start, end, color in colors_zones:
        theta_zone = np.linspace(start * np.pi, end * np.pi, 50)
        r_zone = np.ones_like(theta_zone) * 0.8
        ax.fill_between(theta_zone, 0, r_zone, alpha=0.3, color=color)
    
    # Стрелка-указатель
    angle = (execution_pct / 100) * np.pi
    angle = min(angle, np.pi)  # Ограничиваем 180 градусами
    
    ax.annotate('', xy=(angle, 0.7), xytext=(0, 0),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    # Значение в центре
    ax.text(0, 0, f"{execution_pct:.1f}%", 
            ha='center', va='center', fontsize=24, fontweight='bold',
            color=COLOR_TEXT)
    ax.text(0, -0.2, f"Выполнение плана\n{report_date.strftime('%d.%m.%Y')}",
            ha='center', va='center', fontsize=9, color=COLOR_MUTED)
    
    # Метки
    for pct, label in [(0, '0%'), (50, '50%'), (70, '70%'), (90, '90%'), (100, '100%'), (120, '120%')]:
        angle_label = (pct / 100) * np.pi
        ax.text(angle_label, 0.9, label, ha='center', va='center', fontsize=8)
    
    ax.set_ylim(0, 1)
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.spines['polar'].set_visible(False)
    ax.grid(False)
    
    fig.tight_layout()
    return fig_to_base64(fig)


def build_ytd_forecast_chart_base64(ytd_data, semi_annual_analysis):
    """Строит прогнозный график выполнения планов"""
    if not ytd_data:
        return None
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    
    # Левый график: План vs Факт с прогнозом
    months = [item["month_label"] for item in ytd_data]
    plan_values = [item["plan"] for item in ytd_data]
    fact_values = [item["fact"] for item in ytd_data]
    
    x = np.arange(len(months))
    width = 0.35
    
    ax1.bar(x - width/2, plan_values, width, label='План WB', 
            color='#2E7D32', alpha=0.7)
    ax1.bar(x + width/2, fact_values, width, label='Факт', 
            color='#1976D2', alpha=0.7)
    
    # Прогноз на конец периода
    if semi_annual_analysis:
        current_sem = next((s for s in semi_annual_analysis if s.get("is_current")), None)
        if current_sem:
            projected = current_sem["projected_end"]
            ax1.axhline(y=projected, color=COLOR_TREND, linestyle='--', 
                       linewidth=2, label=f'Прогноз: {format_price_axis_ru(projected, 0)}')
    
    ax1.set_title('Выполнение плана с прогнозом', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Сумма, руб.')
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, rotation=45, ha='right', fontsize=8)
    ax1.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    # Правый график: Необходимый темп продаж
    if semi_annual_analysis:
        current_sem = next((s for s in semi_annual_analysis if s.get("is_current")), None)
        if current_sem:
            categories = ['Текущий темп', 'Необходимый темп']
            values = [
                current_sem["current_daily_rate"],
                current_sem["required_daily_rate"]
            ]
            colors_bar = ['#1976D2', '#C62828'] if values[0] < values[1] else ['#2E7D32', '#1976D2']
            
            bars = ax2.bar(categories, values, color=colors_bar, alpha=0.7, edgecolor='white')
            
            for bar, val in zip(bars, values):
                ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                        format_price_axis_ru(val, 0),
                        ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            ax2.set_title('Дневной темп продаж', fontsize=11, fontweight='bold')
            ax2.set_ylabel('Руб./день')
            ax2.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
            ax2.grid(True, linestyle='--', alpha=0.3, axis='y')
            
            # Добавляем пояснение
            gap = current_sem["required_daily_rate"] - current_sem["current_daily_rate"]
            if gap > 0:
                ax2.text(0.5, -0.25, f'Необходимо увеличить на {format_price_axis_ru(gap, 0)} руб./день',
                        transform=ax2.transAxes, ha='center', fontsize=9, color='#C62828')
            else:
                ax2.text(0.5, -0.25, f'Темп достаточен для выполнения плана',
                        transform=ax2.transAxes, ha='center', fontsize=9, color='#2E7D32')
    
    remove_inner_frame(ax1, keep_bottom=True)
    remove_inner_frame(ax2, keep_bottom=True)
    
    fig.tight_layout()
    return fig_to_base64(fig)


def build_daily_execution_chart_base64(daily_analysis):
    """Строит график дневного выполнения"""
    if not daily_analysis or not daily_analysis.get("days"):
        return None
    
    days_data = daily_analysis["days"]
    days = [d["day"] for d in days_data]
    plan_values = [d["plan_day"] for d in days_data]
    fact_values = [d["fact_day"] for d in days_data]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    
    # Верхний график: дневные продажи
    x = np.arange(len(days))
    width = 0.35
    
    ax1.bar(x - width/2, plan_values, width, label='План на день', 
            color='#2E7D32', alpha=0.7)
    ax1.bar(x + width/2, fact_values, width, label='Факт за день', 
            color='#1976D2', alpha=0.7)
    
    # Выделяем дни с перевыполнением
    for i, (plan, fact) in enumerate(zip(plan_values, fact_values)):
        if fact > plan:
            ax1.plot(x[i] + width/2, fact, 'ro', markersize=6)
    
    ax1.set_title(f'Дневные продажи: {daily_analysis["month_name"]}', 
                  fontsize=11, fontweight='bold')
    ax1.set_ylabel('Сумма, руб.')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{d['day']}\n{d['weekday']}" for d in days_data], 
                        rotation=0, ha='center', fontsize=8)
    ax1.yaxis.set_major_formatter(FuncFormatter(format_price_axis_ru))
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
    
    # Нижний график: накопленное выполнение
    running_pct = [d["running_execution_pct"] for d in days_data]
    
    ax2.plot(days, running_pct, marker='o', linewidth=2, color=COLOR_PRIMARY)
    ax2.fill_between(days, running_pct, 100, where=[p >= 100 for p in running_pct],
                     color='#2E7D32', alpha=0.3)
    ax2.fill_between(days, running_pct, 100, where=[p < 100 for p in running_pct],
                     color='#C62828', alpha=0.3)
    ax2.axhline(y=100, color='#C62828', linestyle='--', linewidth=1.5, label='План 100%')
    
    ax2.set_title('Накопленное выполнение плана (YTD месяц)', fontsize=11, fontweight='bold')
    ax2.set_xlabel('День месяца')
    ax2.set_ylabel('Выполнение, %')
    ax2.set_ylim(0, max(150, max(running_pct) * 1.1))
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.3, axis='both')
    
    for day, pct in zip(days, running_pct):
        ax2.annotate(f'{pct:.0f}%', (day, pct), textcoords="offset points", 
                    xytext=(0, 10), ha='center', fontsize=8)
    
    remove_inner_frame(ax1, keep_bottom=True)
    remove_inner_frame(ax2, keep_bottom=True)
    
    fig.tight_layout()
    return fig_to_base64(fig)