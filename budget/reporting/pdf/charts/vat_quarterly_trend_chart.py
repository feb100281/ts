# budget/reporting/pdf/charts/vat_quarterly_trend_chart.py

from io import BytesIO
import base64
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from budget.reporting.pdf.charts.styles import (
    COLOR_PRIMARY,
    COLOR_LINE,
    COLOR_GRID,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_POSITIVE,
    COLOR_NEGATIVE,
)


def _format_money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def build_vat_quarterly_trend_chart_base64(quarter_rows: list, as_of_date: date) -> str | None:
    """
    Строит линейный график динамики НДС по кварталам (только для завершенных кварталов).
    
    Args:
        quarter_rows: список кварталов из контекста
        as_of_date: текущая дата отчета
    """
    if not quarter_rows:
        return None
    
    # Определяем текущий квартал
    current_month = as_of_date.month
    current_quarter = (current_month - 1) // 3 + 1
    
    # Фильтруем только завершенные кварталы (включая текущий, если он завершен)
    # и только те, у которых есть продажи
    filtered_rows = []
    for row in quarter_rows:
        quarter_num = int(row['quarter'][1])  # Q1 -> 1, Q2 -> 2
        
        # Пропускаем будущие кварталы
        if quarter_num > current_quarter:
            continue
        
        current_vat = float(row.get('current_net_vat', 0) or 0)
        previous_vat = float(row.get('previous_net_vat', 0) or 0)
        
        # Добавляем только если есть хоть какие-то данные
        if current_vat > 0 or previous_vat > 0:
            filtered_rows.append(row)
    
    if not filtered_rows:
        return None
    
    # Подготавливаем данные
    quarters = []
    current_vat = []
    previous_vat = []
    changes = []
    
    for row in filtered_rows:
        quarters.append(row['quarter'])
        current_vat.append(float(row.get('current_net_vat', 0) or 0))
        previous_vat.append(float(row.get('previous_net_vat', 0) or 0))
        changes.append(float(row.get('net_vat_change_pct', 0) or 0))
    
    plt.close("all")
    
    # Уменьшенный размер графика
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.5), dpi=150, 
                                     gridspec_kw={'height_ratios': [2, 1]})
    fig.patch.set_facecolor(COLOR_BG)
    ax1.set_facecolor(COLOR_BG)
    ax2.set_facecolor(COLOR_BG)
    
    x = np.arange(len(quarters))
    
    # ============ Верхний график: линии НДС ============
    # Линия текущего года
    line1, = ax1.plot(x, current_vat, 
                      color=COLOR_PRIMARY, 
                      linewidth=2.2, 
                      marker='o', 
                      markersize=5,
                      markerfacecolor=COLOR_PRIMARY,
                      markeredgecolor=COLOR_BG,
                      markeredgewidth=1.2,
                      label=f'НДС {filtered_rows[0]["year"] if filtered_rows else "текущий год"}',
                      zorder=3)
    
    # Линия прошлого года (только если есть данные)
    if any(previous_vat):
        line2, = ax1.plot(x, previous_vat, 
                          color=COLOR_LINE, 
                          linewidth=1.8, 
                          marker='s', 
                          markersize=4.5,
                          markerfacecolor=COLOR_LINE,
                          markeredgecolor=COLOR_BG,
                          markeredgewidth=1,
                          linestyle='--',
                          label=f'НДС {filtered_rows[0]["year"] - 1 if filtered_rows else "прошлый год"}',
                          zorder=2)
        
        # Заливка между линиями (только где есть оба значения)
        mask_current_gt = np.array([c > p if p > 0 else False for c, p in zip(current_vat, previous_vat)])
        mask_prev_gt = np.array([p > c if c > 0 else False for c, p in zip(current_vat, previous_vat)])
        
        if any(mask_current_gt):
            ax1.fill_between(x, current_vat, previous_vat, 
                              where=mask_current_gt,
                              color=COLOR_POSITIVE, alpha=0.12, interpolate=True,
                              label='Рост')
        if any(mask_prev_gt):
            ax1.fill_between(x, current_vat, previous_vat, 
                              where=mask_prev_gt,
                              color=COLOR_NEGATIVE, alpha=0.12, interpolate=True,
                              label='Снижение')
    
    # Подписи значений только для последней точки текущего года
    if current_vat and current_vat[-1] > 0:
        ax1.annotate(
            _format_money(current_vat[-1]),
            xy=(x[-1], current_vat[-1]),
            xytext=(5, 8),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=7,
            color=COLOR_PRIMARY,
            fontweight='bold',
            bbox=dict(
                boxstyle="round,pad=0.15",
                facecolor=COLOR_BG,
                edgecolor=COLOR_PRIMARY,
                linewidth=0.6,
                alpha=0.9
            ),
            zorder=4
        )
    
    # Настройка осей верхнего графика
    ax1.set_xticks(x)
    ax1.set_xticklabels(quarters, fontsize=9, fontweight='bold', color=COLOR_TEXT)
    ax1.set_ylabel('Сумма НДС, руб.', fontsize=8, color=COLOR_MUTED)
    
    # Форматирование y-оси
    from matplotlib.ticker import FuncFormatter
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, p: _format_money(x)))
    ax1.tick_params(axis='y', labelsize=7, colors=COLOR_MUTED)
    
    # Сетка и рамки
    ax1.grid(axis='y', color=COLOR_GRID, linewidth=0.6, alpha=0.6, linestyle='--')
    ax1.grid(axis='x', visible=False)
    ax1.set_axisbelow(True)
    
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_color(COLOR_BORDER)
    ax1.spines['bottom'].set_color(COLOR_BORDER)
    
    # Легенда (компактная)
    if any(previous_vat):
        ax1.legend(loc='upper left', frameon=True, fancybox=False, 
                   edgecolor=COLOR_BORDER, fontsize=7, facecolor=COLOR_BG, 
                   handlelength=1.5, handletextpad=0.8)
    
    ax1.set_title('Динамика НДС по кварталам', loc='left', fontsize=10, 
                  fontweight='bold', color=COLOR_TEXT, pad=8)
    
    # ============ Нижний график: бары изменений ============
    if any(changes):
        colors = [COLOR_POSITIVE if change >= 0 else COLOR_NEGATIVE for change in changes]
        bars = ax2.bar(x, changes, width=0.5, color=colors, alpha=0.7, 
                       edgecolor=COLOR_BORDER, linewidth=0.6)
        
        # Добавляем значения процентов
        for bar, change in zip(bars, changes):
            height = bar.get_height()
            sign = '+' if change >= 0 else ''
            ax2.annotate(
                f'{sign}{change:.1f}%',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3 if height >= 0 else -10),
                textcoords="offset points",
                ha='center',
                va='bottom' if height >= 0 else 'top',
                fontsize=7,
                fontweight='bold',
                color=colors[0] if change >= 0 else colors[0],
            )
        
        ax2.axhline(y=0, color=COLOR_MUTED, linewidth=0.8, linestyle='-', alpha=0.5)
    
    # Настройка нижнего графика
    ax2.set_xticks(x)
    ax2.set_xticklabels(quarters, fontsize=8, color=COLOR_MUTED)
    ax2.set_ylabel('Изменение, %', fontsize=8, color=COLOR_MUTED)
    
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:+.0f}%'))
    ax2.tick_params(axis='y', labelsize=7, colors=COLOR_MUTED)
    
    ax2.grid(axis='y', color=COLOR_GRID, linewidth=0.6, alpha=0.5, linestyle='--')
    ax2.grid(axis='x', visible=False)
    ax2.set_axisbelow(True)
    
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_color(COLOR_BORDER)
    ax2.spines['bottom'].set_color(COLOR_BORDER)
    
    plt.tight_layout(pad=1.5)
    
    buffer = BytesIO()
    fig.savefig(
        buffer,
        format='png',
        bbox_inches='tight',
        facecolor=fig.get_facecolor(),
        dpi=150,
    )
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    buffer.close()
    plt.close(fig)
    
    return image_base64