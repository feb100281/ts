# # gear/app/daily_sales/wb_plan_monitor/prophet_note/charts.py
# from __future__ import annotations

# from io import BytesIO
# from typing import Any

# import matplotlib.pyplot as plt
# from matplotlib import font_manager
# from matplotlib.ticker import FuncFormatter
# import numpy as np
# import pandas as pd

# from .formatting import MONTHS_SHORT_RU


# # =============================================================================
# # Палитра графиков
# # =============================================================================

# COLOR_FACT = "#2563EB"
# COLOR_FORECAST = "#0F766E"
# COLOR_PLAN = "#F97316"

# COLOR_POSITIVE = "#15803D"
# COLOR_NEGATIVE = "#B91C1C"

# COLOR_TEXT = "#0F172A"
# COLOR_SECONDARY = "#475569"
# COLOR_MUTED = "#64748B"
# COLOR_GRID = "#E2E8F0"
# COLOR_WHITE = "#FFFFFF"


# def _configure_matplotlib() -> None:
#     """
#     Единые настройки графиков PDF.

#     DejaVu Sans содержит кириллицу и знак рубля.
#     """
#     regular_path = font_manager.findfont(
#         font_manager.FontProperties(
#             family="DejaVu Sans",
#             weight="normal",
#         )
#     )
#     bold_path = font_manager.findfont(
#         font_manager.FontProperties(
#             family="DejaVu Sans",
#             weight="bold",
#         )
#     )

#     font_manager.fontManager.addfont(regular_path)
#     font_manager.fontManager.addfont(bold_path)

#     plt.rcParams.update(
#         {
#             "font.family": "DejaVu Sans",
#             "font.size": 9,
#             "axes.titlesize": 12,
#             "axes.titleweight": 700,
#             "axes.labelsize": 9,
#             "axes.labelcolor": COLOR_SECONDARY,
#             "axes.edgecolor": COLOR_GRID,
#             "axes.facecolor": COLOR_WHITE,
#             "figure.facecolor": COLOR_WHITE,
#             "xtick.color": COLOR_SECONDARY,
#             "ytick.color": COLOR_SECONDARY,
#             "text.color": COLOR_TEXT,
#             "legend.fontsize": 8.5,
#         }
#     )


# _configure_matplotlib()


# def _millions_formatter(value, position) -> str:
#     return (
#         f"{value:,.0f}"
#         .replace(",", " ")
#     )


# def _format_value_mln(value: float) -> str:
#     return (
#         f"{float(value or 0):,.0f}"
#         .replace(",", " ")
#     )


# def _save_figure(
#     fig,
#     *,
#     dpi: int = 300,
# ) -> BytesIO:
#     """
#     Сохраняет график в высоком разрешении.

#     300 DPI достаточно для:
#     - просмотра PDF с увеличением;
#     - качественной печати;
#     - вставки графика на страницу A4.
#     """
#     output = BytesIO()

#     fig.savefig(
#         output,
#         format="png",
#         dpi=dpi,
#         bbox_inches="tight",
#         pad_inches=0.08,
#         facecolor=COLOR_WHITE,
#         edgecolor="none",
#         transparent=False,
#     )

#     plt.close(fig)
#     output.seek(0)

#     return output


# # =============================================================================
# # План / факт / прогноз по месяцам
# # =============================================================================

# def build_monthly_plan_chart(
#     monthly_rows: list[dict[str, Any]],
# ) -> BytesIO:
#     """
#     Профессиональный помесячный график.

#     Логика:
#     - факт и прогноз показываются накопленным столбиком;
#     - сумма двух частей равна ожидаемому итогу месяца;
#     - план WB показывается отдельной линией;
#     - линия факта не падает в ноль на будущих месяцах.
#     """
#     df = pd.DataFrame(monthly_rows).copy()

#     if df.empty:
#         raise ValueError(
#             "Нет помесячных данных для графика."
#         )

#     required_columns = [
#         "month",
#         "plan",
#         "fact",
#         "forecast",
#         "expected_total",
#         "delta_to_plan",
#         "plan_exec_pct",
#     ]

#     for column in required_columns:
#         if column not in df.columns:
#             df[column] = 0.0

#     df["month_date"] = pd.to_datetime(
#         df["month"].astype(str) + "-01",
#         errors="coerce",
#     )

#     df = (
#         df.dropna(subset=["month_date"])
#         .sort_values("month_date")
#         .reset_index(drop=True)
#     )

#     df["month_label"] = (
#         df["month_date"]
#         .dt.month
#         .map(MONTHS_SHORT_RU)
#     )

#     for column in (
#         "plan",
#         "fact",
#         "forecast",
#         "expected_total",
#         "delta_to_plan",
#         "plan_exec_pct",
#     ):
#         df[column] = pd.to_numeric(
#             df[column],
#             errors="coerce",
#         ).fillna(0.0)

#     # Все значения графика отображаем в млн ₽.
#     plan = df["plan"] / 1_000_000
#     fact = df["fact"] / 1_000_000
#     forecast = df["forecast"] / 1_000_000
#     expected = df["expected_total"] / 1_000_000

#     x = np.arange(len(df))

#     fig, ax = plt.subplots(
#         figsize=(11.47, 5.0),
#     )

#     bar_width = 0.58

#     # Фактическая часть.
#     fact_bars = ax.bar(
#         x,
#         fact,
#         width=bar_width,
#         label="Факт",
#         color=COLOR_FACT,
#         alpha=0.88,
#         edgecolor="none",
#         zorder=3,
#     )

#     # Прогнозная часть поверх факта.
#     forecast_bars = ax.bar(
#         x,
#         forecast,
#         width=bar_width,
#         bottom=fact,
#         label="Прогноз Prophet",
#         color=COLOR_FORECAST,
#         alpha=0.82,
#         edgecolor="none",
#         zorder=3,
#     )

#     # План отдельной линией — так сравнение читается быстрее.
#     ax.plot(
#         x,
#         plan,
#         label="План WB",
#         color=COLOR_PLAN,
#         linewidth=2.2,
#         linestyle=(0, (5, 3)),
#         marker="o",
#         markersize=5,
#         markerfacecolor=COLOR_WHITE,
#         markeredgecolor=COLOR_PLAN,
#         markeredgewidth=1.5,
#         zorder=5,
#     )

#     max_value = max(
#         float(plan.max() or 0),
#         float(expected.max() or 0),
#         1.0,
#     )

#     label_offset = max_value * 0.025

#     # Подписываем ожидаемый итог каждого месяца.
#     for index, value in enumerate(expected):
#         ax.text(
#             x[index],
#             value + label_offset,
#             _format_value_mln(value),
#             ha="center",
#             va="bottom",
#             fontsize=8,
#             fontweight=700,
#             color=COLOR_TEXT,
#             zorder=6,
#         )

#     # Для текущих и будущих месяцев показываем выполнение плана.
#     for index, row in df.iterrows():
#         if float(row["forecast"] or 0) <= 0:
#             continue

#         expected_value = expected.iloc[index]
#         execution = float(
#             row["plan_exec_pct"] or 0
#         )

#         color = (
#             COLOR_POSITIVE
#             if execution >= 100
#             else COLOR_NEGATIVE
#         )

#         ax.text(
#             x[index],
#             expected_value / 2,
#             f"{execution:.1f}%",
#             ha="center",
#             va="center",
#             fontsize=7.5,
#             fontweight=700,
#             color=COLOR_WHITE,
#             bbox={
#                 "boxstyle": "round,pad=0.22",
#                 "facecolor": color,
#                 "edgecolor": "none",
#                 "alpha": 0.92,
#             },
#             zorder=7,
#         )

#     ax.set_xticks(x)
#     ax.set_xticklabels(
#         df["month_label"],
#         fontsize=9,
#     )

#     ax.set_ylabel("Выручка, млн ₽")
#     ax.yaxis.set_major_formatter(
#         FuncFormatter(_millions_formatter)
#     )

#     ax.set_title(
#         "План WB и ожидаемый результат по месяцам",
#         loc="left",
#         pad=16,
#     )

#     ax.text(
#         0,
#         1.015,
#         (
#             "Столбец = факт + прогнозная часть; "
#             "линия = утверждённый план WB"
#         ),
#         transform=ax.transAxes,
#         fontsize=8,
#         color=COLOR_MUTED,
#         va="bottom",
#     )

#     ax.set_ylim(
#         0,
#         max_value * 1.18,
#     )

#     ax.grid(
#         axis="y",
#         color=COLOR_GRID,
#         linewidth=0.8,
#         alpha=0.85,
#         zorder=0,
#     )

#     ax.grid(
#         axis="x",
#         visible=False,
#     )

#     for spine in (
#         "top",
#         "right",
#         "left",
#     ):
#         ax.spines[spine].set_visible(False)

#     ax.spines["bottom"].set_color(
#         COLOR_GRID
#     )

#     ax.tick_params(
#         axis="y",
#         length=0,
#     )

#     ax.tick_params(
#         axis="x",
#         length=0,
#         pad=7,
#     )

#     handles, labels = ax.get_legend_handles_labels()

#     # Желаемый порядок легенды:
#     # факт, прогноз, план.
#     order = [
#         labels.index("Факт"),
#         labels.index("Прогноз Prophet"),
#         labels.index("План WB"),
#     ]

#     ax.legend(
#         [handles[index] for index in order],
#         [labels[index] for index in order],
#         loc="upper left",
#         bbox_to_anchor=(0, 1.0),
#         ncol=3,
#         frameon=False,
#         handlelength=2.3,
#         columnspacing=1.6,
#         borderaxespad=0,
#     )

#     fig.tight_layout()
#     return _save_figure(fig)


# # =============================================================================
# # Год и текущее полугодие
# # =============================================================================

# def build_period_comparison_chart(
#     year_period,
#     half_period,
# ) -> BytesIO:
#     """
#     Сравнение плана и ожидаемого результата:
#     - по году;
#     - по текущему полугодию.
#     """
#     labels = [
#         "Год",
#         "Текущее\nполугодие",
#     ]

#     periods = [
#         year_period,
#         half_period,
#     ]

#     plan = np.array(
#         [
#             year_period.plan,
#             half_period.plan,
#         ],
#         dtype=float,
#     ) / 1_000_000

#     expected = np.array(
#         [
#             year_period.expected,
#             half_period.expected,
#         ],
#         dtype=float,
#     ) / 1_000_000

#     execution = np.array(
#         [
#             year_period.execution_pct,
#             half_period.execution_pct,
#         ],
#         dtype=float,
#     )

#     delta = np.array(
#         [
#             year_period.delta,
#             half_period.delta,
#         ],
#         dtype=float,
#     ) / 1_000_000

#     x = np.arange(len(labels))
#     width = 0.30

#     fig, ax = plt.subplots(
#          figsize=(8.7, 4.68),
#     )

#     plan_bars = ax.bar(
#         x - width / 2,
#         plan,
#         width,
#         label="План WB",
#         color="#FED7AA",
#         edgecolor=COLOR_PLAN,
#         linewidth=1.1,
#         zorder=3,
#     )

#     expected_colors = [
#         (
#             COLOR_POSITIVE
#             if value >= 100
#             else COLOR_FORECAST
#         )
#         for value in execution
#     ]

#     expected_bars = ax.bar(
#         x + width / 2,
#         expected,
#         width,
#         label="Ожидаемый итог",
#         color=expected_colors,
#         alpha=0.88,
#         edgecolor="none",
#         zorder=3,
#     )

#     max_value = max(
#         float(plan.max() or 0),
#         float(expected.max() or 0),
#         1.0,
#     )
#     label_offset = max_value * 0.025

#     for bar, value in zip(
#         plan_bars,
#         plan,
#     ):
#         ax.text(
#             bar.get_x() + bar.get_width() / 2,
#             value + label_offset,
#             _format_value_mln(value),
#             ha="center",
#             va="bottom",
#             fontsize=8.5,
#             color=COLOR_SECONDARY,
#         )

#     for index, (
#         bar,
#         value,
#         execution_value,
#         delta_value,
#     ) in enumerate(
#         zip(
#             expected_bars,
#             expected,
#             execution,
#             delta,
#         )
#     ):
#         ax.text(
#             bar.get_x() + bar.get_width() / 2,
#             value + label_offset,
#             _format_value_mln(value),
#             ha="center",
#             va="bottom",
#             fontsize=9,
#             fontweight=700,
#             color=COLOR_TEXT,
#         )

#         status_color = (
#             COLOR_POSITIVE
#             if execution_value >= 100
#             else COLOR_NEGATIVE
#         )

#         ax.text(
#             bar.get_x() + bar.get_width() / 2,
#             value * 0.52,
#             f"{execution_value:.1f}%",
#             ha="center",
#             va="center",
#             fontsize=8,
#             fontweight=700,
#             color=COLOR_WHITE,
#             bbox={
#                 "boxstyle": "round,pad=0.25",
#                 "facecolor": status_color,
#                 "edgecolor": "none",
#                 "alpha": 0.95,
#             },
#         )

#         delta_sign = "+" if delta_value > 0 else ""

#         ax.text(
#             x[index],
#             -max_value * 0.09,
#             (
#                 f"Отклонение: "
#                 f"{delta_sign}{delta_value:,.1f} млн ₽"
#             ).replace(",", " "),
#             ha="center",
#             va="top",
#             fontsize=8,
#             color=status_color,
#             fontweight=600,
#         )

#     ax.set_xticks(x)
#     ax.set_xticklabels(
#         labels,
#         fontsize=9,
#     )

#     ax.set_ylabel("Выручка, млн ₽")
#     ax.yaxis.set_major_formatter(
#         FuncFormatter(_millions_formatter)
#     )

#     ax.set_title(
#         "План и ожидаемый результат",
#         loc="left",
#         pad=16,
#     )

#     ax.text(
#         0,
#         1.015,
#         (
#             "Значение внутри столбца — "
#             "ожидаемое выполнение плана"
#         ),
#         transform=ax.transAxes,
#         fontsize=8,
#         color=COLOR_MUTED,
#         va="bottom",
#     )

#     ax.set_ylim(
#         -max_value * 0.17,
#         max_value * 1.17,
#     )

#     ax.grid(
#         axis="y",
#         color=COLOR_GRID,
#         linewidth=0.8,
#         alpha=0.85,
#         zorder=0,
#     )

#     for spine in (
#         "top",
#         "right",
#         "left",
#     ):
#         ax.spines[spine].set_visible(False)

#     ax.spines["bottom"].set_color(
#         COLOR_GRID
#     )

#     ax.tick_params(
#         axis="both",
#         length=0,
#     )

#     ax.legend(
#         loc="upper left",
#         bbox_to_anchor=(0, 1.0),
#         ncol=2,
#         frameon=False,
#         handlelength=2.1,
#         columnspacing=1.6,
#         borderaxespad=0,
#     )

#     fig.tight_layout()
#     return _save_figure(fig)




# # gear/app/daily_sales/wb_plan_monitor/prophet_note/charts.py
# from __future__ import annotations

# from io import BytesIO
# from typing import Any

# import matplotlib.pyplot as plt
# from matplotlib import font_manager
# from matplotlib.ticker import FuncFormatter
# import numpy as np
# import pandas as pd

# from .formatting import MONTHS_SHORT_RU


# # =============================================================================
# # Палитра графиков
# # =============================================================================

# COLOR_FACT = "#2563EB"
# COLOR_FORECAST = "#0F766E"
# COLOR_PLAN = "#D97706"

# COLOR_POSITIVE = "#15803D"
# COLOR_NEGATIVE = "#C81E1E"

# COLOR_TEXT = "#0F172A"
# COLOR_SECONDARY = "#475569"
# COLOR_MUTED = "#64748B"
# COLOR_GRID = "#E2E8F0"
# COLOR_WHITE = "#FFFFFF"


# def _configure_matplotlib() -> None:
#     """
#     Единые настройки графиков PDF.

#     DejaVu Sans содержит кириллицу и знак рубля.
#     """
#     regular_path = font_manager.findfont(
#         font_manager.FontProperties(
#             family="DejaVu Sans",
#             weight="normal",
#         )
#     )
#     bold_path = font_manager.findfont(
#         font_manager.FontProperties(
#             family="DejaVu Sans",
#             weight="bold",
#         )
#     )

#     font_manager.fontManager.addfont(regular_path)
#     font_manager.fontManager.addfont(bold_path)

#     plt.rcParams.update(
#         {
#             "font.family": "DejaVu Sans",
#             "font.size": 9,
#             "axes.titlesize": 12,
#             "axes.titleweight": 700,
#             "axes.labelsize": 9,
#             "axes.labelcolor": COLOR_SECONDARY,
#             "axes.edgecolor": COLOR_GRID,
#             "axes.facecolor": COLOR_WHITE,
#             "figure.facecolor": COLOR_WHITE,
#             "xtick.color": COLOR_SECONDARY,
#             "ytick.color": COLOR_SECONDARY,
#             "text.color": COLOR_TEXT,
#             "legend.fontsize": 8.5,
#         }
#     )


# _configure_matplotlib()


# def _millions_formatter(value, position) -> str:
#     return (
#         f"{value:,.0f}"
#         .replace(",", " ")
#     )


# def _format_value_mln(value: float) -> str:
#     return (
#         f"{float(value or 0):,.0f}"
#         .replace(",", " ")
#     )


# def _save_figure(
#     fig,
#     *,
#     dpi: int = 300,
# ) -> BytesIO:
#     """
#     Сохраняет график в высоком разрешении.

#     300 DPI достаточно для:
#     - просмотра PDF с увеличением;
#     - качественной печати;
#     - вставки графика на страницу A4.
#     """
#     output = BytesIO()

#     fig.savefig(
#         output,
#         format="png",
#         dpi=dpi,
#         bbox_inches="tight",
#         pad_inches=0.08,
#         facecolor=COLOR_WHITE,
#         edgecolor="none",
#         transparent=False,
#     )

#     plt.close(fig)
#     output.seek(0)

#     return output


# # =============================================================================
# # План / факт / прогноз по месяцам
# # =============================================================================

# def build_monthly_plan_chart(
#     monthly_rows: list[dict[str, Any]],
# ) -> BytesIO:
#     """
#     Профессиональный помесячный график.

#     Логика:
#     - факт и прогноз показываются накопленным столбиком;
#     - сумма двух частей равна ожидаемому итогу месяца;
#     - план WB показывается отдельной линией;
#     - линия факта не падает в ноль на будущих месяцах.
#     """
#     df = pd.DataFrame(monthly_rows).copy()

#     if df.empty:
#         raise ValueError(
#             "Нет помесячных данных для графика."
#         )

#     required_columns = [
#         "month",
#         "plan",
#         "fact",
#         "forecast",
#         "expected_total",
#         "delta_to_plan",
#         "plan_exec_pct",
#     ]

#     for column in required_columns:
#         if column not in df.columns:
#             df[column] = 0.0

#     df["month_date"] = pd.to_datetime(
#         df["month"].astype(str) + "-01",
#         errors="coerce",
#     )

#     df = (
#         df.dropna(subset=["month_date"])
#         .sort_values("month_date")
#         .reset_index(drop=True)
#     )

#     df["month_label"] = (
#         df["month_date"]
#         .dt.month
#         .map(MONTHS_SHORT_RU)
#     )

#     for column in (
#         "plan",
#         "fact",
#         "forecast",
#         "expected_total",
#         "delta_to_plan",
#         "plan_exec_pct",
#     ):
#         df[column] = pd.to_numeric(
#             df[column],
#             errors="coerce",
#         ).fillna(0.0)

#     # Все значения графика отображаем в млн ₽.
#     plan = df["plan"] / 1_000_000
#     fact = df["fact"] / 1_000_000
#     forecast = df["forecast"] / 1_000_000
#     expected = df["expected_total"] / 1_000_000

#     x = np.arange(len(df))

#     fig, ax = plt.subplots(
#         figsize=(11.47, 5.0),
#     )

#     bar_width = 0.58

#     # Фактическая часть.
#     fact_bars = ax.bar(
#         x,
#         fact,
#         width=bar_width,
#         label="Факт",
#         color=COLOR_FACT,
#         alpha=0.88,
#         edgecolor="none",
#         zorder=3,
#     )

#     # Прогнозная часть поверх факта.
#     forecast_bars = ax.bar(
#         x,
#         forecast,
#         width=bar_width,
#         bottom=fact,
#         label="Прогноз Prophet",
#         color=COLOR_FORECAST,
#         alpha=0.82,
#         edgecolor="none",
#         zorder=3,
#     )

#     # План отдельной линией — так сравнение читается быстрее.
#     ax.plot(
#         x,
#         plan,
#         label="План WB",
#         color=COLOR_PLAN,
#         linewidth=2.2,
#         linestyle=(0, (5, 3)),
#         marker="o",
#         markersize=5,
#         markerfacecolor=COLOR_WHITE,
#         markeredgecolor=COLOR_PLAN,
#         markeredgewidth=1.5,
#         zorder=5,
#     )

#     max_value = max(
#         float(plan.max() or 0),
#         float(expected.max() or 0),
#         1.0,
#     )

#     label_offset = max_value * 0.025

#     # Подписываем ожидаемый итог каждого месяца.
#     for index, value in enumerate(expected):
#         ax.text(
#             x[index],
#             value + label_offset,
#             _format_value_mln(value),
#             ha="center",
#             va="bottom",
#             fontsize=8,
#             fontweight=700,
#             color=COLOR_TEXT,
#             zorder=6,
#         )

#     # Для текущих и будущих месяцев показываем выполнение плана.
#     for index, row in df.iterrows():
#         if float(row["forecast"] or 0) <= 0:
#             continue

#         expected_value = expected.iloc[index]
#         execution = float(
#             row["plan_exec_pct"] or 0
#         )

#         color = (
#             COLOR_POSITIVE
#             if execution >= 100
#             else COLOR_NEGATIVE
#         )

#         ax.text(
#             x[index],
#             expected_value / 2,
#             f"{execution:.1f}%",
#             ha="center",
#             va="center",
#             fontsize=7.5,
#             fontweight=700,
#             color=COLOR_WHITE,
#             bbox={
#                 "boxstyle": "square,pad=0.22",
#                 "facecolor": color,
#                 "edgecolor": "none",
#                 "alpha": 0.92,
#             },
#             zorder=7,
#         )

#     ax.set_xticks(x)
#     ax.set_xticklabels(
#         df["month_label"],
#         fontsize=9,
#     )

#     ax.set_ylabel("Выручка, млн ₽")
#     ax.yaxis.set_major_formatter(
#         FuncFormatter(_millions_formatter)
#     )

#     ax.set_title(
#         "План WB и ожидаемый результат по месяцам",
#         loc="left",
#         pad=16,
#     )

#     ax.text(
#         0,
#         1.015,
#         (
#             "Столбец = факт + прогнозная часть; "
#             "линия = утверждённый план WB"
#         ),
#         transform=ax.transAxes,
#         fontsize=8,
#         color=COLOR_MUTED,
#         va="bottom",
#     )

#     ax.set_ylim(
#         0,
#         max_value * 1.18,
#     )

#     ax.grid(
#         axis="y",
#         color=COLOR_GRID,
#         linewidth=0.8,
#         alpha=0.85,
#         zorder=0,
#     )

#     ax.grid(
#         axis="x",
#         visible=False,
#     )

#     for spine in (
#         "top",
#         "right",
#         "left",
#     ):
#         ax.spines[spine].set_visible(False)

#     ax.spines["bottom"].set_color(
#         COLOR_GRID
#     )

#     ax.tick_params(
#         axis="y",
#         length=0,
#     )

#     ax.tick_params(
#         axis="x",
#         length=0,
#         pad=7,
#     )

#     handles, labels = ax.get_legend_handles_labels()

#     # Желаемый порядок легенды:
#     # факт, прогноз, план.
#     order = [
#         labels.index("Факт"),
#         labels.index("Прогноз Prophet"),
#         labels.index("План WB"),
#     ]

#     ax.legend(
#         [handles[index] for index in order],
#         [labels[index] for index in order],
#         loc="upper left",
#         bbox_to_anchor=(0, 1.0),
#         ncol=3,
#         frameon=False,
#         handlelength=2.3,
#         columnspacing=1.6,
#         borderaxespad=0,
#     )

#     fig.tight_layout()
#     return _save_figure(fig)


# # =============================================================================
# # Год и текущее полугодие
# # =============================================================================

# def build_period_comparison_chart(
#     year_period,
#     half_period,
# ) -> BytesIO:
#     """
#     Сравнение плана и ожидаемого результата:
#     - по году;
#     - по текущему полугодию.
#     """
#     labels = [
#         "Год",
#         "Текущее\nполугодие",
#     ]

#     periods = [
#         year_period,
#         half_period,
#     ]

#     plan = np.array(
#         [
#             year_period.plan,
#             half_period.plan,
#         ],
#         dtype=float,
#     ) / 1_000_000

#     expected = np.array(
#         [
#             year_period.expected,
#             half_period.expected,
#         ],
#         dtype=float,
#     ) / 1_000_000

#     execution = np.array(
#         [
#             year_period.execution_pct,
#             half_period.execution_pct,
#         ],
#         dtype=float,
#     )

#     delta = np.array(
#         [
#             year_period.delta,
#             half_period.delta,
#         ],
#         dtype=float,
#     ) / 1_000_000

#     x = np.arange(len(labels))
#     width = 0.30

#     fig, ax = plt.subplots(
#          figsize=(8.7, 4.68),
#     )

#     plan_bars = ax.bar(
#         x - width / 2,
#         plan,
#         width,
#         label="План WB",
#         color="#FED7AA",
#         edgecolor=COLOR_PLAN,
#         linewidth=1.1,
#         zorder=3,
#     )

#     expected_colors = [
#         (
#             COLOR_POSITIVE
#             if value >= 100
#             else COLOR_FORECAST
#         )
#         for value in execution
#     ]

#     expected_bars = ax.bar(
#         x + width / 2,
#         expected,
#         width,
#         label="Ожидаемый итог",
#         color=expected_colors,
#         alpha=0.88,
#         edgecolor="none",
#         zorder=3,
#     )

#     max_value = max(
#         float(plan.max() or 0),
#         float(expected.max() or 0),
#         1.0,
#     )
#     label_offset = max_value * 0.025

#     for bar, value in zip(
#         plan_bars,
#         plan,
#     ):
#         ax.text(
#             bar.get_x() + bar.get_width() / 2,
#             value + label_offset,
#             _format_value_mln(value),
#             ha="center",
#             va="bottom",
#             fontsize=8.5,
#             color=COLOR_SECONDARY,
#         )

#     for index, (
#         bar,
#         value,
#         execution_value,
#         delta_value,
#     ) in enumerate(
#         zip(
#             expected_bars,
#             expected,
#             execution,
#             delta,
#         )
#     ):
#         ax.text(
#             bar.get_x() + bar.get_width() / 2,
#             value + label_offset,
#             _format_value_mln(value),
#             ha="center",
#             va="bottom",
#             fontsize=9,
#             fontweight=700,
#             color=COLOR_TEXT,
#         )

#         status_color = (
#             COLOR_POSITIVE
#             if execution_value >= 100
#             else COLOR_NEGATIVE
#         )

#         ax.text(
#             bar.get_x() + bar.get_width() / 2,
#             value * 0.52,
#             f"{execution_value:.1f}%",
#             ha="center",
#             va="center",
#             fontsize=8,
#             fontweight=700,
#             color=COLOR_WHITE,
#             bbox={
#                 "boxstyle": "square,pad=0.25",
#                 "facecolor": status_color,
#                 "edgecolor": "none",
#                 "alpha": 0.95,
#             },
#         )

#         delta_sign = "+" if delta_value > 0 else ""

#         ax.text(
#             x[index],
#             -max_value * 0.09,
#             (
#                 f"Отклонение: "
#                 f"{delta_sign}{delta_value:,.1f} млн ₽"
#             ).replace(",", " "),
#             ha="center",
#             va="top",
#             fontsize=8,
#             color=status_color,
#             fontweight=600,
#         )

#     ax.set_xticks(x)
#     ax.set_xticklabels(
#         labels,
#         fontsize=9,
#     )

#     ax.set_ylabel("Выручка, млн ₽")
#     ax.yaxis.set_major_formatter(
#         FuncFormatter(_millions_formatter)
#     )

#     ax.set_title(
#         "План и ожидаемый результат",
#         loc="left",
#         pad=16,
#     )

#     ax.text(
#         0,
#         1.015,
#         (
#             "Значение внутри столбца — "
#             "ожидаемое выполнение плана"
#         ),
#         transform=ax.transAxes,
#         fontsize=8,
#         color=COLOR_MUTED,
#         va="bottom",
#     )

#     ax.set_ylim(
#         -max_value * 0.17,
#         max_value * 1.17,
#     )

#     ax.grid(
#         axis="y",
#         color=COLOR_GRID,
#         linewidth=0.8,
#         alpha=0.85,
#         zorder=0,
#     )

#     for spine in (
#         "top",
#         "right",
#         "left",
#     ):
#         ax.spines[spine].set_visible(False)

#     ax.spines["bottom"].set_color(
#         COLOR_GRID
#     )

#     ax.tick_params(
#         axis="both",
#         length=0,
#     )

#     ax.legend(
#         loc="upper left",
#         bbox_to_anchor=(0, 1.0),
#         ncol=2,
#         frameon=False,
#         handlelength=2.1,
#         columnspacing=1.6,
#         borderaxespad=0,
#     )

#     fig.tight_layout()
#     return _save_figure(fig)



from __future__ import annotations

from io import BytesIO
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from .formatting import MONTHS_SHORT_RU

# =============================================================================
# Единая палитра графиков
# =============================================================================
COLOR_ACTUAL = "#233B5D"
COLOR_FORECAST = "#167C80"
COLOR_PLAN = "#7B8796"
COLOR_RISK = "#B42318"
COLOR_SUCCESS = "#18794E"
COLOR_TEXT = "#142033"
COLOR_SECONDARY = "#4B586A"
COLOR_MUTED = "#7A8696"
COLOR_GRID = "#E7EBF0"
COLOR_TRACK = "#E9EDF2"
COLOR_WHITE = "#FFFFFF"


def _configure_matplotlib() -> None:
    regular_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="normal")
    )
    bold_path = font_manager.findfont(
        font_manager.FontProperties(family="DejaVu Sans", weight="bold")
    )
    font_manager.fontManager.addfont(regular_path)
    font_manager.fontManager.addfont(bold_path)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 11,
            "axes.titleweight": 700,
            "axes.labelsize": 8.3,
            "axes.labelcolor": COLOR_SECONDARY,
            "axes.edgecolor": COLOR_GRID,
            "axes.facecolor": COLOR_WHITE,
            "figure.facecolor": COLOR_WHITE,
            "xtick.color": COLOR_SECONDARY,
            "ytick.color": COLOR_SECONDARY,
            "text.color": COLOR_TEXT,
            "legend.fontsize": 8,
        }
    )


_configure_matplotlib()


def _millions_formatter(value, position) -> str:
    return f"{value:,.0f}".replace(",", " ")


def _format_value_mln(value: float, digits: int = 0) -> str:
    return f"{float(value or 0):,.{digits}f}".replace(",", " ").replace(".", ",")


def _save_figure(fig, *, dpi: int = 300) -> BytesIO:
    output = BytesIO()
    fig.savefig(
        output,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.06,
        facecolor=COLOR_WHITE,
        edgecolor="none",
        transparent=False,
    )
    plt.close(fig)
    output.seek(0)
    return output


def build_monthly_plan_chart(monthly_rows: list[dict[str, Any]]) -> BytesIO:
    """
    Спокойный управленческий график:
    - факт — тёмно-синий;
    - прогноз — бирюзовый;
    - план — нейтральная пунктирная линия;
    - без красных плашек внутри столбцов;
    - риск отмечается только цветом небольшого процента под осью.
    """
    df = pd.DataFrame(monthly_rows).copy()
    if df.empty:
        raise ValueError("Нет помесячных данных для графика.")

    required = [
        "month", "plan", "fact", "forecast",
        "expected_total", "delta_to_plan", "plan_exec_pct",
    ]
    for column in required:
        if column not in df.columns:
            df[column] = 0.0

    df["month_date"] = pd.to_datetime(
        df["month"].astype(str) + "-01",
        errors="coerce",
    )
    df = (
        df.dropna(subset=["month_date"])
        .sort_values("month_date")
        .reset_index(drop=True)
    )
    df["month_label"] = df["month_date"].dt.month.map(MONTHS_SHORT_RU)

    numeric_columns = [
        "plan", "fact", "forecast",
        "expected_total", "delta_to_plan", "plan_exec_pct",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    plan = df["plan"] / 1_000_000
    fact = df["fact"] / 1_000_000
    forecast = df["forecast"] / 1_000_000
    expected = df["expected_total"] / 1_000_000
    x = np.arange(len(df))

    fig, ax = plt.subplots(figsize=(11.45, 4.85))
    width = 0.54

    ax.bar(
        x, fact, width=width,
        label="Факт", color=COLOR_ACTUAL,
        edgecolor="none", zorder=3,
    )
    ax.bar(
        x, forecast, width=width, bottom=fact,
        label="Прогноз", color=COLOR_FORECAST,
        edgecolor="none", zorder=3,
    )
    ax.plot(
        x, plan,
        label="План WB",
        color=COLOR_PLAN,
        linewidth=1.7,
        linestyle=(0, (4, 3)),
        marker="o",
        markersize=3.8,
        markerfacecolor=COLOR_WHITE,
        markeredgecolor=COLOR_PLAN,
        markeredgewidth=1.1,
        zorder=5,
    )

    max_value = max(float(plan.max() or 0), float(expected.max() or 0), 1.0)
    label_offset = max_value * 0.022

    for index, value in enumerate(expected):
        ax.text(
            x[index], value + label_offset,
            _format_value_mln(value),
            ha="center", va="bottom",
            fontsize=7.6, fontweight=700,
            color=COLOR_TEXT, zorder=6,
        )

    # Процент выполнения показываем только для месяцев с прогнозной частью.
    # Значение размещается под подписью месяца, без цветных прямоугольников.
    for index, row in df.iterrows():
        if float(row["forecast"] or 0) <= 0:
            continue
        execution = float(row["plan_exec_pct"] or 0)
        status_color = COLOR_SUCCESS if execution >= 100 else COLOR_RISK
        ax.text(
            x[index], -max_value * 0.075,
            f"{execution:.1f}%",
            ha="center", va="top",
            fontsize=7.0, fontweight=700,
            color=status_color,
        )

    ax.set_title("План и ожидаемый результат по месяцам", loc="left", pad=13)
    ax.text(
        0, 1.01,
        "Столбец = факт + прогноз; пунктир = утверждённый план WB",
        transform=ax.transAxes,
        fontsize=7.5, color=COLOR_MUTED, va="bottom",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(df["month_label"], fontsize=8.2)
    ax.set_ylabel("Выручка, млн ₽")
    ax.yaxis.set_major_formatter(FuncFormatter(_millions_formatter))
    ax.set_ylim(-max_value * 0.13, max_value * 1.16)

    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.7, zorder=0)
    ax.grid(axis="x", visible=False)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.tick_params(axis="both", length=0)
    ax.tick_params(axis="x", pad=7)

    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index("Факт"), labels.index("Прогноз"), labels.index("План WB")]
    ax.legend(
        [handles[i] for i in order],
        [labels[i] for i in order],
        loc="upper left",
        bbox_to_anchor=(0, 0.995),
        ncol=3,
        frameon=False,
        handlelength=2.1,
        columnspacing=1.5,
        borderaxespad=0,
    )

    fig.tight_layout()
    return _save_figure(fig)


def build_period_comparison_chart(
    year_period,
    half_period,
) -> BytesIO:
    """
    Компактный bullet-chart для сравнения ожидаемого выполнения плана
    по году и текущему полугодию.

    Логика:
    - светло-серая шкала соответствует 100% плана;
    - бирюзовая полоса показывает ожидаемое выполнение;
    - внутри полосы отображаются процент и ожидаемая сумма;
    - справа от отметки 100% выводится плановая сумма.
    """

    periods = [
        year_period,
        half_period,
    ]

    labels = [
        year_period.label,
        half_period.label,
    ]

    execution = np.array(
        [
            float(period.execution_pct or 0)
            for period in periods
        ],
        dtype=float,
    )

    plan = np.array(
        [
            float(period.plan or 0)
            for period in periods
        ],
        dtype=float,
    ) / 1_000_000

    expected = np.array(
        [
            float(period.expected or 0)
            for period in periods
        ],
        dtype=float,
    ) / 1_000_000

    y = np.arange(len(periods))

    # Справа оставляем отдельную область для подписей плана.
    chart_limit = 124

    fig, ax = plt.subplots(
        figsize=(10.8, 3.45),
    )

    # ================================================================
    # Фоновая шкала: план = 100%
    # ================================================================

    ax.barh(
        y=y,
        width=np.full(len(periods), 100.0),
        height=0.38,
        color=COLOR_TRACK,
        edgecolor="none",
        zorder=1,
    )

    # ================================================================
    # Ожидаемое выполнение
    # ================================================================

    bars = ax.barh(
        y=y,
        width=execution,
        height=0.38,
        color=COLOR_FORECAST,
        alpha=0.96,
        edgecolor="none",
        zorder=3,
    )

    # Вертикальная отметка плана.
    ax.axvline(
        x=100,
        color=COLOR_PLAN,
        linewidth=1.25,
        linestyle=(0, (4, 4)),
        zorder=4,
    )

    # ================================================================
    # Подписи
    # ================================================================

    for index, (
        bar,
        execution_value,
        expected_value,
        plan_value,
    ) in enumerate(
        zip(
            bars,
            execution,
            expected,
            plan,
        )
    ):
        bar_center_y = (
            bar.get_y()
            + bar.get_height() / 2
        )

        # Подписи размещаем внутри цветной полосы справа.
        text_x = max(
            min(execution_value - 2.0, 96.5),
            22.0,
        )

        ax.text(
            text_x,
            bar_center_y + 0.045,
            f"{execution_value:.1f}%".replace(".", ","),
            ha="right",
            va="center",
            fontsize=11,
            fontweight=700,
            color=COLOR_WHITE,
            zorder=6,
        )

        ax.text(
            text_x,
            bar_center_y - 0.075,
            (
                f"Ожидается "
                f"{expected_value:,.1f} млн ₽"
            ).replace(",", " ").replace(".", ","),
            ha="right",
            va="center",
            fontsize=7.8,
            color=COLOR_WHITE,
            zorder=6,
        )

        # Плановая сумма выводится справа от шкалы 100%.
        ax.text(
            102.2,
            bar_center_y,
            (
                f"План "
                f"{plan_value:,.1f} млн ₽"
            ).replace(",", " ").replace(".", ","),
            ha="left",
            va="center",
            fontsize=8.2,
            color=COLOR_SECONDARY,
            zorder=6,
        )

    # ================================================================
    # Оси и подписи
    # ================================================================

    ax.set_yticks(y)

    ax.set_yticklabels(
        labels,
        fontsize=9.2,
        fontweight=700,
        color=COLOR_TEXT,
    )

    ax.invert_yaxis()

    ax.set_xlim(
        0,
        chart_limit,
    )

    ax.set_xticks(
        [
            0,
            20,
            40,
            60,
            80,
            100,
        ]
    )

    ax.xaxis.set_major_formatter(
        FuncFormatter(
            lambda value, position: (
                f"{value:.0f}%"
            )
        )
    )

    ax.set_xlabel(
        "Выполнение плана, %",
        fontsize=8.5,
        color=COLOR_SECONDARY,
        labelpad=8,
    )

    ax.set_title(
        "Ожидаемое выполнение плана",
        loc="left",
        fontsize=12,
        fontweight=700,
        color=COLOR_TEXT,
        pad=23,
    )

    ax.text(
        0,
        1.035,
        (
            "Светло-серая шкала соответствует "
            "100% утверждённого плана"
        ),
        transform=ax.transAxes,
        fontsize=7.5,
        color=COLOR_MUTED,
        va="bottom",
    )

    # ================================================================
    # Сетка и оформление
    # ================================================================

    ax.grid(
        axis="x",
        color=COLOR_GRID,
        linewidth=0.7,
        alpha=0.85,
        zorder=0,
    )

    ax.grid(
        axis="y",
        visible=False,
    )

    for spine in (
        "top",
        "right",
        "left",
    ):
        ax.spines[spine].set_visible(False)

    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_linewidth(0.8)

    ax.tick_params(
        axis="x",
        length=0,
        labelsize=8,
        colors=COLOR_SECONDARY,
        pad=6,
    )

    ax.tick_params(
        axis="y",
        length=0,
        pad=10,
    )

    # Не используем tight_layout:
    # он слишком сильно сжимает подписи при вставке изображения в PDF.
    fig.subplots_adjust(
        left=0.205,
        right=0.975,
        top=0.78,
        bottom=0.22,
    )

    return _save_figure(
        fig,
        dpi=400,
    )