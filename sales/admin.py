from django.contrib import admin
from .models import ProductGroup, Product, Category, Brand, MVSalesProductData, MVSalesDaily
from django.utils.html import format_html




# Register your models here.
@admin.register(MVSalesDaily)
class MVSalesDailyAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "amount",         
        "revenue",
        "comission",
        "quant",
        "sales",
        "rtr",
        "rtr_ratio"
    )
    search_fields = ("date",)
    list_filter = ("date", )
    list_per_page = 25
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
    
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # если тебе не нужен object_id, можно оставить статикой:
        extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        # если нужно фильтровать даш по конкретной записи/дате:
        # extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )
    



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
    

