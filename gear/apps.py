from django.apps import AppConfig


class GearConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gear"
    verbose_name = "Dash Board"
    
    
    def ready(self):       
            # Импортируем Dash-приложение при старте Django
            from .app.segement_sales import app as segments_sales_app
            from .app.daily_sales import app as dayly_sales_app
