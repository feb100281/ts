from django.apps import AppConfig


class MacroConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "macro"
    verbose_name = "Макропоказатели"
    
    def ready(self):
        # Импортируем Dash-приложение при старте Django
        from macro.calapp import app as cal_app  # <- здесь регистрируется Dash
