# gear/app/daily_sales/commercial_review/report.py
"""
Сборка PDF коммерческого обзора.

Порядок страниц: сначала ответ, потом доказательства.
Первые три страницы читает руководитель, остальные —
коммерческая команда.

Каждая страница собирается отдельно и в своей «песочнице»:
если один раздел упал, отчёт всё равно выпускается, а на месте
этого раздела стоит честная страница с текстом ошибки. Отдавать
пустой экран вместо шестнадцати рабочих страниц — плохой обмен,
но и прятать сбой нельзя: иначе он живёт месяцами.
"""

from __future__ import annotations

import logging

from io import BytesIO

from . import pages
from .analysis import build_findings, headline
from .blocks import callout, page
from .formats import escape
from .styles import CSS


logger = logging.getLogger(__name__)


def _safe(title, chapter, builder, *args, **kwargs) -> str:
    try:
        return builder(*args, **kwargs)

    except Exception as error:
        logger.exception("Коммерческий обзор: раздел «%s» не собрался", title)

        return page(
            chapter,
            title,
            "",
            callout(
                "Раздел не собрался",
                (
                    "<b>Этот раздел не удалось построить, остальной "
                    "отчёт собран полностью.</b><br>"
                    f"{escape(type(error).__name__)}: "
                    f"{escape(error)}"
                ),
                plain=True,
            ),
        )


def build_commercial_review_html(payload: dict, fbs=None) -> str:
    # Движок выводов трогает много полей сразу, поэтому он тоже
    # под защитой: без выводов отчёт беднее, но цифры на месте.
    try:
        findings = build_findings(payload, fbs=fbs)
    except Exception:
        logger.exception("Коммерческий обзор: движок выводов не отработал")
        findings = []

    try:
        headline_text = headline(payload, findings)
    except Exception:
        logger.exception("Коммерческий обзор: главная мысль не собралась")
        headline_text = (
            "Сводка собрана, но главный вывод сформулировать "
            "не удалось — смотрите разделы по показателям."
        )

    blocks = [
        ("Обложка", "Главное",
         pages.cover, (payload, findings, headline_text)),
        ("Содержание", "Как читать этот отчёт",
         pages.contents, (payload,)),
        ("Главное на одной странице", "Главное",
         pages.summary_page, (payload, findings, headline_text)),
        ("Выручка: как она менялась", "Выручка",
         pages.revenue_dynamics_page, (payload,)),
        ("Выручка: почему она изменилась", "Выручка",
         pages.revenue_reasons_page, (payload, findings)),
        ("Цена, количество и скидка WB", "Цена",
         pages.price_page, (payload,)),
        ("Бренды: цена против количества", "Цена",
         pages.brands_page, (payload, findings)),
        ("Бренды: кто даёт оборот, а кто прибыль", "Структура",
         pages.brand_profit_page, (payload, findings)),
        ("Категории: кто даёт оборот, а кто прибыль", "Структура",
         pages.category_profit_page, (payload, findings)),
        ("План месяца", "План",
         pages.plan_month_page, (payload, findings)),
        ("План года и полугодия", "План",
         pages.plan_year_page, (payload,)),
        ("Прогноз до конца года", "Прогноз",
         pages.forecast_page, (payload,)),
        ("Финансовый результат", "Финансовый результат",
         pages.finance_page, (payload, findings)),
        ("Анализ расходов WB", "Расходы WB",
         pages.wb_expenses_page, (payload,)),
        ("Запасы: структура и покрытие", "Запасы",
         pages.stocks_page, (payload,)),
        ("Запасы: зона риска", "Запасы",
         pages.stock_risk_page, (payload, findings)),
        ("Заказы FBS: сборка и сроки", "Заказы FBS",
         pages.fbs_assembly_page, (fbs,)),
        ("Заказы FBS: склады, поставки и товары", "Заказы FBS",
         pages.fbs_logistics_page, (fbs, findings)),
        ("Выводы и рекомендации", "Выводы",
         pages.findings_page, (payload, findings)),
        ("Методика", "Методика",
         pages.methodology_page, (payload, fbs)),
    ]

    body = "".join(
        _safe(title, chapter, builder, *arguments)
        for title, chapter, builder, arguments in blocks
    )

    return f"""<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>ТРЕНДСЕТТЕР · Коммерческий обзор</title>
    <style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_commercial_review_pdf(payload: dict, fbs=None) -> bytes:
    try:
        from weasyprint import HTML

    except ImportError as exc:
        raise RuntimeError(
            "Для PDF нужен WeasyPrint: pip install weasyprint"
        ) from exc

    buffer = BytesIO()

    HTML(
        string=build_commercial_review_html(payload, fbs=fbs),
    ).write_pdf(buffer)

    return buffer.getvalue()
