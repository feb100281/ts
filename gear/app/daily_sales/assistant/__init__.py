# gear/app/daily_sales/assistant/__init__.py
"""ИИ-помощник (чат) по данным дашборда. Пробная версия."""
from .layout import assistant_widget
from .callbacks import register_assistant_callbacks

__all__ = ["assistant_widget", "register_assistant_callbacks"]
