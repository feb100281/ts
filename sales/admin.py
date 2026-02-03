from django.contrib import admin
from django.urls import path, reverse
from .models import ProductGroup, Product, Category, Brand, MVSalesProductData, MVSalesDaily
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Q

from django.shortcuts import render, get_object_or_404
from django.http import Http404
from datetime import date
from sales.dash_apps.dailysales.data import get_month_data, get_ytd_data
from .print_utils import (
    build_mtd_table,     # -> str (готовый HTML таблицы)
    build_ytd_table,     # -> str (готовый HTML таблицы)

)




### -----ДНЕВНЫЕ ПРОДАЖИ----- ###
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
        "rtr_ratio",
        "print_link",
    )
    search_fields = ("date",)
    # list_filter = ("date", )
    list_per_page = 25
    date_hierarchy = "date"
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
        
        
    
    # --- Кнопка печати в списке ---
    @admin.display(description="Печать")
    def print_link(self, obj):
        url = reverse(
            f"admin:{MVSalesDaily._meta.app_label}_{MVSalesDaily._meta.model_name}_print",
            args=[obj.pk.isoformat()],
        )
        url = f"{url}?src=list"
        return format_html(
            '<a href="{}" title="Печать отчёта" style="text-decoration:none;font-size:14px;">🖨</a>',
            url,
        )

    # --- Добавляем кастомный url /print/ ---
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<slug:pk>/print/",
                self.admin_site.admin_view(self.print_daily_sales),
                name=f"{MVSalesDaily._meta.app_label}_{MVSalesDaily._meta.model_name}_print",
            ),
        ]
        return my_urls + urls

    # --- View печати ---
    def print_daily_sales(self, request, pk: str):
        # pk приходит как 'YYYY-MM-DD'
        try:
            d = date.fromisoformat(pk)
        except ValueError:
            raise Http404("Invalid date format. Expected YYYY-MM-DD")

        obj = get_object_or_404(MVSalesDaily, pk=d)

        # сырые данные (как в dash)
        df_mtd_raw = get_month_data(d)
        df_ytd_raw = get_ytd_data(d)

        # таблицы (в print_utils делай красивый HTML и стили)
        table_mtd = build_mtd_table(df_mtd_raw)
        table_ytd = build_ytd_table(df_ytd_raw)




        context = {
            "obj": obj,
            "report_date": d,
            "table_mtd_html": table_mtd["html"],
            "table_ytd_html": table_ytd["html"],
            "src": request.GET.get("src", "list"),
        }
        return render(request, "admin/daily_sales_print.html", context)
    
    
    
    
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # если тебе не нужен object_id, можно оставить статикой:
        extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        # если нужно фильтровать даш по конкретной записи/дате:
        # extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )
    


### -----НОМЕНКЛАТУРЫ----- ###
@admin.register(MVSalesProductData)
class MVSalesProductDataAdmin(admin.ModelAdmin):
    list_display = (
        "imt_name",
        "wb_link",         
        "imt_id",
        "subj_name",
        "subj_root_name",
        "brand_name",
        "contents",
    )
    search_fields = ("imt_name", "subj_name", "subj_root_name")
    list_filter = ("subj_name", "subj_root_name", 'brand_name',)
    list_per_page = 25
    ordering = ("imt_name",)
    readonly_fields = ("create_date",
                        "update_date",
                         "nm_id",
                        "photo_count",
                        "supplier_id",
                        "slug",
                         "description",
                        "country",
                        "sex",
                        "kit",
                        "composition",
                        "nm_colors_names",)
    
    
    
    # тут считаем мини-метрики по ТЕКУЩЕЙ выборке (учитывает фильтры/поиск)
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        try:
            cl = response.context_data["cl"]
            qs = cl.queryset

            brands_cnt = (
                qs.exclude(Q(brand_name__isnull=True) | Q(brand_name=""))
                .values("brand_name").distinct().count()
            )
            groups_cnt = (
                qs.exclude(Q(subj_root_name__isnull=True) | Q(subj_root_name=""))
                .values("subj_root_name").distinct().count()
            )
            cats_cnt = (
                qs.exclude(Q(subj_name__isnull=True) | Q(subj_name=""))
                .values("subj_name").distinct().count()
            )
            wb_links_cnt = (
                qs.exclude(Q(nm_id__isnull=True) | Q(nm_id=""))
                .count()
            )

            response.context_data["mini_metrics"] = {
                "brands_cnt": brands_cnt,
                "groups_cnt": groups_cnt,
                "cats_cnt": cats_cnt,
                "wb_links_cnt": wb_links_cnt,
            }
        except Exception:
            # чтобы ничего не ломалось даже если где-то ошибка
            response.context_data["mini_metrics"] = None

        return response
    
    

    @admin.display(description="WB")
    def wb_link(self, obj):
        if not obj.nm_id:
            return "—"
        return format_html(
            '<a href="https://www.wildberries.ru/catalog/{}/detail.aspx" '
            'target="_blank" rel="noopener">открыть</a>',
            obj.nm_id,
        )
        
        
    
    
    class Media:
        css = {"all": ("css/admin_overrides.css",)}
    


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
    

