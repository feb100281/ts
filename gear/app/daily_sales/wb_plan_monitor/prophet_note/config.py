from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class NoteConfig:
    company_name: str
    author_name: str
    author_position: str
    document_title: str


def get_note_config() -> NoteConfig:
    """
    Настройки можно переопределить в settings.py:

        PROPHET_REPORT_COMPANY = "ТРЕНДСЕТТЕР"
        PROPHET_REPORT_AUTHOR = "Дарья Войтенко"
        PROPHET_REPORT_POSITION = "Финансовый аналитик"
    """
    try:
        from django.conf import settings

        company_name = getattr(
            settings,
            "PROPHET_REPORT_COMPANY",
            "ТРЕНДСЕТТЕР",
        )
        author_name = getattr(
            settings,
            "PROPHET_REPORT_AUTHOR",
            "Дарья Войтенко",
        )
        author_position = getattr(
            settings,
            "PROPHET_REPORT_POSITION",
            "",
        )
    except Exception:
        company_name = "ТРЕНДСЕТТЕР"
        author_name = "Дарья Войтенко"
        author_position = ""

    return NoteConfig(
        company_name=company_name,
        author_name=author_name,
        author_position=author_position,
        document_title=(
            "Пояснительная записка "
            "к прогнозу продаж Wildberries"
        ),
    )
