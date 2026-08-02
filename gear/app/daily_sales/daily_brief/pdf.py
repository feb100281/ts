# gear/app/daily_sales/daily_brief/pdf.py

from __future__ import annotations

from io import BytesIO

from .presentation.pages import build_first_page
from .presentation.sections import (
    half_year,
    incidents_section,
    masthead,
    plan_block,
    price_analysis,
    quality,
    recommendations,
    stock_geography,
    stock_summary,
)
from .presentation.styles import CSS


def build_daily_brief_html(
    payload: dict,
) -> str:
    editorial = payload.get(
        "editorial",
        {},
    )

    incidents = payload.get(
        "incidents",
        {},
    )

    incident_html = (
        incidents_section(payload)
        if (
            incidents.get("available")
            and incidents.get("events")
        )
        else ""
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

        <!-- =========================================================
             СТРАНИЦА 2 — АНАЛИТИКА ЦЕНЫ И СПРОСА
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

        <!-- =========================================================
             СТРАНИЦА 3 — ПЛАН
             ========================================================= -->

        <div class="page">
            {masthead(
                payload,
                "ПЛАНОВЫЙ РАЗВОРОТ",
            )}

            <div class="columns page-columns">
                <div>
                    {plan_block(payload)}
                </div>

                <div>
                    {half_year(payload)}
                    {recommendations(payload)}
                </div>
            </div>

            <div class="big-quote">
                {editorial.get(
                    "closing",
                    "",
                )}
            </div>

            <div class="footer-note">
                <span>
                    План к дате учитывает распределение
                    месячного плана.
                </span>

                <span>
                    {payload.get(
                        "generated_at",
                        "",
                    )}
                </span>
            </div>
        </div>

        <!-- =========================================================
             СТРАНИЦА 4 — ОСТАТКИ
             ========================================================= -->

        <div class="page">
            {masthead(
                payload,
                "ТОВАРНЫЙ РАЗВОРОТ",
            )}

            {stock_summary(payload)}

            {stock_geography(payload)}

            {incident_html}

            <div class="footer-note">
                <span>
                    Названия регионов синхронизированы с
                    inventories.reporting.map.map_config.
                </span>

                <span>
                    Источник: dashboard остатков
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