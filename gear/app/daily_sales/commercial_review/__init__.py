"""Новый коммерческий обзор: отдельный отчёт и своя кнопка."""

__all__ = [
    "commercial_review_controls",
    "register_commercial_review_callbacks",
]


def __getattr__(name):
    if name == "commercial_review_controls":
        from .layout import commercial_review_controls
        return commercial_review_controls

    if name == "register_commercial_review_callbacks":
        from .callbacks import register_commercial_review_callbacks
        return register_commercial_review_callbacks

    raise AttributeError(name)
