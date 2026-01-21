from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from django.db.models import Count, Prefetch
from django.utils.html import format_html

from .models import (
    Contracts,
    Conditions,
    ContractsTitle,
    ContractItems,
    ContractFiles,
    CfItemAuto,
    
)

# class CfItemAutoInline(admin.TabularInline):
#     model = CfItemAuto
#     extra = 0

class CfItemAutoInline(admin.StackedInline):
    model = CfItemAuto
    extra = 0
    fields = ("regex", "defaultcfdt", "defaultcfcr")
    # template = "admin/contracts/inlines/cfitemauto_stacked_inline.html"  # <-- УБРАТЬ
    verbose_name = "⚙️ Автоматизация"
    verbose_name_plural = "⚙️ Автоматизация"


    
    

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
    inlines = (ContractFilesInline, ContractItemsInline, ConditionsInline,CfItemAutoInline)

    list_display = ("cp_logo", "cp_with_inn", "title", "number", "date_short", "amendment", "cf_defaults")
    list_display_links = ("cp_with_inn", "number",)   
    list_select_related = ("title", "cp",  "cp__gr", "owner", "manager", "pid",)

    search_fields = ("number", "cp__name", "title__title", "regex")
    search_help_text = "Поиск: номер, контрагент, тип, RegEx"

    list_filter = ( ("cp", RelatedOnlyFieldListFilter), 'title', "owner",  "manager", "is_signed")
    date_hierarchy = "date"
    ordering = ("cp__name", "-date", "number")
    preserve_filters = True
    autocomplete_fields = ("title", "cp", "manager",)
    
    list_per_page = 25
    
    change_list_template = "admin/contracts/contracts/change_list.html"
    change_form_template = "admin/contracts/contracts/change_form.html"

    fieldsets = (
        (
            format_html('📄 Карточка'),
            {
                "fields": ("title", "number", "date", "cp", "owner", "manager", "is_signed","regex",)
            },
        ),
        # (
        #     format_html('⚙️ Автоматизация'),
        #     {
        #         "fields": ("regex", "defaultcf", "defaultcfcr"),
        #         "classes": ("collapse",),
        #     },
        # ),
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
        qs = qs.select_related("title", "cp", "cp__gr", "owner", "manager", "pid").annotate(
            _files_count=Count("files", distinct=True),
            _amendments_count=Count("amendments", distinct=True),
        ).prefetch_related(
            Prefetch(
                "cfitemauto_set",
                queryset=CfItemAuto.objects.select_related("defaultcfdt", "defaultcfcr"),
                to_attr="_cf_auto",
            )
        )
        return qs

    
    
    @admin.display(description="Контрагент", ordering="cp__name")
    def cp_with_inn(self, obj):
        cp = obj.cp
        if not cp:
            return "—"

        return format_html(
            '{}<br><span style="font-size:11px; line-height:1.2; color:#94a3b8;">ИНН: {}</span>',
            cp.name,
            cp.tax_id,
        )
    
    @admin.display(description="Дата договора", ordering="date")
    def date_short(self, obj):
        if not obj.date:
            return "—"

        months = {
            1: "янв", 2: "фев", 3: "мар", 4: "апр",
            5: "май", 6: "июн", 7: "июл", 8: "авг",
            9: "сент", 10: "окт", 11: "ноя", 12: "дек",
        }

        d = obj.date
        return f"{d.day} {months[d.month]} {d.year}"
    
    
    @admin.display(description="CF по умолч.", ordering=None)
    def cf_defaults(self, obj):
        # берём первую запись автоматизации (обычно она одна на договор)
        auto = (getattr(obj, "_cf_auto", None) or [])
        auto = auto[0] if auto else None

        dt = getattr(auto, "defaultcfdt", None) if auto else None
        cr = getattr(auto, "defaultcfcr", None) if auto else None

        dt_txt = str(dt) if dt else "—"
        cr_txt = str(cr) if cr else "—"

        # маленький светло-серый текст, две строки
        return format_html(
            '<div style="font-size:11px; line-height:1.25; color:#94a3b8;">'
            '<div><span style="font-weight:700; color:#cbd5e1;">Дт:</span> {}</div>'
            '<div><span style="font-weight:700; color:#cbd5e1;">Кт:</span> {}</div>'
            '</div>',
            dt_txt,
            cr_txt,
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
            "width:28px;height:28px;border-radius:6px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )
        inner = "font-family:NotoManu;font-size:20px;line-height:1;"

        return format_html(
            '<span style="{}"><span style="{}">{}</span></span>',
            outer, inner, glyph
        )


    @admin.display(description="Доп.согл.", ordering="_amendments_count")
    def amendment(self, obj):
        # если текущая запись — допник
        if obj.pid_id:
            return format_html(
                '<span style="display:inline-flex;align-items:center;justify-content:center;'
                'padding:4px 10px;border-radius:999px;'
                'font-size:11px;font-weight:900;'
                'background:rgba(148,163,184,.16);color:#475569;'
                'border:1px solid rgba(148,163,184,.28);">доп.согл.</span>'
            )

        n = getattr(obj, "_amendments_count", 0) or 0
        if not n:
            return "—"

        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'min-width:34px;padding:4px 10px;border-radius:999px;'
            'font-size:11px;font-weight:900;'
            'background:rgba(14,165,233,.10);color:#075985;'
            'border:1px solid rgba(14,165,233,.18);">+{} док.</span>',
            n
        )


    @admin.display(description="Файлы", ordering="_files_count")
    def files_count(self, obj):
        return getattr(obj, "_files_count", 0) or 0
    
    
    
    class Media:
        css = {"all": ("fonts/glyphs.css", "css/admin_overrides.css",  )}
      
    
    
    



    





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
                'min-width:34px;padding:4px 10px;border-radius:6px;'
                'font-size:12px;font-weight:800;'
                'background:rgba(148,163,184,.16);color:#475569;'
                'border:1px solid rgba(148,163,184,.28);">0</span>'
            )
        return admin.utils.format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'min-width:34px;padding:4px 10px;border-radius:6px;'
            'font-size:12px;font-weight:800;'
            'background:rgba(29,78,216,.10);color:#1e3a8a;'
            'border:1px solid rgba(29,78,216,.18);">{}</span>',
            n,
        )
    
    
    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",  
            )
        }