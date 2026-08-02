"""Daily business digest package with lazy UI imports."""

__all__ = ["daily_brief_controls", "register_daily_brief_callbacks"]


def __getattr__(name):
    if name == "daily_brief_controls":
        from .layout import daily_brief_controls
        return daily_brief_controls
    if name == "register_daily_brief_callbacks":
        from .callbacks import register_daily_brief_callbacks
        return register_daily_brief_callbacks
    raise AttributeError(name)
