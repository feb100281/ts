from django.contrib import admin
from django.urls import path, reverse
from .models import ProductGroup, Product, Category, Brand, MVSalesProductData, MVSalesDaily,MVDataMartProduct
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

from django.db.models import F





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
    

@admin.register(MVDataMartProduct)
class MVDataMartProductAdmin(admin.ModelAdmin):
    list_display = (
        "imt_name",
        "wb_link",          # ← отдельная колонка
        "nm_id",
        "subj_name",
        "subj_root_name",
        "brand_name",
        "total_revenue",
        "last_year_revenue",
        "current_year_revenue",
        "tot_rating",
        "lys_rating",
        "cur_rating",
        "first_sale",
        "last_sale",
        "days_interval",
        "sales_days",
        "zeros_days",
        "percent_zero",
        "tot_quant",
        "mean_quant_zeros",
        "monthly_sales_zero",
        "st_dev_with_zeros",
        "cv_zeros",
        "demand_rank_zeros",
    )
    search_fields = ("imt_name", "subj_name", "subj_root_name")
    list_filter = ("subj_root_name","subj_name", )
    list_per_page = 25
    ordering = (
        F("total_revenue").desc(nulls_last=True),
    )
    
    class Media:
        css = {"all": ("css/admin_overrides.css",'css/wide_table.css')}
    
    

    @admin.display(description="WB")
    def wb_link(self, obj):
        if not obj.nm_id:
            return "—"
        return format_html(
            '<a href="https://www.wildberries.ru/catalog/{}/detail.aspx" '
            'target="_blank" rel="noopener">открыть</a>',
            obj.nm_id,
        )
        
    
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        # если тебе не нужен object_id, можно оставить статикой:
        extra_context["iframe_url"] = f"/apps/app/products_app/?object_id={object_id}"

        # если нужно фильтровать даш по конкретной записи/дате:
        # extra_context["iframe_url"] = f"/apps/app/dailysales_app/?object_id={object_id}"

        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )

