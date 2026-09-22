from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
    verbose_name = 'Report Center'

    def ready(self):       
                # Импортируем Dash-приложение при старте Django
                from .app.app import app as rpt_app
