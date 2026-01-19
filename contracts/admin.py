from django.contrib import admin

# Register your models here.
from .models import (
    Contracts,
    Conditions,
    ContractsTitle,
    ContractItems,
    ContractFiles,
    
)

class ContractItemsInline(admin.TabularInline):
    model = ContractItems
    extra = 1
    fields = ("item",)

class ConditionsInline(admin.TabularInline):
    model = Conditions
    extra = 1

class ContractFilesInline(admin.TabularInline):
    model = ContractFiles
    extra = 1

@admin.register(Contracts)
class ContractsAdmin(admin.ModelAdmin):
    list_display = ("title", "number", "date", "cp")
    inlines = [ContractItemsInline,ConditionsInline,ContractFilesInline]
    
    fieldsets = (
        (
            "Основное",
            {"fields": ("title","number","date","owner","cp","pid","date_signed","is_signed")},
        ),
        (
            "Прочее",
            {
                "fields": (
                    "manager",
                    "regex",
                    "defaultcf",
                    
                )
            },
        ),
        
    )
    

@admin.register(ContractsTitle)
class ContractsTitleAdmin(admin.ModelAdmin):
    list_display = ("title",)