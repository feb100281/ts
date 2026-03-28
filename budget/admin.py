from django.contrib import admin
from .models import BudgetVersion
from django.db import models

from jsoneditor.forms import JSONEditor

# Register your models here.
@admin.register(BudgetVersion)
class BudgetVersionAdmin(admin.ModelAdmin):
    

    list_display = (
        "number",
        "budget_type",
        "date_from",
        "date_to",
        "description",
        # "description_short",
    )
    

    formfield_overrides = {
        models.JSONField: {"widget": JSONEditor},
    }

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }