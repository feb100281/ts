from django.contrib import admin

from .models import Product


# Register your models here.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "nm_id",        
        "subject",
        "createdAt",
        "updatedAt",
        "tnved",
        "vat_rate",
        "gender",
        "country",
    )
    search_fields = ("title","nm_id")
    # list_filter = ("date", )
    list_per_page = 25   
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
