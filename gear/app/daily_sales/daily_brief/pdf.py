# gear/app/daily_sales/daily_brief/pdf.py

from __future__ import annotations

from io import BytesIO

from .presentation.pages import (
    build_first_page,
    build_plans_page,
    build_stocks_page,
    build_incidents_page,
)
from .presentation.sections import (
    masthead,
    price_analysis,
    quality,
)
from .presentation.styles import CSS


def build_daily_brief_html(
    payload: dict,
) -> str:
    editorial = payload.get(
        "editorial",
        {},
    )

    return f"""
    <!doctype html>
    <html lang="ru">

    <head>
        <meta charset="utf-8">

        <style>
            {CSS}
        </style>
    </head>

    <body>

        {build_first_page(payload)}

        {build_plans_page(payload)}
        
         {build_stocks_page(payload)}
         
         {build_incidents_page(payload)}

        <!-- =========================================================
             СТРАНИЦА — АНАЛИТИКА ЦЕНЫ И СПРОСА
             ========================================================= -->

        <div class="page">

            {masthead(
                payload,
                "АНАЛИТИЧЕСКИЙ РАЗВОРОТ",
            )}

            <div class="columns analysis-top">

                <div>
                    {quality(payload)}
                </div>

                <div class="editorial-aside">

                    <div class="aside-label">
                        КЛЮЧЕВАЯ МЫСЛЬ
                    </div>

                    <div>
                        {editorial.get(
                            "day_analysis",
                            "",
                        )}
                    </div>

                </div>

            </div>

            {price_analysis(payload)}

            <div class="footer-note">

                <span>
                    Корреляция не доказывает
                    причинно-следственную связь.
                </span>

                <span>
                    Горизонт: 90 дней и 12 месяцев
                </span>

            </div>

        </div>

       

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