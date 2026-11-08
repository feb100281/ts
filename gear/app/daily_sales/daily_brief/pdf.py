# gear/app/daily_sales/daily_brief/pdf.py


# убрала страницу там где география      {build_stocks_page(payload)}
from __future__ import annotations

from io import BytesIO

from .presentation.pages import (
    build_financial_page,
    build_first_page,
    build_incidents_page,
    build_plans_page,
    build_stocks_page,
    build_stock_balance_page,
    build_demand_page,
    build_sales_dynamics_page,
    build_price_page,
)

from .presentation.styles import CSS
from .presentation.stock_style import (
    STOCK_BALANCE_CSS,
)


def build_daily_brief_html(
    payload: dict,
) -> str:

    return f"""
    <!doctype html>
    <html lang="ru">

    <head>
        <meta charset="utf-8">

        <style>
            {CSS}
            {STOCK_BALANCE_CSS}
        </style>
    </head>

    <body>

        {build_first_page(payload)}

        {build_sales_dynamics_page(payload)}

        {build_price_page(payload)}

        {build_financial_page(payload)}

        {build_plans_page(payload)}


        {build_stock_balance_page(payload)}

        {build_incidents_page(payload)}

    </body>
    </html>
    """


def build_daily_brief_pdf(
    payload: dict,
) -> bytes:

    try:
        from weasyprint import HTML

    except ImportError as exc:
        raise RuntimeError(
            "Для PDF установите WeasyPrint: "
            "pip install weasyprint"
        ) from exc

    html_text = build_daily_brief_html(
        payload
    )

    buffer = BytesIO()

    HTML(
        string=html_text,
    ).write_pdf(
        buffer
    )

    return buffer.getvalue()