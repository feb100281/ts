from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sales"
    verbose_name = "Продажи"
    
    def ready(self):       
        # Импортируем Dash-приложение при старте Django
        from .dash_apps.dailysales.app import app as dailysales_app
