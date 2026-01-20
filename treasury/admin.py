from django.contrib import admin, messages
from django.shortcuts import redirect
from .models import BankStatements, CfData, CfSplits
from utils.bsparsers.bsupdater import update_cf_data
from django.utils.safestring import mark_safe

from django.shortcuts import redirect


class CfSplitsInline(admin.StackedInline):
    model = CfSplits
    extra = 1

@admin.register(BankStatements)
class MigrationsAdmin(admin.ModelAdmin):
    list_display = ("__str__","bb", "eb", "uploaded_at", 'file')
    change_form_template = "admin/services/migrations/change_form.html"
    file_path = None
    
    fieldsets = (
        (
            "Файл выписки",
            {"fields": ("file",)},
        ),
        (
            "Информация",
            {
                "fields": (
                    "owner",
                    "ba",
                    "start",
                    "finish",
                    "bb",
                    "eb"
                    
                )
            },
        )
        
    )
    
    

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get('original')
        if obj and obj.file:
            self.file_path = obj.file.path
        return super().render_change_form(request, context, *args, **kwargs)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.method == "POST" and "apply_migration" in request.POST:
            obj = self.get_object(request, object_id)

            if obj and obj.file:
                result = update_cf_data(obj.file.path, obj.pk)   # или object_id
                messages.success(request, mark_safe(result))
            else:
                messages.error(request, "Файл не найден")

            return redirect(request.path)

        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(CfData)
class CfDataAdmin(admin.ModelAdmin):
    list_display = ("date","dt", "cr", "temp", 'cp',"intercompany")
    inlines = [CfSplitsInline,]
    
    
    fieldsets = (
        (
            "Основное",
            {"fields": ("bs","doc_type",'doc_numner',"doc_date","date","temp","dt","cr")},
        ),
        
        (
            "Реффересы",
            {"fields": ("cp_bs_name","cp","cp_final","contract","cfitem")},
        ),        
        
        (
            "Детали",
            {
                "fields": (
                    "ba",
                    "tax_id",                   
                    "payer_account",
                    "reciver_account",
                    "vat_rate",                    
                    "intercompany"
                    
                )
            },
        )
    )
    