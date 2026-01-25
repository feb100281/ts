from django.contrib import admin
from .models import ProductGroup, Product, Category, Brand, MVSalesProductData
from django.utils.html import format_html


# list_display = ("cp_logo", "cp_with_inn", "title", "number_with_id", "date_short", "amendment", "cf_defaults")
#     list_display_links = ("cp_with_inn", "number_with_id",)   
#     list_select_related = ("title", "cp",  "cp__gr", "owner", "manager", "pid",)

#     search_fields = ("number", "cp__name", "title__title", "regex")
#     search_help_text = "Поиск: номер, контрагент, тип, RegEx"

#     list_filter = ( ("cp", RelatedOnlyFieldListFilter), 'title', "owner",  "manager", "is_signed")
#     date_hierarchy = "date"
#     ordering = ("cp__name", "-date", "number")
#     preserve_filters = True
#     autocomplete_fields = ("title", "cp", "manager", )
    
#     list_per_page = 25



# Register your models here.


@admin.register(MVSalesProductData)
class MVSalesProductDataAdmin(admin.ModelAdmin):
    list_display = (
        "imt_name",
        "wb_link",          # ← отдельная колонка
        "imt_id",
        "subj_name",
        "subj_root_name",
        "brand_name",
        "contents",
    )
    search_fields = ("imt_name", "subj_name", "subj_root_name")
    list_filter = ("subj_name", "subj_root_name")
    list_per_page = 25
    ordering = ("imt_name",)

    @admin.display(description="WB")
    def wb_link(self, obj):
        if not obj.nm_id:
            return "—"
        return format_html(
            '<a href="https://www.wildberries.ru/catalog/{}/detail.aspx" '
            'target="_blank" rel="noopener">открыть</a>',
            obj.nm_id,
        )
    fieldsets = (
    (
        "Описание",
        {
            "fields": (
                "description",
                "country",
                "sex",
                "kit",
            ),
        },
    ),
    (
        "Состав и цвета",
        {
            "fields": (
                "composition",
                "nm_colors_names",
            ),
        },
    ),
    (
        "Даты",
        {
            "fields": (
                "create_date",
                "update_date",
            ),
        },
    ),
    (
        "Прочие",
        {
            "fields": (
                "nm_id",
                "photo_count",
                "supplier_id",
                "slug",
            ),
        },
    ),
)
    


# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     list_display = ("name", "group")
#     search_fields = ("name", "group__name",)
#     list_per_page = 25
#     ordering = ("name",)
    
# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ("wb_article", "imt_name_preview", "categories_preview", "brands_preview")
#     search_fields = ("wb_article", "wb_data__data__imt_name", "categories__name", "brands__name")
#     list_per_page = 25
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         return qs.prefetch_related("categories__group", "brands")

#     @admin.display(description="Категории")
#     def categories_preview(self, obj):
#         cats = obj.categories.all()[:2]
#         return ", ".join(str(c) for c in cats)

#     @admin.display(description="Бренды")
#     def brands_preview(self, obj):
#         br = obj.brands.all()[:2]
#         return ", ".join(b.name for b in br)
    
#     @admin.display(description="Название WB")
#     def imt_name_preview(self, obj):
#         return getattr(obj.wb_data, "data", {}).get("imt_name", "—")
    

