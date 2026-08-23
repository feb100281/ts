# gear/app/loans/charts.py
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .calculations import build_maturity_summary
from .config import COLORS, MATURITY_ORDER


def empty_figure(
    message: str = "Нет данных для построения графика",
    height: int = 400,
) -> go.Figure:
    fig = go.Figure()

    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={
            "family": "Inter, Arial, sans-serif",
            "size": 13,
            "color": COLORS["muted"],
        },
    )

    fig.update_layout(
        height=height,
        paper_bgcolor=COLORS["white"],
        plot_bgcolor=COLORS["white"],
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
        xaxis={"visible": False},
        yaxis={"visible": False},
    )

    return fig


def base_layout(
    *,
    height: int = 420,
    margin: dict | None = None,
) -> dict:
    return {
        "template": "plotly_white",
        "height": height,
        "paper_bgcolor": COLORS["white"],
        "plot_bgcolor": COLORS["white"],
        "font": {
            "family": "Inter, Arial, sans-serif",
            "size": 12,
            "color": COLORS["text"],
        },
        "margin": margin
        or {
            "l": 55,
            "r": 25,
            "t": 25,
            "b": 55,
        },
        "hoverlabel": {
            "bgcolor": COLORS["white"],
            "bordercolor": COLORS["border"],
            "font": {
                "family": "Inter, Arial, sans-serif",
                "size": 12,
                "color": COLORS["text"],
            },
        },
    }


def _money_text(
    value: float | int | None,
) -> str:
    """
    Компактное форматирование денежных значений.

    Примеры:
    195_000_000 -> 195,0 млн
    927_000     -> 927 тыс
    211         -> 211 ₽
    0           -> 0 ₽
    """

    if value is None:
        return "—"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return "—"

    absolute = abs(value)

    if absolute >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.2f}"
            .replace(".", ",")
            + " млрд"
        )

    if absolute >= 1_000_000:
        return (
            f"{value / 1_000_000:.1f}"
            .replace(".", ",")
            + " млн"
        )

    if absolute >= 1_000:
        return (
            f"{value / 1_000:.0f}"
            .replace(".", ",")
            + " тыс"
        )

    return (
        f"{value:,.0f}"
        .replace(",", " ")
        + " ₽"
    )


def build_debt_dynamics_chart(
    df: pd.DataFrame,
) -> go.Figure:

    if df.empty:
        return empty_figure()

    work = df.copy()

    # =============================================================
    # Подготовка
    # =============================================================

    work["date_from"] = pd.to_datetime(
        work["date_from"],
        errors="coerce",
    )

    for column in (
        "principal_debt",
        "interest_debt",
        "total_debt",
    ):
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        ).fillna(0)

    work = (
        work
        .dropna(
            subset=["date_from"]
        )
        .sort_values("date_from")
        .reset_index(drop=True)
    )

    if work.empty:
        return empty_figure()

    # =============================================================
    # Метрики
    # =============================================================

    first = work.iloc[0]
    last = work.iloc[-1]

    start_total = float(
        first["total_debt"]
    )

    end_total = float(
        last["total_debt"]
    )

    absolute_change = (
        end_total
        - start_total
    )

    change_pct = None

    if start_total:
        change_pct = (
            absolute_change
            / abs(start_total)
            * 100
        )

    peak_index = (
        work["total_debt"]
        .idxmax()
    )

    peak_row = work.loc[
        peak_index
    ]

    peak_value = float(
        peak_row["total_debt"]
    )

    peak_date = peak_row[
        "date_from"
    ]

    # =============================================================
    # Формат
    # =============================================================

    def compact_money(
        value: float,
    ) -> str:

        absolute = abs(value)

        if absolute >= 1_000_000_000:
            return (
                f"{value / 1_000_000_000:.2f}"
                .replace(".", ",")
                + " млрд ₽"
            )

        if absolute >= 1_000_000:
            return (
                f"{value / 1_000_000:.1f}"
                .replace(".", ",")
                + " млн ₽"
            )

        if absolute >= 1_000:
            return (
                f"{value / 1_000:.0f}"
                .replace(".", ",")
                + " тыс. ₽"
            )

        return (
            f"{value:,.0f}"
            .replace(",", " ")
            + " ₽"
        )

    # =============================================================
    # Figure
    # =============================================================

    fig = go.Figure()

    # -------------------------------------------------------------
    # Основной долг
    # -------------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=work["date_from"],
            y=work["principal_debt"],

            name="Основной долг",

            mode="lines",

            line={
                "color": COLORS["green"],
                "width": 2.6,
            },

            fill="tozeroy",

            fillcolor=(
                "rgba(60,122,103,0.07)"
            ),

            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br>"
                "Основной долг: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # -------------------------------------------------------------
    # Проценты
    # -------------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=work["date_from"],
            y=work["interest_debt"],

            name="Проценты",

            mode="lines",

            yaxis="y2",

            line={
                "color": COLORS["orange"],
                "width": 2.0,
                "dash": "dot",
            },

            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br>"
                "Проценты: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Максимум — только точка
    # =============================================================

    fig.add_trace(
        go.Scatter(
            x=[peak_date],
            y=[peak_value],

            mode="markers",

            marker={
                "size": 7,
                "color": COLORS["red"],
                "line": {
                    "color": "#FFFFFF",
                    "width": 1.5,
                },
            },

            showlegend=False,

            hovertemplate=(
                "<b>Максимальная задолженность</b>"
                "<br>"
                "%{x|%d.%m.%Y}"
                "<br>"
                "%{y:,.2f} ₽"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Изменение
    # =============================================================

    if absolute_change > 0:
        change_color = COLORS["red"]
        sign = "+"

    elif absolute_change < 0:
        change_color = COLORS["green"]
        sign = ""

    else:
        change_color = COLORS["muted"]
        sign = ""

    change_money = (
        f"{sign}"
        f"{compact_money(absolute_change)}"
    )

    change_percent = (
        f"{sign}{change_pct:.1f}%"
        if change_pct is not None
        else "—"
    )

    # =============================================================
    # Верхние KPI
    # =============================================================

    metric_positions = [
        {
            "x": 0.00,
            "title": "Начало периода",
            "value": compact_money(
                start_total
            ),
            "color": COLORS["text"],
        },
        {
            "x": 0.32,
            "title": "Конец периода",
            "value": compact_money(
                end_total
            ),
            "color": COLORS["text"],
        },
        {
            "x": 0.64,
            "title": "Изменение",
            "value": (
                f"{change_money}"
                f"<br>{change_percent}"
            ),
            "color": change_color,
        },
        {
            "x": 0.86,
            "title": "Максимум",
            "value": compact_money(
                peak_value
            ),
            "color": COLORS["text"],
        },
    ]

    for metric in metric_positions:

        fig.add_annotation(
            x=metric["x"],
            y=1.24,

            xref="paper",
            yref="paper",

            xanchor="left",
            yanchor="top",

            text=(
                "<span "
                "style='color:#6B7280;"
                "font-size:11px'>"
                f"{metric['title']}"
                "</span>"
                "<br>"
                "<b>"
                f"{metric['value']}"
                "</b>"
            ),

            showarrow=False,

            align="left",

            font={
                "size": 11,
                "color": metric["color"],
            },
        )

    # =============================================================
    # Layout
    # =============================================================

    fig.update_layout(
        **base_layout(
            height=410,

            margin={
                "l": 62,
                "r": 60,
                "t": 105,
                "b": 42,
            },
        ),

        hovermode="x unified",

        # ---------------------------------------------------------
        # Легенда
        # ---------------------------------------------------------

        legend={
            "orientation": "h",

            "x": 0,
            "y": 1.03,

            "xanchor": "left",
            "yanchor": "bottom",

            "font": {
                "size": 11,
            },

            "itemwidth": 40,
        },

        # ---------------------------------------------------------
        # Правая шкала процентов
        # ---------------------------------------------------------

        yaxis2={
            "overlaying": "y",
            "side": "right",

            "showgrid": False,
            "zeroline": False,

            "tickformat": "~s",

            "tickfont": {
                "size": 9,
                "color": COLORS["orange"],
            },

            "title": None,

            "rangemode": "tozero",
        },

        showlegend=True,
    )

    # =============================================================
    # Левая шкала
    # =============================================================

    fig.update_yaxes(
        showgrid=True,

        gridcolor="#E7ECEA",
        griddash="dot",
        gridwidth=1,

        zeroline=False,

        tickformat="~s",

        tickfont={
            "size": 10,
            "color": COLORS["muted"],
        },

        title=None,

        rangemode="tozero",
    )

    # =============================================================
    # X
    # =============================================================

    fig.update_xaxes(
        showgrid=False,

        showline=True,
        linewidth=1,
        linecolor=COLORS["border"],

        tickformat="%d.%m.%y",

        tickfont={
            "size": 10,
            "color": COLORS["muted"],
        },

        automargin=True,
    )

    return fig


def build_counterparty_debt_chart(
    df: pd.DataFrame,
    top_n: int = 5,
) -> go.Figure:
    """
    TOP контрагентов по текущей задолженности.

    На графике:
    - только контрагенты с ненулевым долгом;
    - по умолчанию TOP-5;
    - подписи выводятся в млн / тыс / рублях;
    - справа оставлен запас под значения.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # =============================================================
    # Подготовка
    # =============================================================

    work["counterparty_name"] = (
        work["counterparty_name"]
        .fillna("Без контрагента")
        .astype(str)
        .str.strip()
    )

    work["total_debt"] = pd.to_numeric(
        work["total_debt"],
        errors="coerce",
    ).fillna(0)

    # =============================================================
    # Агрегация
    # =============================================================

    summary = (
        work.groupby(
            "counterparty_name",
            as_index=False,
        )
        .agg(
            total_debt=(
                "total_debt",
                "sum",
            ),
            contracts=(
                "contract_id",
                "nunique",
            ),
        )
    )

    # -------------------------------------------------------------
    # Убираем нулевой долг
    # -------------------------------------------------------------

    summary = summary[
        summary["total_debt"] > 0.01
    ].copy()

    if summary.empty:
        return empty_figure(
            "На выбранную дату задолженность отсутствует"
        )

    # =============================================================
    # Доля в общем портфеле
    # =============================================================

    total_portfolio_debt = float(
        summary["total_debt"].sum()
    )

    summary["share_pct"] = (
        summary["total_debt"]
        / total_portfolio_debt
        * 100
    )

    # =============================================================
    # TOP-N
    # =============================================================

    summary = (
        summary
        .sort_values(
            "total_debt",
            ascending=False,
        )
        .head(top_n)
        .sort_values(
            "total_debt",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    # =============================================================
    # Подписи
    # =============================================================

    text_labels = [
        _money_text(value)
        for value in summary["total_debt"]
    ]

    customdata = np.column_stack(
        [
            summary["contracts"],
            summary["share_pct"],
        ]
    )

    # =============================================================
    # Figure
    # =============================================================

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=summary["total_debt"],
            y=summary["counterparty_name"],

            orientation="h",

            marker={
                "color": (
                    "rgba(60,122,103,0.68)"
                ),
                "line": {
                    "color": COLORS["green"],
                    "width": 0.8,
                },
            },

            text=text_labels,
            textposition="outside",

            textfont={
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 11,
                "color": COLORS["text"],
            },

            cliponaxis=False,

            customdata=customdata,

            hovertemplate=(
                "<b>%{y}</b>"
                "<br><br>"
                "Общий долг: "
                "<b>%{x:,.2f} ₽</b>"
                "<br>"
                "Доля портфеля: "
                "<b>%{customdata[1]:.1f}%</b>"
                "<br>"
                "Договоров: "
                "<b>%{customdata[0]:,.0f}</b>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Запас справа под подписи
    # =============================================================

    max_debt = float(
        summary["total_debt"].max()
    )

    x_max = (
        max_debt * 1.22
        if max_debt > 0
        else 1
    )

    # =============================================================
    # Layout
    # =============================================================

    fig.update_layout(
        **base_layout(
            height=410,
            margin={
                "l": 235,
                "r": 80,
                "t": 18,
                "b": 42,
            },
        ),

        showlegend=False,
        bargap=0.28,
        hovermode="closest",
    )

    fig.update_xaxes(
        range=[
            0,
            x_max,
        ],

        showgrid=True,
        gridcolor="#E8ECEF",
        griddash="dot",
        gridwidth=1,

        zeroline=False,
        tickformat="~s",

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 10,
            "color": COLORS["muted"],
        },

        showline=False,
    )

    fig.update_yaxes(
        showgrid=False,

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 11,
            "color": COLORS["text"],
        },

        automargin=True,
        ticks="",
    )

    return fig



def build_maturity_chart(
    df: pd.DataFrame,
) -> go.Figure:
    """
    Распределение текущей задолженности
    по срокам погашения.

    Визуально показывает:
    - просроченную задолженность;
    - долг к погашению в ближайшие периоды;
    - средне- и долгосрочную часть портфеля;
    - сумму и долю каждой категории.

    Категория "Без даты" намеренно
    не отображается на графике.
    """

    summary = build_maturity_summary(
        df
    )

    if summary.empty:
        return empty_figure()

    work = summary.copy()

    # =============================================================
    # Убираем "Без даты" именно с графика
    # =============================================================

    work = work[
        work["maturity_bucket"]
        != "Без даты"
    ].copy()

    # =============================================================
    # Подготовка
    # =============================================================

    work["total_debt"] = pd.to_numeric(
        work["total_debt"],
        errors="coerce",
    ).fillna(0)

    work["contracts"] = pd.to_numeric(
        work["contracts"],
        errors="coerce",
    ).fillna(0)

    total_debt = float(
        pd.to_numeric(
            df["total_debt"],
            errors="coerce",
        )
        .fillna(0)
        .clip(lower=0)
        .sum()
    )

    if total_debt > 0:
        work["share_pct"] = (
            work["total_debt"]
            / total_debt
            * 100
        )
    else:
        work["share_pct"] = 0.0

    # =============================================================
    # Порядок категорий
    # =============================================================

    maturity_order = [
        "Просрочено",
        "До 30 дней",
        "31–90 дней",
        "91–180 дней",
        "181–365 дней",
        "Более года",
    ]

    # =============================================================
    # Цвета
    # =============================================================

    palette = {
        "Просрочено": COLORS["red"],
        "До 30 дней": COLORS["orange"],
        "31–90 дней": "#C89535",
        "91–180 дней": "#9A8E4F",
        "181–365 дней": COLORS["green"],
        "Более года": COLORS["blue"],
    }

    colors = [
        palette.get(
            bucket,
            COLORS["green"],
        )
        for bucket in work[
            "maturity_bucket"
        ]
    ]

    # =============================================================
    # Helper
    # =============================================================

    def bucket_value(
        bucket_name: str,
    ) -> float:

        rows = work.loc[
            work["maturity_bucket"]
            == bucket_name,
            "total_debt",
        ]

        if rows.empty:
            return 0.0

        return float(
            rows.iloc[0]
        )

    def share_of_total(
        value: float,
    ) -> float:

        if total_debt <= 0:
            return 0.0

        return (
            value
            / total_debt
            * 100
        )

    # =============================================================
    # Верхние показатели
    # =============================================================

    overdue_debt = bucket_value(
        "Просрочено"
    )

    due_30_debt = bucket_value(
        "До 30 дней"
    )

    due_90_debt = (
        due_30_debt
        + bucket_value(
            "31–90 дней"
        )
    )

    long_term_debt = bucket_value(
        "Более года"
    )

    # =============================================================
    # Подписи столбиков
    # =============================================================

    text_labels = []

    for _, row in work.iterrows():

        debt = float(
            row["total_debt"]
        )

        share = float(
            row["share_pct"]
        )

        if debt <= 0:
            text_labels.append("")
            continue

        text_labels.append(
            (
                f"<b>{_money_text(debt)}</b>"
                "<br>"
                f"{share:.1f}%"
            )
        )

    customdata = np.column_stack(
        [
            work["contracts"],
            work["share_pct"],
        ]
    )

    # =============================================================
    # Figure
    # =============================================================

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=work[
                "maturity_bucket"
            ],

            y=work[
                "total_debt"
            ],

            marker={
                "color": colors,

                "line": {
                    "color": "#FFFFFF",
                    "width": 1,
                },
            },

            width=0.64,

            text=text_labels,

            textposition="outside",

            textfont={
                "family": (
                    "Inter, Arial, sans-serif"
                ),
                "size": 11,
                "color": COLORS["text"],
            },

            cliponaxis=False,

            customdata=customdata,

            hovertemplate=(
                "<b>%{x}</b>"
                "<br><br>"
                "Задолженность: "
                "<b>%{y:,.2f} ₽</b>"
                "<br>"
                "Доля портфеля: "
                "<b>%{customdata[1]:.1f}%</b>"
                "<br>"
                "Договоров: "
                "<b>%{customdata[0]:,.0f}</b>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # KPI сверху
    # =============================================================

    top_metrics = [
        {
            "x": 0.00,
            "title": "Просрочено",
            "value": _money_text(
                overdue_debt
            ),
            "share": share_of_total(
                overdue_debt
            ),
            "color": (
                COLORS["red"]
                if overdue_debt > 0
                else COLORS["muted"]
            ),
        },

        {
            "x": 0.36,
            "title": (
                "К погашению ≤ 90 дней"
            ),
            "value": _money_text(
                due_90_debt
            ),
            "share": share_of_total(
                due_90_debt
            ),
            "color": (
                COLORS["orange"]
                if due_90_debt > 0
                else COLORS["muted"]
            ),
        },

        {
            "x": 0.73,
            "title": "Со сроком более года",
            "value": _money_text(
                long_term_debt
            ),
            "share": share_of_total(
                long_term_debt
            ),
            "color": (
                COLORS["blue"]
                if long_term_debt > 0
                else COLORS["muted"]
            ),
        },
    ]

    for metric in top_metrics:

        fig.add_annotation(
            x=metric["x"],
            y=1.23,

            xref="paper",
            yref="paper",

            xanchor="left",
            yanchor="top",

            text=(
                "<span "
                "style='color:#6B7280;"
                "font-size:10px'>"
                f"{metric['title']}"
                "</span>"
                "<br>"

                "<b>"
                f"{metric['value']}"
                "</b>"
                "<br>"

                "<span "
                "style='font-size:10px'>"
                f"{metric['share']:.1f}% "
                "портфеля"
                "</span>"
            ),

            showarrow=False,

            align="left",

            font={
                "size": 11,
                "color": metric[
                    "color"
                ],
            },
        )

    # =============================================================
    # Верхний запас
    # =============================================================

    max_value = float(
        work["total_debt"].max()
    )

    y_max = (
        max_value * 1.22
        if max_value > 0
        else 1
    )

    # =============================================================
    # Layout
    # =============================================================

    fig.update_layout(
        **base_layout(
            height=410,

            margin={
                "l": 58,
                "r": 22,
                "t": 92,
                "b": 68,
            },
        ),

        showlegend=False,

        bargap=0.24,

        hovermode="closest",
    )

    # =============================================================
    # X
    # =============================================================

    fig.update_xaxes(
        categoryorder="array",
        categoryarray=maturity_order,

        tickangle=0,

        showgrid=False,

        showline=True,

        linewidth=1,

        linecolor=COLORS[
            "border"
        ],

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 10,
            "color": COLORS["text"],
        },

        ticks="",

        automargin=True,
    )

    # =============================================================
    # Y
    # =============================================================

    fig.update_yaxes(
        range=[
            0,
            y_max,
        ],

        showgrid=True,

        gridcolor="#E8ECEF",

        griddash="dot",

        gridwidth=1,

        zeroline=False,

        tickformat="~s",

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 10,
            "color": COLORS["muted"],
        },

        title=None,
    )

    return fig




def build_interest_flow_chart(
    df: pd.DataFrame,
) -> go.Figure:
    """
    Анализ процентного потока по месяцам.

    Показывает:
    - начисленные проценты;
    - погашенные проценты;
    - чистый процентный поток:
      начислено - погашено;
    - ключевые показатели за выбранный период.
    """

    if df.empty:
        return empty_figure()

    work = df.copy()

    # =============================================================
    # Подготовка
    # =============================================================

    work["month"] = pd.to_datetime(
        work["month"],
        errors="coerce",
    )

    for column in (
        "interest_accrued",
        "interest_repaid",
    ):
        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        ).fillna(0)

    work = (
        work
        .dropna(
            subset=["month"]
        )
        .sort_values("month")
        .reset_index(drop=True)
    )

    if work.empty:
        return empty_figure()

    # =============================================================
    # Расчёты
    # =============================================================

    work["net_interest_flow"] = (
        work["interest_accrued"]
        - work["interest_repaid"]
    )

    total_accrued = float(
        work["interest_accrued"].sum()
    )

    total_repaid = float(
        work["interest_repaid"].sum()
    )

    net_flow = (
        total_accrued
        - total_repaid
    )

    repayment_ratio = None

    if total_accrued > 0:
        repayment_ratio = (
            total_repaid
            / total_accrued
            * 100
        )

    # =============================================================
    # Максимальные месяцы
    # =============================================================

    max_accrued_idx = (
        work["interest_accrued"]
        .idxmax()
    )

    max_repaid_idx = (
        work["interest_repaid"]
        .idxmax()
    )

    max_accrued_row = (
        work.loc[
            max_accrued_idx
        ]
    )

    max_repaid_row = (
        work.loc[
            max_repaid_idx
        ]
    )

    # =============================================================
    # Цвет чистого потока
    # =============================================================

    if net_flow > 0:
        net_color = COLORS["red"]

    elif net_flow < 0:
        net_color = COLORS["green"]

    else:
        net_color = COLORS["muted"]

    # =============================================================
    # Figure
    # =============================================================

    fig = go.Figure()

    # -------------------------------------------------------------
    # Начислено
    # -------------------------------------------------------------

    fig.add_trace(
        go.Bar(
            x=work["month"],
            y=work["interest_accrued"],

            name="Начислено",

            marker={
                "color": (
                    "rgba(180,83,9,0.68)"
                ),

                "line": {
                    "color": COLORS["orange"],
                    "width": 0.8,
                },
            },

            hovertemplate=(
                "<b>%{x|%m.%Y}</b>"
                "<br><br>"
                "Начислено процентов: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # -------------------------------------------------------------
    # Погашено
    # -------------------------------------------------------------

    fig.add_trace(
        go.Bar(
            x=work["month"],
            y=work["interest_repaid"],

            name="Погашено",

            marker={
                "color": (
                    "rgba(60,122,103,0.68)"
                ),

                "line": {
                    "color": COLORS["green"],
                    "width": 0.8,
                },
            },

            hovertemplate=(
                "<b>%{x|%m.%Y}</b>"
                "<br><br>"
                "Погашено процентов: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # -------------------------------------------------------------
    # Чистый процентный поток
    # -------------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=work["month"],
            y=work["net_interest_flow"],

            name="Чистый поток",

            mode="lines+markers",

            line={
                "color": COLORS["dark"],
                "width": 2.2,
            },

            marker={
                "size": 6,

                "color": [
                    (
                        COLORS["red"]
                        if value > 0
                        else (
                            COLORS["green"]
                            if value < 0
                            else COLORS["muted"]
                        )
                    )
                    for value
                    in work[
                        "net_interest_flow"
                    ]
                ],

                "line": {
                    "color": "#FFFFFF",
                    "width": 1,
                },
            },

            hovertemplate=(
                "<b>%{x|%m.%Y}</b>"
                "<br><br>"
                "Чистый поток: "
                "<b>%{y:,.2f} ₽</b>"
                "<br>"
                "<span style='color:#6B7280'>"
                "Начислено − погашено"
                "</span>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Формат KPI
    # =============================================================

    def ratio_text() -> str:

        if repayment_ratio is None:
            return "—"

        return (
            f"{repayment_ratio:.1f}%"
        )

    if net_flow > 0:
        net_prefix = "+"

    else:
        net_prefix = ""

    # =============================================================
    # Верхние KPI
    # =============================================================

    top_metrics = [
        {
            "x": 0.00,
            "title": (
                "Начислено за период"
            ),
            "value": _money_text(
                total_accrued
            ),
            "sub": None,
            "color": COLORS["orange"],
        },

        {
            "x": 0.28,
            "title": (
                "Погашено за период"
            ),
            "value": _money_text(
                total_repaid
            ),
            "sub": None,
            "color": COLORS["green"],
        },

        {
            "x": 0.56,
            "title": (
                "Чистый поток"
            ),
            "value": (
                f"{net_prefix}"
                f"{_money_text(net_flow)}"
            ),
            "sub": (
                "начислено − погашено"
            ),
            "color": net_color,
        },

        {
            "x": 0.82,
            "title": (
                "Покрытие начислений"
            ),
            "value": ratio_text(),
            "sub": (
                "погашено / начислено"
            ),
            "color": (
                COLORS["green"]
                if (
                    repayment_ratio
                    is not None
                    and repayment_ratio >= 100
                )
                else COLORS["orange"]
            ),
        },
    ]

    for metric in top_metrics:

        text = (
            "<span "
            "style='color:#6B7280;"
            "font-size:10px'>"
            f"{metric['title']}"
            "</span>"
            "<br>"

            "<b>"
            f"{metric['value']}"
            "</b>"
        )

        if metric["sub"]:

            text += (
                "<br>"
                "<span "
                "style='color:#6B7280;"
                "font-size:9px'>"
                f"{metric['sub']}"
                "</span>"
            )

        fig.add_annotation(
            x=metric["x"],
            y=1.24,

            xref="paper",
            yref="paper",

            xanchor="left",
            yanchor="top",

            text=text,

            showarrow=False,

            align="left",

            font={
                "size": 11,
                "color": metric[
                    "color"
                ],
            },
        )

    # =============================================================
    # Отметка максимального начисления
    # =============================================================

    if (
        max_accrued_row[
            "interest_accrued"
        ] > 0
    ):

        fig.add_trace(
            go.Scatter(
                x=[
                    max_accrued_row[
                        "month"
                    ]
                ],

                y=[
                    max_accrued_row[
                        "interest_accrued"
                    ]
                ],

                mode="markers",

                marker={
                    "size": 7,
                    "color": COLORS["red"],

                    "line": {
                        "color": "#FFFFFF",
                        "width": 1,
                    },
                },

                showlegend=False,

                hovertemplate=(
                    "<b>Максимальное начисление</b>"
                    "<br>"
                    "%{x|%m.%Y}"
                    "<br>"
                    "%{y:,.2f} ₽"
                    "<extra></extra>"
                ),
            )
        )

    # =============================================================
    # Нулевая линия для net flow
    # =============================================================

    fig.add_hline(
        y=0,

        line={
            "color": COLORS["border"],
            "width": 1,
        },
    )

    # =============================================================
    # Layout
    # =============================================================

    fig.update_layout(
        **base_layout(
            height=410,

            margin={
                "l": 58,
                "r": 22,

                # Место под KPI
                "t": 100,

                "b": 48,
            },
        ),

        barmode="group",

        bargap=0.26,

        bargroupgap=0.08,

        hovermode="x unified",

        legend={
            "orientation": "h",

            "x": 0,
            "y": 1.02,

            "xanchor": "left",
            "yanchor": "bottom",

            "font": {
                "size": 10,
            },
        },
    )

    # =============================================================
    # X
    # =============================================================

    fig.update_xaxes(
        showgrid=False,

        showline=True,

        linewidth=1,

        linecolor=COLORS[
            "border"
        ],

        tickformat="%m.%Y",

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 10,
            "color": COLORS["muted"],
        },

        automargin=True,
    )

    # =============================================================
    # Y
    # =============================================================

    fig.update_yaxes(
        showgrid=True,

        gridcolor="#E8ECEF",

        griddash="dot",

        gridwidth=1,

        zeroline=False,

        tickformat="~s",

        tickfont={
            "family": (
                "Inter, Arial, sans-serif"
            ),
            "size": 10,
            "color": COLORS["muted"],
        },

        title=None,
    )

    return fig



def build_selected_loan_chart(
    df: pd.DataFrame,
) -> go.Figure:
    """
    Детальная история выбранного займа.

    Показывает:
    - основной долг;
    - задолженность по процентам;
    - общий долг;
    - выдачи / привлечение средств;
    - погашения тела;
    - ключевые показатели договора за период.
    """

    if df.empty:
        return empty_figure(
            "Выберите договор в реестре",
            height=360,
        )

    work = df.copy()

    # =============================================================
    # Подготовка
    # =============================================================

    work["date_from"] = pd.to_datetime(
        work["date_from"],
        errors="coerce",
    )

    numeric_columns = [
        "drawdown_amount",
        "principal_repayment",
        "interest_accrued",
        "interest_repayment",
        "ending_balance",
        "interest_balance",
        "total_debt",
        "rate",
    ]

    for column in numeric_columns:
        if column not in work.columns:
            work[column] = 0.0

        work[column] = pd.to_numeric(
            work[column],
            errors="coerce",
        ).fillna(0)

    work = (
        work
        .dropna(
            subset=["date_from"]
        )
        .sort_values("date_from")
        .reset_index(drop=True)
    )

    if work.empty:
        return empty_figure(
            "Нет данных по выбранному договору",
            height=360,
        )

    # =============================================================
    # KPI
    # =============================================================

    first = work.iloc[0]
    last = work.iloc[-1]

    current_principal = float(
        last["ending_balance"]
    )

    current_interest = float(
        last["interest_balance"]
    )

    current_total = float(
        last["total_debt"]
    )

    current_rate = float(
        last["rate"]
    )

    total_drawdown = float(
        work["drawdown_amount"].sum()
    )

    total_principal_repaid = float(
        work["principal_repayment"].sum()
    )

    total_interest_accrued = float(
        work["interest_accrued"].sum()
    )

    total_interest_repaid = float(
        work["interest_repayment"].sum()
    )

    # =============================================================
    # Helpers
    # =============================================================

    def compact_money(
        value: float,
    ) -> str:

        absolute = abs(value)

        if absolute >= 1_000_000_000:
            return (
                f"{value / 1_000_000_000:.2f}"
                .replace(".", ",")
                + " млрд ₽"
            )

        if absolute >= 1_000_000:
            return (
                f"{value / 1_000_000:.1f}"
                .replace(".", ",")
                + " млн ₽"
            )

        if absolute >= 1_000:
            return (
                f"{value / 1_000:.0f}"
                .replace(".", ",")
                + " тыс. ₽"
            )

        return (
            f"{value:,.0f}"
            .replace(",", " ")
            + " ₽"
        )

    # =============================================================
    # Figure
    # =============================================================

    fig = go.Figure()

    # =============================================================
    # Основной долг
    # =============================================================

    fig.add_trace(
        go.Scatter(
            x=work["date_from"],
            y=work["ending_balance"],

            name="Основной долг",

            mode="lines",

            line={
                "color": COLORS["green"],
                "width": 2.6,
            },

            fill="tozeroy",

            fillcolor=(
                "rgba(60,122,103,0.08)"
            ),

            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br>"
                "Основной долг: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Общий долг
    # =============================================================

    fig.add_trace(
        go.Scatter(
            x=work["date_from"],
            y=work["total_debt"],

            name="Общий долг",

            mode="lines",

            line={
                "color": COLORS["dark"],
                "width": 2.8,
            },

            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br>"
                "Общий долг: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Процентный долг — правая шкала
    # =============================================================

    fig.add_trace(
        go.Scatter(
            x=work["date_from"],
            y=work["interest_balance"],

            name="Проценты",

            mode="lines",

            yaxis="y2",

            line={
                "color": COLORS["orange"],
                "width": 2,
                "dash": "dot",
            },

            hovertemplate=(
                "<b>%{x|%d.%m.%Y}</b>"
                "<br>"
                "Долг по процентам: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Выдачи
    # =============================================================

    drawdowns = work[
        work["drawdown_amount"] > 0.01
    ].copy()

    if not drawdowns.empty:
        fig.add_trace(
            go.Scatter(
                x=drawdowns["date_from"],
                y=drawdowns["total_debt"],

                name="Выдача / привлечение",

                mode="markers",

                marker={
                    "size": 9,
                    "symbol": "triangle-up",
                    "color": COLORS["blue"],
                    "line": {
                        "color": "#FFFFFF",
                        "width": 1.2,
                    },
                },

                customdata=drawdowns[
                    ["drawdown_amount"]
                ].to_numpy(),

                hovertemplate=(
                    "<b>%{x|%d.%m.%Y}</b>"
                    "<br>"
                    "Выдача / привлечение: "
                    "<b>%{customdata[0]:,.2f} ₽</b>"
                    "<br>"
                    "Долг после операции: "
                    "<b>%{y:,.2f} ₽</b>"
                    "<extra></extra>"
                ),
            )
        )

    # =============================================================
    # Погашения тела
    # =============================================================

    repayments = work[
        work["principal_repayment"] > 0.01
    ].copy()

    if not repayments.empty:
        fig.add_trace(
            go.Scatter(
                x=repayments["date_from"],
                y=repayments["total_debt"],

                name="Погашение тела",

                mode="markers",

                marker={
                    "size": 9,
                    "symbol": "triangle-down",
                    "color": COLORS["green"],
                    "line": {
                        "color": "#FFFFFF",
                        "width": 1.2,
                    },
                },

                customdata=repayments[
                    ["principal_repayment"]
                ].to_numpy(),

                hovertemplate=(
                    "<b>%{x|%d.%m.%Y}</b>"
                    "<br>"
                    "Погашение тела: "
                    "<b>%{customdata[0]:,.2f} ₽</b>"
                    "<br>"
                    "Долг после операции: "
                    "<b>%{y:,.2f} ₽</b>"
                    "<extra></extra>"
                ),
            )
        )

    # =============================================================
    # Последняя точка
    # =============================================================

    fig.add_trace(
        go.Scatter(
            x=[
                last["date_from"]
            ],
            y=[
                current_total
            ],

            mode="markers",

            marker={
                "size": 8,
                "color": COLORS["dark"],
                "line": {
                    "color": "#FFFFFF",
                    "width": 1.5,
                },
            },

            showlegend=False,

            hovertemplate=(
                "<b>Текущее состояние</b>"
                "<br>"
                "%{x|%d.%m.%Y}"
                "<br>"
                "Общий долг: "
                "<b>%{y:,.2f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # =============================================================
    # Верхние KPI
    # =============================================================

    metrics = [
        {
            "x": 0.00,
            "title": "Текущий долг",
            "value": compact_money(
                current_total
            ),
            "color": COLORS["dark"],
        },
        {
            "x": 0.27,
            "title": "Основной долг",
            "value": compact_money(
                current_principal
            ),
            "color": COLORS["green"],
        },
        {
            "x": 0.54,
            "title": "Проценты",
            "value": compact_money(
                current_interest
            ),
            "color": COLORS["orange"],
        },
        {
            "x": 0.76,
            "title": "Ставка",
            "value": (
                f"{current_rate:.2f}%"
                if current_rate
                else "—"
            ),
            "color": COLORS["text"],
        },
    ]

    for metric in metrics:

        fig.add_annotation(
            x=metric["x"],
            y=1.23,

            xref="paper",
            yref="paper",

            xanchor="left",
            yanchor="top",

            text=(
                "<span "
                "style='color:#6B7280;"
                "font-size:10px'>"
                f"{metric['title']}"
                "</span>"
                "<br>"
                "<b>"
                f"{metric['value']}"
                "</b>"
            ),

            showarrow=False,

            align="left",

            font={
                "size": 11,
                "color": metric[
                    "color"
                ],
            },
        )

    # =============================================================
    # Layout
    # =============================================================

    fig.update_layout(
        **base_layout(
            height=390,

            margin={
                "l": 62,
                "r": 62,
                "t": 95,
                "b": 48,
            },
        ),

        hovermode="x unified",

        legend={
            "orientation": "h",

            "x": 0,
            "y": 1.02,

            "xanchor": "left",
            "yanchor": "bottom",

            "font": {
                "size": 10,
            },
        },

        yaxis2={
            "overlaying": "y",
            "side": "right",

            "showgrid": False,
            "zeroline": False,

            "tickformat": "~s",

            "tickfont": {
                "size": 9,
                "color": COLORS["orange"],
            },

            "title": None,

            "rangemode": "tozero",
        },
    )

    # =============================================================
    # X
    # =============================================================

    fig.update_xaxes(
        showgrid=False,

        showline=True,

        linecolor=COLORS["border"],
        linewidth=1,

        tickformat="%d.%m.%y",

        tickfont={
            "size": 10,
            "color": COLORS["muted"],
        },

        automargin=True,
    )

    # =============================================================
    # Y
    # =============================================================

    fig.update_yaxes(
        showgrid=True,

        gridcolor="#E8ECEF",
        griddash="dot",

        zeroline=False,

        tickformat="~s",

        tickfont={
            "size": 10,
            "color": COLORS["muted"],
        },

        title=None,

        rangemode="tozero",
    )

    return fig