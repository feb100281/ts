from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    Contracts,
    Conditions,
    ContractsTitle,
    ContractItems,
    ContractFiles,
    
)

class ContractItemsInline(admin.TabularInline):
    model = ContractItems
    extra = 0
    fields = ("item",)
    verbose_name = "🧾 Предмет"
    verbose_name_plural = "🧾 Предмет"
    fields = ("item",)
    show_change_link = True

class ConditionsInline(admin.TabularInline):
    model = Conditions
    extra = 1
    verbose_name = "✅ Условие"
    verbose_name_plural = "✅ Условия"



class ContractFilesInline(admin.TabularInline):
    model = ContractFiles
    extra = 0
    verbose_name = "📎 Файл"
    verbose_name_plural = "📎 Файлы"
    show_change_link = True

# @admin.register(Contracts)
# class ContractsAdmin(admin.ModelAdmin):
#     list_display = ("title", "number", "date", "cp")
#     inlines = [ContractItemsInline,ConditionsInline,ContractFilesInline]
    
#     fieldsets = (
#         (
#             "Основное",
#             {"fields": ("title","number","date","owner","cp","pid","date_signed","is_signed")},
#         ),
#         (
#             "Прочее",
#             {
#                 "fields": (
#                     "manager",
#                     "regex",
#                     "defaultcf",
                    
#                 )
#             },
#         ),
        
#     )








@admin.register(Contracts)
class ContractsAdmin(admin.ModelAdmin):
    inlines = (ContractFilesInline, ContractItemsInline, ConditionsInline)

    list_display = ("cp_logo", "cp", "title", "number", "date", "amendment", "files_count")
    list_display_links = ("cp", "number",)   
    list_select_related = ("title", "cp",  "cp__gr", "owner", "manager", "pid",)

    search_fields = ("number", "cp__name", "title__title", "regex")
    search_help_text = "Поиск: номер, контрагент, тип, RegEx"

    list_filter = ("cp", 'title', "owner",  "manager", "is_signed")
    date_hierarchy = "date"
    ordering = ("cp__name", "-date", "number")
    preserve_filters = True
    autocomplete_fields = ("title", "cp", "manager",   "defaultcf")
    
    list_per_page = 25
    
    change_list_template = "admin/contracts/contracts/change_list.html"
    change_form_template = "admin/contracts/contracts/change_form.html"

    fieldsets = (
        (
            format_html('📄 Карточка'),
            {
                "fields": ("title", "number", "date", "cp", "owner", "manager", "is_signed")
            },
        ),
        (
            format_html('⚙️ Автоматизация'),
            {
                "fields": ("regex", "defaultcf"),
                "classes": ("collapse",),
            },
        ),
        (
            format_html('🔗 Связи'),
            {
                "fields": ("pid",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _files_count=Count("files", distinct=True),
            _amendments_count=Count("amendments", distinct=True),
        )
        
        
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "pid":
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                try:
                    obj = Contracts.objects.select_related("cp").get(pk=obj_id)
                    field.queryset = Contracts.objects.filter(cp=obj.cp).order_by("-date")
                    # если хочешь выбирать только “основные” договоры:
                    # field.queryset = field.queryset.filter(pid__isnull=True)
                except Contracts.DoesNotExist:
                    field.queryset = Contracts.objects.none()
            else:
                # форма создания: пока cp не выбран — скрываем варианты
                field.queryset = Contracts.objects.none()

        return field
        
        
    
    @admin.display(description="Лого")
    def cp_logo(self, obj):
        cp = getattr(obj, "cp", None)
        if not cp:
            return "—"

        # 1) приоритет: лого контрагента, 2) fallback: лого группы
        glyph = (cp.logo or "").strip() or (getattr(cp.gr, "logo", "") or "").strip()
        if not glyph:
            return "—"

        outer = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "width:28px;height:28px;border-radius:999px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )
        inner = "font-family:NotoManu;font-size:20px;line-height:1;"

        return format_html(
            '<span style="{}"><span style="{}">{}</span></span>',
            outer, inner, glyph
        )


    @admin.display(description="Доп.согл.")
    def amendment(self, obj):
        if obj.pid_id:
            return "доп.согл."
        n = getattr(obj, "_amendments_count", 0) or 0
        if n:
            return f"Допников: {n}"
        return "—"

    @admin.display(description="Файлы", ordering="_files_count")
    def files_count(self, obj):
        return getattr(obj, "_files_count", 0) or 0
    
    
    
    





        
    
    class Media:
        css = {"all": ("fonts/glyphs.css", "css/admin_overrides.css")}
      
    
    
    



    





@admin.register(ContractsTitle)
class ContractsTitleAdmin(admin.ModelAdmin):
    change_list_template = "admin/contracts/contractstitle/change_list.html"
    change_form_template = "admin/contracts/contractstitle/change_form.html"

    list_display = ("title", "contracts_badge")
    search_fields = ("title",)
    ordering = ("title",)
    preserve_filters = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_contracts_count=Count("contracts", distinct=True))

    @admin.display(description="Договоров", ordering="_contracts_count")
    def contracts_badge(self, obj):
        n = getattr(obj, "_contracts_count", 0) or 0
        if n == 0:
            return admin.utils.format_html(
                '<span style="display:inline-flex;align-items:center;justify-content:center;'
                'min-width:34px;padding:4px 10px;border-radius:999px;'
                'font-size:12px;font-weight:800;'
                'background:rgba(148,163,184,.16);color:#475569;'
                'border:1px solid rgba(148,163,184,.28);">0</span>'
            )
        return admin.utils.format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'min-width:34px;padding:4px 10px;border-radius:999px;'
            'font-size:12px;font-weight:800;'
            'background:rgba(29,78,216,.10);color:#1e3a8a;'
            'border:1px solid rgba(29,78,216,.18);">{}</span>',
            n,
        )