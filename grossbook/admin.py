from django.contrib import admin
from .models import Manual

# Register your models here.
@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'pid',
        'date',
        'owner',
        'acc',
        'contract',
        'dt',
        'cr',
        'currency',
        
        
    )
    search_fields = ("owner", "contract","acc")
    list_filter = ("contract","acc", )
    list_per_page = 25
    
    
    class Media:
        css = {"all": ("css/admin_overrides.css",'css/wide-table.css')}