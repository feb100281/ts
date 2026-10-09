# gear/app/daily_sales/wb_plan_monitor/charts.py
import pandas as pd
import plotly.graph_objects as go

from .formatters import format_money_short, format_pct



def build_progress_chart(current_semi):
    value = float(current_semi["exec_pct"] if current_semi else 0)
    max_value = max(120, value + 10)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={
                "suffix": "%",
                "valueformat": ".1f",
                "font": {
                    "size": 56,
                    "color": "#22324d",
                    "family": "Inter, Arial",
                },
            },
            domain={
                "x": [0.05, 0.95],
                "y": [0.00, 0.86],
            },
            gauge={
                "shape": "angular",
                "axis": {
                    "range": [0, max_value],
                    "tickmode": "array",
                    "tickvals": [0, 20, 40, 60, 80, 100, 120],
                    "ticktext": ["0", "20", "40", "60", "80", "100", "120"],
                    "tickwidth": 1,
                    "ticklen": 8,
                    "tickcolor": "#495057",
                    "tickfont": {
                        "size": 15,
                        "color": "#22324d",
                        "family": "Inter, Arial",
                    },
                },
                "bar": {
                    "color": "#228be6",
                    "thickness": 0.30,
                },
                "bgcolor": "#ffffff",
                "borderwidth": 1,
                "bordercolor": "#dfe5ec",
                "steps": [
                    {"range": [0, 80], "color": "#fff5f5"},
                    {"range": [80, 100], "color": "#fff9db"},
                    {"range": [100, max_value], "color": "#ebfbee"},
                ],
                "threshold": {
                    "line": {
                        "color": "#2f9e44",
                        "width": 5,
                    },
                    "thickness": 0.78,
                    "value": 100,
                },
            },
        )
    )

    fig.add_annotation(
        x=0.825,
        y=0.345,
        text="план",
        showarrow=False,
        font={
            "size": 15,
            "color": "#2f9e44",
            "family": "Inter, Arial",
        },
    )

    fig.update_layout(
        height=270,
        margin=dict(l=10, r=10, t=36, b=8),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={
            "family": "Inter, Arial",
            "color": "#22324d",
        },
    )

    return fig



def build_monthly_chart(monthly_rows):
    df = pd.DataFrame(monthly_rows)

    plan_color = "#4F6BED"
    fact_color = "#F97316"
    line_color = "#0F766E"
    text_color = "#22324D"
    muted_color = "#64748B"
    grid_color = "#EEF2F6"

    max_money = max(
        float(df["plan"].max() or 0),
        float(df["fact"].max() or 0),
    )

    max_pct = float(df["running_exec_pct"].max() or 0)
    min_pct = float(df["running_exec_pct"].min() or 0)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["month_short"],
            y=df["plan"],
            name="План",
            marker={"color": plan_color, "line": {"width": 0}},
            opacity=0.92,
            hovertemplate="<b>%{x}</b><br>План: %{y:,.0f} ₽<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["month_short"],
            y=df["fact"],
            name="Факт",
            marker={"color": fact_color, "line": {"width": 0}},
            opacity=0.95,
            hovertemplate="<b>%{x}</b><br>Факт: %{y:,.0f} ₽<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["month_short"],
            y=df["running_exec_pct"],
            name="Накопительное выполнение",
            mode="lines+markers",
            yaxis="y2",
            line={
                "color": line_color,
                "width": 4,
                "shape": "spline",
                "smoothing": 0.55,
            },
            marker={
                "size": 10,
                "color": line_color,
                "line": {
                    "width": 2.5,
                    "color": "white",
                },
            },
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Накопительное выполнение: %{y:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    fig.add_shape(
        type="line",
        xref="paper",
        x0=0,
        x1=1,
        yref="y2",
        y0=100,
        y1=100,
        line={
            "color": "#94A3B8",
            "width": 1.3,
            "dash": "dot",
        },
        layer="below",
    )

    fig.add_annotation(
        xref="paper",
        x=1,
        yref="y2",
        y=100,
        text="100%",
        showarrow=False,
        xanchor="right",
        yanchor="bottom",
        font={
            "size": 12,
            "color": muted_color,
            "family": "Inter, Arial",
        },
        bgcolor="rgba(255,255,255,0.78)",
        bordercolor="rgba(148,163,184,0.35)",
        borderwidth=1,
        borderpad=4,
    )

    for i, row in df.iterrows():
        pct = float(row["running_exec_pct"] or 0)

        if i <= 6:
            yshift = 14
        else:
            yshift = -18

        fig.add_annotation(
            x=row["month_short"],
            y=pct,
            yref="y2",
            text=format_pct(pct),
            showarrow=False,
            yshift=yshift,
            font={
                "size": 11,
                "color": text_color,
                "family": "Inter, Arial",
            },
            bgcolor="rgba(255,255,255,0.82)",
            bordercolor="rgba(203,213,225,0.75)",
            borderwidth=1,
            borderpad=3,
        )

    fig.update_layout(
        height=430,
        barmode="group",
        bargap=0.30,
        bargroupgap=0.10,
        margin=dict(l=34, r=38, t=64, b=34),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={
            "family": "Inter, Arial",
            "color": text_color,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.08,
            "xanchor": "left",
            "x": 0,
            "font": {
                "size": 14,
                "color": text_color,
            },
            "itemsizing": "constant",
        },
        hovermode="x unified",
        hoverlabel={
            "bgcolor": "white",
            "bordercolor": "#CBD5E1",
            "font": {
                "size": 13,
                "color": text_color,
                "family": "Inter, Arial",
            },
        },
        yaxis={
            "title": None,
            "range": [0, max_money * 1.20],
            "showgrid": True,
            "gridcolor": grid_color,
            "gridwidth": 1,
            "zeroline": False,
            "tickfont": {
                "size": 13,
                "color": muted_color,
            },
            "tickformat": "~s",
            "ticksuffix": " ₽",
        },
        yaxis2={
            "title": None,
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "zeroline": False,
            "range": [
                max(0, min_pct - 10),
                max(110, max_pct + 8),
            ],
            "tickfont": {
                "size": 13,
                "color": muted_color,
            },
            "ticksuffix": "%",
        },
    )

    fig.update_xaxes(
        showline=False,
        showgrid=False,
        zeroline=False,
        tickfont={
            "size": 16,
            "color": text_color,
        },
    )

    return fig







def build_daily_chart(daily_rows):
    df = pd.DataFrame(daily_rows).copy()

    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            height=500,
            paper_bgcolor="white",
            plot_bgcolor="white",
            margin=dict(l=35, r=35, t=35, b=40),
        )
        return fig

    df["returns_amount_negative"] = -df["returns_amount"]

    df["return_rate"] = df.apply(
        lambda x: x["returns_amount"] / x["sales_amount"] * 100
        if x["sales_amount"] else 0,
        axis=1,
    )

    fig = go.Figure()

    # Продажи — голубые столбцы, уже не бледные
    fig.add_trace(
        go.Bar(
            x=df["date_label"],
            y=df["sales_amount"],
            name="Продажи",
            marker=dict(
                color="rgba(37, 99, 235, 0.42)",
                line=dict(
                    color="rgba(37, 99, 235, 0.70)",
                    width=1,
                ),
            ),
            customdata=df[
                [
                    "sales_transactions",
                    "returns_amount",
                    "returns_transactions",
                    "fact",
                    "qty",
                    "avg_price",
                    "return_rate",
                ]
            ],
            hovertemplate=(
                "<b>%{x}</b><br><br>"
                "Продажи: <b>%{y:,.0f} ₽</b><br>"
                "Кол-во продаж: %{customdata[0]:,.0f}<br>"
                "Возвраты: %{customdata[1]:,.0f} ₽<br>"
                "Кол-во возвратов: %{customdata[2]:,.0f}<br>"
                "Доля возвратов: %{customdata[6]:.1f}%<br><br>"
                "Выручка net: <b>%{customdata[3]:,.0f} ₽</b><br>"
                "Кол-во net: %{customdata[4]:,.0f}<br>"
                "Ср. цена: %{customdata[5]:,.0f} ₽"
                "<extra></extra>"
            ),
        )
    )

    # Возвраты — мягкий, но заметный красный
    fig.add_trace(
        go.Bar(
            x=df["date_label"],
            y=df["returns_amount_negative"],
            name="Возвраты",
            marker=dict(
                color="rgba(239, 68, 68, 0.45)",
                line=dict(
                    color="rgba(220, 38, 38, 0.70)",
                    width=1,
                ),
            ),
            customdata=df[["returns_amount", "returns_transactions", "return_rate"]],
            hovertemplate=(
                "<b>%{x}</b><br><br>"
                "Возвраты: <b>%{customdata[0]:,.0f} ₽</b><br>"
                "Кол-во возвратов: %{customdata[1]:,.0f}<br>"
                "Доля возвратов: %{customdata[2]:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    
    # Выручка net — главная линия
    fig.add_trace(
        go.Scatter(
            x=df["date_label"],
            y=df["fact"],
            name="Выручка net",
            mode="lines+markers",
            line=dict(
                color="#0f172a",
                width=3.4,
                shape="spline",
                smoothing=0.35,
            ),
            marker=dict(
                size=8,
                color="#0f172a",
                line=dict(
                    color="white",
                    width=1.6,
                ),
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Выручка net: <b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # Средняя цена — ярче и читаемее
    fig.add_trace(
        go.Scatter(
            x=df["date_label"],
            y=df["avg_price"],
            name="Ср. цена",
            mode="lines+markers",
            yaxis="y2",
            line=dict(
                color="#f97316",
                width=2.8,
                dash="dot",
                shape="spline",
                smoothing=0.35,
            ),
            marker=dict(
                size=7,
                color="#f97316",
                line=dict(
                    color="white",
                    width=1.4,
                ),
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Средняя цена: <b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    fig.add_hline(
        y=0,
        line_width=1,
        line_color="#94a3b8",
    )

    fig.update_layout(
        height=500,
        barmode="relative",
        bargap=0.14,
        margin=dict(l=60, r=75, t=55, b=80),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",

        font=dict(
            family="Inter, Arial, sans-serif",
            size=13,
            color="#334155",
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="center",
            x=0.5,
            font=dict(
                size=15,
                color="#334155",
            ),
            bgcolor="rgba(255,255,255,0)",
        ),

        xaxis=dict(
            title=None,
            showgrid=False,
            tickangle=-45,
            tickfont=dict(
                size=12,
                color="#334155",
            ),
            linecolor="#cbd5e1",
            linewidth=1,
        ),

        yaxis=dict(
            title=dict(
                text="Сумма, ₽",
                font=dict(
                    size=13,
                    color="#2563eb",
                ),
            ),
            tickformat="~s",
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.22)",
            zeroline=False,
            tickfont=dict(
                size=12,
                color="#2563eb",
            ),
            linecolor="#cbd5e1",
            linewidth=1,
        ),

        yaxis2=dict(
            title=dict(
                text="Ср. цена, ₽",
                font=dict(
                    size=13,
                    color="#f97316",
                ),
            ),
            overlaying="y",
            side="right",
            showgrid=False,
            tickformat=",.0f",
            tickfont=dict(
                size=12,
                color="#f97316",
            ),
            linecolor="#cbd5e1",
            linewidth=1,
        ),
    )

    fig.update_traces(
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_color="#111827",
            bordercolor="#cbd5e1",
        )
    )

    fig.update_xaxes(
        rangeslider_visible=False,
        fixedrange=False,
    )

    fig.update_yaxes(
        fixedrange=False,
    )

    return fig




def build_current_month_plan_chart(current_month):
    rows = current_month.get("rows", [])

    df = pd.DataFrame(rows)

    if df.empty:
        fig = go.Figure()

        fig.update_layout(
            height=460,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        return fig

    # ---------------------------------------------------------
    # Цвета
    # ---------------------------------------------------------

    fact_color = "#2563EB"
    plan_color = "#F97316"
    positive_color = "#0F766E"
    negative_color = "#DC2626"
    neutral_color = "#64748B"

    # ---------------------------------------------------------
    # Подготовка данных
    # ---------------------------------------------------------

    df = df.copy()

    numeric_columns = [
        "running_plan",
        "running_fact",
        "exec_to_date_pct",
        "delta_to_plan",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0)

    # Отклонение от плана в %
    df["delta_to_plan_pct"] = (
        df["delta_to_plan"]
        .div(df["running_plan"].replace(0, pd.NA))
        .mul(100)
        .fillna(0)
    )

    # Красивые строки для hover
    df["delta_to_plan_hover"] = df["delta_to_plan"].apply(
        lambda x: f"{x:+,.0f} ₽"
    )

    df["delta_to_plan_pct_hover"] = df["delta_to_plan_pct"].apply(
        lambda x: f"{x:+.1f}%"
    )

    fig = go.Figure()

    # ---------------------------------------------------------
    # Накопительный план
    # ---------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=df["date_label"],
            y=df["running_plan"],
            name="План к дате",
            mode="lines",

            line=dict(
                color=plan_color,
                width=3,
                dash="dash",
            ),

            hovertemplate=(
                "<b>%{x}</b><br>"
                "План к дате: "
                "<b>%{y:,.0f} ₽</b>"
                "<extra></extra>"
            ),
        )
    )

    # ---------------------------------------------------------
    # Зона между планом и фактом
    #
    # Позволяет визуально увидеть размер отклонения.
    # ---------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=df["date_label"],
            y=df["running_fact"],
            mode="lines",
            line=dict(
                width=0,
            ),
            fill="tonexty",
            fillcolor="rgba(37, 99, 235, 0.07)",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # ---------------------------------------------------------
    # Накопительный факт
    # ---------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=df["date_label"],
            y=df["running_fact"],
            name="Факт",
            mode="lines+markers",

            line=dict(
                color=fact_color,
                width=3.5,
                shape="spline",
                smoothing=0.35,
            ),

            marker=dict(
                size=7,
                color=fact_color,
                line=dict(
                    color="white",
                    width=1.5,
                ),
            ),

            customdata=df[
                    [
                        "running_plan",
                        "exec_to_date_pct",
                        "delta_to_plan_hover",
                        "delta_to_plan_pct_hover",
                    ]
                ],
           hovertemplate=(
                    "<b>%{x}</b><br><br>"

                    "Факт: "
                    "<b>%{y:,.0f} ₽</b><br>"

                    "План: "
                    "%{customdata[0]:,.0f} ₽<br>"

                    "Выполнение: "
                    "<b>%{customdata[1]:.1f}%</b><br>"

                    "Отклонение: "
                    "<b>%{customdata[2]}</b> "
                    "(%{customdata[3]})"

                    "<extra></extra>"
                ),
        )
    )

    # ---------------------------------------------------------
    # Процент выполнения
    # ---------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=df["date_label"],
            y=df["exec_to_date_pct"],
            name="Выполнение к дате",
            mode="lines+markers",

            yaxis="y2",

            line=dict(
                color=positive_color,
                width=2,
            ),

            marker=dict(
                size=5,
                color=positive_color,
            ),

            hovertemplate=(
                "<b>%{x}</b><br>"
                "Выполнение: "
                "<b>%{y:.1f}%</b>"
                "<extra></extra>"
            ),
        )
    )

    # ---------------------------------------------------------
    # Уровень выполнения плана — 100%
    # ---------------------------------------------------------

    fig.add_hline(
        y=100,
        yref="y2",

        line_width=1,
        line_dash="dot",
        line_color="#94A3B8",

        annotation_text="100% плана",
        annotation_position="top right",

        annotation_font=dict(
            size=11,
            color=neutral_color,
        ),
    )

    # ---------------------------------------------------------
    # Текущий статус — последняя точка
    # ---------------------------------------------------------

    last_row = df.iloc[-1]

    last_date = last_row["date_label"]

    last_fact = float(
        last_row["running_fact"]
    )

    last_plan = float(
        last_row["running_plan"]
    )

    last_exec = float(
        last_row["exec_to_date_pct"]
    )

    last_delta = float(
        last_row["delta_to_plan"]
    )

    last_delta_pct = float(
        last_row["delta_to_plan_pct"]
    )

    status_color = (
        positive_color
        if last_delta >= 0
        else negative_color
    )

    status_sign = (
        "▲"
        if last_delta >= 0
        else "▼"
    )

    # Крупная последняя точка
    fig.add_trace(
        go.Scatter(
            x=[last_date],
            y=[last_fact],

            mode="markers",

            marker=dict(
                size=13,
                color=status_color,
                line=dict(
                    color="white",
                    width=3,
                ),
            ),

            hoverinfo="skip",

            showlegend=False,
        )
    )

    # ---------------------------------------------------------
    # Подпись текущего результата
    # ---------------------------------------------------------

    fig.add_annotation(
        x=last_date,
        y=last_fact,

        text=(
            f"<b>{last_exec:.1f}% плана</b>"
            "<br>"
            f"{status_sign} "
            f"{last_delta:+,.0f} ₽ "
            f"({last_delta_pct:+.1f}%)"
        ),

        showarrow=True,

        arrowhead=0,
        arrowwidth=1,
        arrowcolor=status_color,

        ax=-15,
        ay=-65,

        align="left",

        bgcolor="rgba(255,255,255,0.96)",

        bordercolor=status_color,
        borderwidth=1,
        borderpad=7,

        font=dict(
            size=12,
            color=status_color,
        ),
    )

    # ---------------------------------------------------------
    # Масштабы
    # ---------------------------------------------------------

    max_money = max(
        float(df["running_plan"].max() or 0),
        float(df["running_fact"].max() or 0),
    )

    max_pct = max(
        110,
        float(
            df["exec_to_date_pct"].max() or 0
        ) + 10,
    )

    # ---------------------------------------------------------
    # Layout
    # ---------------------------------------------------------

    fig.update_layout(
        height=480,

        margin=dict(
            l=60,
            r=80,
            t=70,
            b=65,
        ),

        paper_bgcolor="white",
        plot_bgcolor="white",

        hovermode="x unified",

        font=dict(
            family="Inter, Arial, sans-serif",
            size=13,
            color="#334155",
        ),

        legend=dict(
            orientation="h",

            yanchor="bottom",
            y=1.05,

            xanchor="left",
            x=0,

            font=dict(
                size=12,
            ),
        ),

        xaxis=dict(
            title=None,

            showgrid=False,

            tickangle=-45,

            linecolor="#CBD5E1",

            ticks="outside",

            tickfont=dict(
                size=11,
                color="#64748B",
            ),
        ),

        yaxis=dict(
            title="Накопительно, ₽",

            range=[
                0,
                max_money * 1.18
                if max_money > 0
                else 1,
            ],

            showgrid=True,

            gridcolor="rgba(148,163,184,0.18)",

            zeroline=False,

            tickformat="~s",

            title_font=dict(
                size=12,
                color="#64748B",
            ),

            tickfont=dict(
                size=11,
                color="#64748B",
            ),
        ),

        yaxis2=dict(
            title="Выполнение, %",

            overlaying="y",
            side="right",

            range=[
                0,
                max_pct,
            ],

            showgrid=False,
            zeroline=False,

            ticksuffix="%",

            title_font=dict(
                size=12,
                color=positive_color,
            ),

            tickfont=dict(
                size=11,
                color=positive_color,
            ),
        ),
    )

    return fig