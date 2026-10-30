# gear/app/stats/callbacks.py
from __future__ import annotations

from datetime import datetime
from time import time

import pandas as pd
import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    html,
)

from .calculations import (
    aggregate_data,
    build_insights,
    build_month_analysis,
    build_weekday_analysis,
    calculate_correlation_matrix,
    calculate_kpis,
    calculate_lag_correlations,
    calculate_price_elasticity,
    calculate_rolling_correlation,
    detect_anomalies,
)
from .charts import (
    build_anomaly_chart,
    build_correlation_matrix,
    build_lag_chart,
    build_marketing_scatter,
    build_month_chart,
    build_price_elasticity_chart,
    build_price_scatter,
    build_roas_chart,
    build_rolling_corr_chart,
    build_trend_chart,
    build_weekday_chart,
    empty_figure,
)

from .insights import (
    build_correlation_matrix_insight,
    build_marketing_scatter_insight,
    build_lag_insight,
    build_roas_insight,
    build_rolling_corr_insight,
    build_price_scatter_insight,
    build_price_elasticity_insight,
    build_weekday_insight,
    build_month_insight,
    build_anomaly_insight,
)

from .config import (
    COLORS,
    DEFAULT_AGGREGATION,
)
from .data import (
    get_stats_data,
)
from .ids import (
    AGGREGATION_FILTER_ID,
    ANOMALY_CHART_ID,
    CORRELATION_MATRIX_ID,
    DATE_FILTER_ID,
    INSIGHTS_CONTAINER_ID,
    KPI_BEST_LAG_ID,
    KPI_BEST_WEEKDAY_ID,
    KPI_CORRELATION_ID,
    KPI_MARKETING_ID,
    KPI_MARKETING_SHARE_ID,
    KPI_PRICE_CORRELATION_ID,
    KPI_REVENUE_ID,
    KPI_ROAS_ID,
    LAG_CHART_ID,
    LAG_INSIGHT_ID,
    LAST_UPDATE_ID,
    LOADING_TRIGGER_ID,
    MARKETING_SCATTER_ID,
    MARKETING_SCATTER_INSIGHT_ID,
    MONTH_CHART_ID,
    PRICE_ELASTICITY_CHART_ID,
    PRICE_SCATTER_ID,
    REFRESH_BTN_ID,
    ROAS_CHART_ID,
    ROLLING_CORR_CHART_ID,
    ROLLING_CORR_INSIGHT_ID,
    TREND_CHART_ID,
    WEEKDAY_CHART_ID,
    CORRELATION_MATRIX_INSIGHT_ID,
    ROAS_INSIGHT_ID,
    PRICE_SCATTER_INSIGHT_ID,
    PRICE_ELASTICITY_INSIGHT_ID,
    WEEKDAY_INSIGHT_ID,
    MONTH_INSIGHT_ID,
    ANOMALY_INSIGHT_ID,
    
)

from .profit_optimizer import (
    register_profit_optimizer_callbacks,
)


def _format_money(
    value,
):
    if value is None:
        return "—"

    try:
        if pd.isna(value):
            return "—"
    except TypeError:
        pass

    value = float(value)

    absolute = abs(
        value
    )

    if absolute >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.2f}"
            " млрд ₽"
        )

    if absolute >= 1_000_000:
        return (
            f"{value / 1_000_000:.2f}"
            " млн ₽"
        )

    return (
        f"{value:,.0f}"
        .replace(
            ",",
            " ",
        )
        + " ₽"
    )


def _format_percent(
    value,
):
    if value is None:
        return "—"

    try:
        if pd.isna(value):
            return "—"
    except TypeError:
        pass

    return (
        f"{float(value):.2f}%"
    )


def _format_number(
    value,
):
    if value is None:
        return "—"

    try:
        if pd.isna(value):
            return "—"
    except TypeError:
        pass

    return (
        f"{float(value):.2f}"
    )


def _format_correlation(
    value,
):
    if value is None:
        return "—"

    try:
        if pd.isna(value):
            return "—"
    except TypeError:
        pass

    return (
        f"{float(value):+.2f}"
    )


def _format_best_lag(
    lag,
    corr,
    aggregation,
):
    if lag is None:
        return "—"

    units = {
        "day": (
            "дн."
        ),
        "week": (
            "нед."
        ),
        "month": (
            "мес."
        ),
    }

    unit = units.get(
        aggregation,
        "пер.",
    )

    if corr is None:
        return (
            f"{lag} {unit}"
        )

    try:
        if pd.isna(corr):
            return (
                f"{lag} {unit}"
            )
    except TypeError:
        pass

    return (
        f"{lag} {unit} "
        f"(r={corr:+.2f})"
    )


def _build_insights_components(
    insights,
):
    if not insights:
        return dmc.Text(
            (
                "Недостаточно данных "
                "для формирования выводов."
            ),
            size="sm",
            c=COLORS[
                "muted"
            ],
        )

    children = []

    for index, insight in enumerate(
        insights,
        start=1,
    ):
        children.append(
            html.Div(
                style={
                    "display": (
                        "flex"
                    ),
                    "gap": (
                        "10px"
                    ),
                    "padding": (
                        "10px 0"
                    ),
                    "borderBottom": (
                        f"1px solid "
                        f"{COLORS['border']}"
                    ),
                },
                children=[
                    html.Div(
                        style={
                            "width": (
                                "24px"
                            ),
                            "height": (
                                "24px"
                            ),
                            "minWidth": (
                                "24px"
                            ),
                            "display": (
                                "flex"
                            ),
                            "alignItems": (
                                "center"
                            ),
                            "justifyContent": (
                                "center"
                            ),
                            "backgroundColor": (
                                COLORS[
                                    "light_green"
                                ]
                            ),
                            "color": (
                                COLORS[
                                    "dark_green"
                                ]
                            ),
                            "fontWeight": (
                                700
                            ),
                            "fontSize": (
                                "11px"
                            ),
                        },
                        children=str(
                            index
                        ),
                    ),

                    dmc.Text(
                        insight,
                        size="sm",
                        c=COLORS[
                            "text"
                        ],
                        style={
                            "lineHeight": (
                                "21px"
                            ),
                        },
                    ),
                ],
            )
        )

    return children


def _normalise_date_range(
    value,
):
    if (
        not value
        or len(value) != 2
    ):
        return (
            None,
            None,
        )

    date_from = value[0]
    date_to = value[1]

    if date_from:
        date_from = str(
            date_from
        )[:10]

    if date_to:
        date_to = str(
            date_to
        )[:10]

    return (
        date_from,
        date_to,
    )


def _empty_response():
    empty = empty_figure(
        "Нет данных для выбранного периода"
    )

    return (
        # KPI
        "0 ₽",
        "0 ₽",
        "—",
        "—",
        "—",
        "—",
        "—",
        "—",

        # Выручка и маркетинг
        empty,

        # Scatter
        empty,

        # Вывод под scatter
        (
            "Недостаточно данных "
            "для оценки связи маркетинговых "
            "расходов и выручки."
        ),

        # Lag
        empty,
        
        # Вывод по Lag
            (
                "Недостаточно данных "
                "для анализа временного лага."
            ),

        # Rolling correlation
        empty,
        
        # Вывод по Rolling correlation
            (
                "Недостаточно данных "
                "для анализа стабильности связи "
                "маркетинга и выручки."
            ),

        # ROAS
        empty,
        
        # Вывод по ROAS
            (
                "Недостаточно данных "
                "для анализа эффективности маркетинга."
            ),

        # Цена → количество
        empty,
        
        # Вывод по цене → количеству
            (
                "Недостаточно данных "
                "для анализа связи цены "
                "и количества продаж."
            ),

        # Эластичность
        empty,
        
        # Вывод по эластичности
            (
                "Недостаточно данных "
                "для анализа реакции спроса "
                "на изменение цены."
            ),


        # Дни недели
        empty,
        
        # Вывод по дням недели
            (
                "Недостаточно данных "
                "для анализа сезонности "
                "по дням недели."
            ),
            

        # Месяцы
        empty,
        
        # Вывод по месяцам
            (
                "Недостаточно данных "
                "для анализа сезонности "
                "по месяцам."
            ),

        # Корреляционная матрица
        empty,
        
        # Вывод по корреляционной матрице
            (
                "Недостаточно данных "
                "для анализа корреляционной матрицы."
            ),

        # Аномалии
        empty,
        
        # Вывод по аномальным периодам
            (
                "За выбранный период выраженные "
                "аномальные периоды не обнаружены."
            ),

        # Общие выводы
        _build_insights_components(
            []
        ),

        # Последнее обновление
        datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        ),

        # Loading trigger
        str(
            time()
        ),
    )

def register_stats_callbacks(
    app,
):
    @app.callback(
        # -------------------------------------------------
        # KPI
        # -------------------------------------------------

        Output(
            KPI_REVENUE_ID,
            "children",
        ),
        Output(
            KPI_MARKETING_ID,
            "children",
        ),
        Output(
            KPI_MARKETING_SHARE_ID,
            "children",
        ),
        Output(
            KPI_ROAS_ID,
            "children",
        ),
        Output(
            KPI_CORRELATION_ID,
            "children",
        ),
        Output(
            KPI_BEST_LAG_ID,
            "children",
        ),
        Output(
            KPI_PRICE_CORRELATION_ID,
            "children",
        ),
        Output(
            KPI_BEST_WEEKDAY_ID,
            "children",
        ),

        # -------------------------------------------------
        # Обзор
        # -------------------------------------------------

        Output(
            TREND_CHART_ID,
            "figure",
        ),

        Output(
            MARKETING_SCATTER_ID,
            "figure",
        ),

        Output(
            MARKETING_SCATTER_INSIGHT_ID,
            "children",
        ),

        Output(
            LAG_CHART_ID,
            "figure",
        ),
        
        Output(
            LAG_INSIGHT_ID,
            "children",
        ),

        Output(
            ROLLING_CORR_CHART_ID,
            "figure",
        ),
        
        Output(
                ROLLING_CORR_INSIGHT_ID,
                "children",
            ),

        Output(
            ROAS_CHART_ID,
            "figure",
        ),
        
        Output(
                ROAS_INSIGHT_ID,
                "children",
            ),


        Output(
            PRICE_SCATTER_ID,
            "figure",
        ),
        Output(
            PRICE_SCATTER_INSIGHT_ID,
            "children",
        ),

        Output(
            PRICE_ELASTICITY_CHART_ID,
            "figure",
        ),
        Output(
            PRICE_ELASTICITY_INSIGHT_ID,
            "children",
        ),

        Output(
            WEEKDAY_CHART_ID,
            "figure",
        ),
        
        Output(
            WEEKDAY_INSIGHT_ID,
            "children",
        ),

        Output(
            MONTH_CHART_ID,
            "figure",
        ),
        
        Output(
            MONTH_INSIGHT_ID,
            "children",
        ),

        Output(
            CORRELATION_MATRIX_ID,
            "figure",
        ),
        
        Output(
            CORRELATION_MATRIX_INSIGHT_ID,
            "children",
        ),

        Output(
            ANOMALY_CHART_ID,
            "figure",
        ),
        
        Output(
                ANOMALY_INSIGHT_ID,
                "children",
            ),

        # -------------------------------------------------
        # Общие выводы
        # -------------------------------------------------

        Output(
            INSIGHTS_CONTAINER_ID,
            "children",
        ),

        # -------------------------------------------------
        # Служебные
        # -------------------------------------------------

        Output(
            LAST_UPDATE_ID,
            "children",
        ),

        Output(
            LOADING_TRIGGER_ID,
            "children",
        ),

        # -------------------------------------------------
        # Inputs
        # -------------------------------------------------

        Input(
            DATE_FILTER_ID,
            "value",
        ),

        Input(
            AGGREGATION_FILTER_ID,
            "value",
        ),

        Input(
            REFRESH_BTN_ID,
            "n_clicks",
        ),
    )
    def update_dashboard(
        date_range,
        aggregation,
        _refresh_clicks,
    ):
        # -------------------------------------------------
        # Параметры
        # -------------------------------------------------

        aggregation = (
            aggregation
            or DEFAULT_AGGREGATION
        )

        (
            date_from,
            date_to,
        ) = _normalise_date_range(
            date_range
        )

        # -------------------------------------------------
        # Исходные данные
        # -------------------------------------------------

        daily_df = get_stats_data(
            date_from=date_from,
            date_to=date_to,
        )

        if daily_df.empty:
            return _empty_response()

        # -------------------------------------------------
        # Агрегация
        # -------------------------------------------------

        aggregated_df = aggregate_data(
            daily_df,
            aggregation,
        )

        if aggregated_df.empty:
            return _empty_response()

        # -------------------------------------------------
        # KPI
        # -------------------------------------------------

        kpis = calculate_kpis(
            daily_df,
            aggregated_df,
        )

        # -------------------------------------------------
        # Lag-анализ
        # -------------------------------------------------

        lag_df = calculate_lag_correlations(
            aggregated_df
        )

        # -------------------------------------------------
        # Скользящая корреляция
        # -------------------------------------------------

        rolling_df = (
            calculate_rolling_correlation(
                aggregated_df,
                aggregation,
            )
        )

        # -------------------------------------------------
        # Эластичность
        # -------------------------------------------------

        elasticity_df = (
            calculate_price_elasticity(
                aggregated_df
            )
        )

        # -------------------------------------------------
        # Сезонность
        # -------------------------------------------------

        weekday_df = (
            build_weekday_analysis(
                daily_df
            )
        )

        month_df = (
            build_month_analysis(
                daily_df
            )
        )

        # -------------------------------------------------
        # Корреляционная матрица
        # -------------------------------------------------

        correlation_matrix = (
            calculate_correlation_matrix(
                aggregated_df,
                method="pearson",
            )
        )

        # -------------------------------------------------
        # Аномалии
        # -------------------------------------------------

        anomalies_df = (
            detect_anomalies(
                aggregated_df
            )
        )

        # -------------------------------------------------
        # Общие автоматические выводы
        # -------------------------------------------------

        insights = build_insights(
            daily_df,
            aggregated_df,
            aggregation,
        )

        # -------------------------------------------------
        # Return
        #
        # ПОРЯДОК ДОЛЖЕН ТОЧНО СОВПАДАТЬ
        # С ПОРЯДКОМ Output ВЫШЕ
        # -------------------------------------------------

        return (
            # 1. Выручка
            _format_money(
                kpis.get(
                    "revenue"
                )
            ),

            # 2. Маркетинг
            _format_money(
                kpis.get(
                    "marketing"
                )
            ),

            # 3. Доля маркетинга
            _format_percent(
                kpis.get(
                    "marketing_share"
                )
            ),

            # 4. ROAS
            _format_number(
                kpis.get(
                    "roas"
                )
            ),

            # 5. Корреляция маркетинг ↔ выручка
            _format_correlation(
                kpis.get(
                    "marketing_corr"
                )
            ),

            # 6. Лучший lag
            _format_best_lag(
                kpis.get(
                    "best_lag"
                ),
                kpis.get(
                    "best_lag_corr"
                ),
                aggregation,
            ),

            # 7. Корреляция цена ↔ количество
            _format_correlation(
                kpis.get(
                    "price_corr"
                )
            ),

            # 8. Лучший день недели
            (
                kpis.get(
                    "best_weekday"
                )
                or "—"
            ),

            # 9. Выручка + маркетинг
            build_trend_chart(
                aggregated_df
            ),

            # 10. Scatter маркетинг → выручка
            build_marketing_scatter(
                aggregated_df
            ),

            # 11. Аналитический вывод под scatter
            build_marketing_scatter_insight(
                aggregated_df
            ),

            # 12. Lag
            build_lag_chart(
                lag_df
            ),
            
            # 12.1 Аналитический вывод по Lag
            build_lag_insight(
                lag_df
            ),

            # 13. Rolling correlation
            build_rolling_corr_chart(
                rolling_df
            ),
            
            # 13.1 Аналитический вывод по Rolling correlation
                    build_rolling_corr_insight(
                        rolling_df
                    ),

            # 14. ROAS
            build_roas_chart(
                aggregated_df
            ),
            
            # 14.1 Аналитический вывод по ROAS
                    build_roas_insight(
                        aggregated_df
                    ),

            # 15. Цена → количество
            build_price_scatter(
                aggregated_df
            ),
            
            # 15.1 Аналитический вывод по цене → количеству
                build_price_scatter_insight(
                    aggregated_df
                ),

            # 16. Эластичность
            build_price_elasticity_chart(
                elasticity_df
            ),
            
            # 16.1 Аналитический вывод по эластичности
                    build_price_elasticity_insight(
                        elasticity_df
                    ),

            # 17. Сезонность по дням недели
            build_weekday_chart(
                weekday_df
            ),
            
            # 17.1 Аналитический вывод по дням недели
                    build_weekday_insight(
                        weekday_df
                    ),

            # 18. Сезонность по месяцам
            build_month_chart(
                month_df
            ),
            
            # 18.1 Аналитический вывод по месяцам
                build_month_insight(
                    month_df
                ),

            # 19. Корреляционная матрица
            build_correlation_matrix(
                correlation_matrix
            ),
            
            build_correlation_matrix_insight(
                    correlation_matrix
                ),

            # 20. Аномалии
            build_anomaly_chart(
                anomalies_df
            ),
            
            build_anomaly_insight(
                    anomalies_df
                ),
                            

            # 21. Общие выводы
            _build_insights_components(
                insights
            ),

            # 22. Последнее обновление
            datetime.now().strftime(
                "%d.%m.%Y %H:%M"
            ),

            # 23. Loading trigger
            str(
                time()
            ),
        )
        
        
        
    
    register_profit_optimizer_callbacks(app)