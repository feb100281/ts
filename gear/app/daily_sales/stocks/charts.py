# gear/app/daily_sales/stocks/charts.py

import pandas as pd
import plotly.express as px


FONT_FAMILY = (
    "Inter, -apple-system, BlinkMacSystemFont, "
    "Segoe UI, Roboto, Arial, sans-serif"
)

COLORS = {
    "bg": "#FFFFFF",
    "text": "#111827",
    "title": "#111827",
    "subtitle": "#6B7280",
    "hover_bg": "#FFFFFF",
    "hover_border": "#CBD5E1",
    "white": "#FFFFFF",
}

# Готовые палитры Plotly
QTY_SCALE = px.colors.sequential.Tealgrn
COST_SCALE = px.colors.sequential.Emrld
DELTA_SCALE = px.colors.diverging.RdYlGn


def _fmt_date(report_date) -> str:
    return pd.to_datetime(report_date).strftime("%d.%m.%Y")


def _fmt_file_date(report_date) -> str:
    return pd.to_datetime(report_date).strftime("%Y-%m-%d")


def _prepare_chart_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    money_cols = [
        "Бух. с/с за ед.",
        "Упр. с/с за ед.",
        "Бух. с/с всего",
        "Упр. с/с всего",
    ]

    for col in money_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0) / 100
        else:
            df[col] = 0

    for col in ["Бренд", "Категория", "Наименование"]:
        if col not in df.columns:
            df[col] = f"{col} не указан"

        df[col] = (
            df[col]
            .fillna(f"{col} не указан")
            .astype(str)
            .str.strip()
            .replace("", f"{col} не указан")
        )

    qty_cols = [
        "Итого количество",
        "Остаток на складе",
        "В пути от клиента",
        "В пути к клиенту",
    ]

    for col in qty_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    return df


def _safe_div(num, den):
    return num / den if den else 0


def _build_grouped_df(df: pd.DataFrame) -> pd.DataFrame:
    df = _prepare_chart_df(df)

    chart_df = (
        df.groupby(
            ["Бренд", "Категория", "Наименование"],
            dropna=False,
            as_index=False,
        )
        .agg(
            {
                "Итого количество": "sum",
                "Остаток на складе": "sum",
                "В пути от клиента": "sum",
                "В пути к клиенту": "sum",
                "Упр. с/с всего": "sum",
                "Бух. с/с всего": "sum",
            }
        )
    )

    chart_df = chart_df[chart_df["Итого количество"] > 0].copy()

    chart_df["Δ стоимости"] = (
        chart_df["Упр. с/с всего"] - chart_df["Бух. с/с всего"]
    )

    chart_df["Упр. с/с за ед."] = chart_df.apply(
        lambda r: _safe_div(
            r["Упр. с/с всего"],
            r["Итого количество"],
        ),
        axis=1,
    )

    chart_df["Бух. с/с за ед."] = chart_df.apply(
        lambda r: _safe_div(
            r["Бух. с/с всего"],
            r["Итого количество"],
        ),
        axis=1,
    )

    chart_df["Δ за ед."] = (
        chart_df["Упр. с/с за ед."] - chart_df["Бух. с/с за ед."]
    )

    return chart_df


def _custom_data_cols():
    return [
        "Итого количество",
        "Остаток на складе",
        "В пути от клиента",
        "В пути к клиенту",
        "Упр. с/с всего",
        "Бух. с/с всего",
        "Упр. с/с за ед.",
        "Бух. с/с за ед.",
        "Δ стоимости",
        "Δ за ед.",
    ]


def _hover_with_prices():
    return (
        "<b style='font-size:14px;'>%{label}</b><br><br>"
        "📦 Количество: <b>%{customdata[0]:,.0f} шт</b><br>"
        "💰 Упр. с/с всего: <b>%{customdata[4]:,.2f} ₽</b><br>"
        "💰 Бух. с/с всего: <b>%{customdata[5]:,.2f} ₽</b><br>"
        "📈 Упр. с/с за ед.: %{customdata[6]:,.2f} ₽<br>"
        "📈 Бух. с/с за ед.: %{customdata[7]:,.2f} ₽<br>"
        "📊 Δ стоимости: %{customdata[8]:,.2f} ₽<br>"
        "📊 Δ за ед.: %{customdata[9]:,.2f} ₽<br><br>"
        "🏪 Остаток: %{customdata[1]:,.0f} шт<br>"
        "📤 В пути от клиента: %{customdata[2]:,.0f} шт<br>"
        "📥 В пути к клиенту: %{customdata[3]:,.0f} шт"
        "<extra></extra>"
    )


def _apply_common_layout(fig, title: str, subtitle: str | None = None):
    title_text = title

    if subtitle:
        title_text = (
            f"{title}"
            f"<br><sup style='color:{COLORS['subtitle']}; "
            f"font-size:13px; font-weight:400;'>{subtitle}</sup>"
        )

    fig.update_layout(
        template="plotly_white",
        font=dict(
            family=FONT_FAMILY,
            size=12,
            color=COLORS["text"],
        ),
        title=dict(
            text=title_text,
            x=0.02,
            xanchor="left",
            y=0.96,
            font=dict(
                size=21,
                color=COLORS["title"],
                family=FONT_FAMILY,
            ),
        ),
        margin=dict(t=82, l=16, r=16, b=16),
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        uniformtext=dict(
            minsize=10,
            mode="hide",
        ),
        hoverlabel=dict(
            bgcolor=COLORS["hover_bg"],
            bordercolor=COLORS["hover_border"],
            font=dict(
                color=COLORS["text"],
                size=12,
                family=FONT_FAMILY,
            ),
            align="left",
        ),
    )

    return fig


def _apply_tree_style(fig):
    fig.update_traces(
        branchvalues="total",
        marker=dict(
            line=dict(
                color=COLORS["white"],
                width=1.5,
            ),
        ),
        textfont=dict(
            color=COLORS["text"],
            size=12,
            family=FONT_FAMILY,
        ),
        textposition="middle center",
        tiling=dict(
            pad=2,
        ),
    )

    return fig


def _apply_sunburst_style(fig):
    fig.update_traces(
        marker=dict(
            line=dict(
                color=COLORS["white"],
                width=1.5,
            ),
        ),
        textfont=dict(
            color=COLORS["text"],
            size=12,
            family=FONT_FAMILY,
        ),
        insidetextorientation="radial",
    )

    return fig


def _empty_html(title: str, message: str) -> bytes:
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: {FONT_FAMILY};
                background: #FFFFFF;
                padding: 40px;
                color: #111827;
            }}
            .card {{
                max-width: 700px;
                margin: 0 auto;
                background: white;
                border-radius: 14px;
                padding: 40px;
                border: 1px solid #E5E7EB;
            }}
            h1 {{
                font-size: 22px;
                margin-top: 0;
            }}
            p {{
                color: #6B7280;
                font-size: 15px;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>{title}</h1>
            <p>{message}</p>
        </div>
    </body>
    </html>
    """

    return html.encode("utf-8")


def _fig_to_html_bytes(fig, filename: str, title: str) -> bytes:
    html = fig.to_html(
        full_html=True,
        include_plotlyjs="cdn",
        config={
            "displaylogo": False,
            "responsive": True,
            "scrollZoom": True,
            "toImageButtonOptions": {
                "format": "png",
                "filename": filename,
                "height": 1600,
                "width": 2600,
                "scale": 3,
            },
        },
    )

    return html.encode("utf-8")


def make_stocks_sunburst_qty_html(
    df: pd.DataFrame,
    report_date,
) -> bytes:
    chart_df = _build_grouped_df(df)
    date_text = _fmt_date(report_date)

    if chart_df.empty:
        return _empty_html(
            "Sunburst остатков",
            f"На дату {date_text} нет данных для построения графика.",
        )

    fig = px.sunburst(
        chart_df,
        path=["Бренд", "Категория", "Наименование"],
        values="Итого количество",
        color="Итого количество",
        color_continuous_scale=QTY_SCALE,
        custom_data=_custom_data_cols(),
    )

    fig.update_traces(
        textinfo="label+value",
        texttemplate=(
            "<b>%{label}</b><br>"
            "%{value:,.0f} шт"
        ),
        hovertemplate=_hover_with_prices(),
    )

    _apply_sunburst_style(fig)

    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Кол-во, шт",
            tickformat=",.0f",
            title_font=dict(size=11),
            tickfont=dict(size=10),
        )
    )

    _apply_common_layout(
        fig,
        f"Sunburst остатков · {date_text}",
        "Размер и цвет = количество товара",
    )

    return _fig_to_html_bytes(
        fig,
        filename=f"stocks_sunburst_qty_{_fmt_file_date(report_date)}",
        title=f"Sunburst остатков · {date_text}",
    )


def make_stocks_treemap_qty_html(
    df: pd.DataFrame,
    report_date,
) -> bytes:
    chart_df = _build_grouped_df(df)
    date_text = _fmt_date(report_date)

    if chart_df.empty:
        return _empty_html(
            "Treemap остатков",
            f"На дату {date_text} нет данных для построения графика.",
        )

    fig = px.treemap(
        chart_df,
        path=["Бренд", "Категория", "Наименование"],
        values="Итого количество",
        color="Итого количество",
        color_continuous_scale=QTY_SCALE,
        custom_data=_custom_data_cols(),
    )

    fig.update_traces(
        textinfo="label+value",
        texttemplate=(
            "<b>%{label}</b><br>"
            "%{value:,.0f} шт<br>"
            "Упр: %{customdata[6]:,.0f} ₽/ед.<br>"
            "Бух: %{customdata[7]:,.0f} ₽/ед."
        ),
        hovertemplate=_hover_with_prices(),
    )

    _apply_tree_style(fig)

    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Кол-во, шт",
            tickformat=",.0f",
            title_font=dict(size=11),
            tickfont=dict(size=10),
        )
    )

    _apply_common_layout(
        fig,
        f"Treemap остатков · {date_text}",
        "Размер и цвет = количество товара",
    )

    return _fig_to_html_bytes(
        fig,
        filename=f"stocks_treemap_qty_{_fmt_file_date(report_date)}",
        title=f"Treemap остатков · {date_text}",
    )


def make_stocks_treemap_man_cost_html(
    df: pd.DataFrame,
    report_date,
) -> bytes:
    chart_df = _build_grouped_df(df)
    date_text = _fmt_date(report_date)

    chart_df = chart_df[chart_df["Упр. с/с всего"] > 0].copy()

    if chart_df.empty:
        return _empty_html(
            "Treemap по стоимости",
            f"На дату {date_text} нет данных с управленческой себестоимостью.",
        )

    fig = px.treemap(
        chart_df,
        path=["Бренд", "Категория", "Наименование"],
        values="Упр. с/с всего",
        color="Упр. с/с всего",
        color_continuous_scale=COST_SCALE,
        custom_data=_custom_data_cols(),
    )

    fig.update_traces(
        textinfo="label+value",
        texttemplate=(
            "<b>%{label}</b><br>"
            "%{value:,.0f} ₽<br>"
            "%{customdata[0]:,.0f} шт<br>"
            "Упр: %{customdata[6]:,.0f} ₽/ед."
        ),
        hovertemplate=_hover_with_prices(),
    )

    _apply_tree_style(fig)

    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Упр. с/с, ₽",
            tickformat=",.0f",
            title_font=dict(size=11),
            tickfont=dict(size=10),
        )
    )

    _apply_common_layout(
        fig,
        f"Treemap по стоимости · {date_text}",
        "Размер и цвет = управленческая себестоимость",
    )

    return _fig_to_html_bytes(
        fig,
        filename=f"stocks_treemap_man_cost_{_fmt_file_date(report_date)}",
        title=f"Treemap по стоимости · {date_text}",
    )


def make_stocks_treemap_cost_delta_html(
    df: pd.DataFrame,
    report_date,
) -> bytes:
    chart_df = _build_grouped_df(df)
    date_text = _fmt_date(report_date)

    chart_df = chart_df[chart_df["Упр. с/с всего"] > 0].copy()

    if chart_df.empty:
        return _empty_html(
            "Treemap разницы себестоимости",
            f"На дату {date_text} нет данных для анализа разницы себестоимости.",
        )

    fig = px.treemap(
        chart_df,
        path=["Бренд", "Категория", "Наименование"],
        values="Упр. с/с всего",
        color="Δ стоимости",
        color_continuous_scale=DELTA_SCALE,
        color_continuous_midpoint=0,
        custom_data=_custom_data_cols(),
    )

    fig.update_traces(
        textinfo="label+value",
        texttemplate=(
            "<b>%{label}</b><br>"
            "%{value:,.0f} ₽<br>"
            "Δ: %{customdata[8]:,.0f} ₽<br>"
            "Упр: %{customdata[6]:,.0f} ₽/ед.<br>"
            "Бух: %{customdata[7]:,.0f} ₽/ед."
        ),
        hovertemplate=_hover_with_prices(),
    )

    _apply_tree_style(fig)

    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Δ упр − бух, ₽",
            tickformat=",.0f",
            title_font=dict(size=11),
            tickfont=dict(size=10),
        )
    )

    _apply_common_layout(
        fig,
        f"Treemap разницы с/с · {date_text}",
        "Размер = упр. с/с, цвет = разница упр. − бух.",
    )

    return _fig_to_html_bytes(
        fig,
        filename=f"stocks_treemap_cost_delta_{_fmt_file_date(report_date)}",
        title=f"Treemap разницы себестоимости · {date_text}",
    )