from django.apps import AppConfig


class CardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cards"
    verbose_name = "УПД и приходы"

    def ready(self):       
            # Импортируем Dash-приложение при старте Django
            from .upd_app.app import app as cards_app
            