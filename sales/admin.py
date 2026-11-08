from django.contrib import admin
from django.urls import path, reverse
from .models import ProductGroup, Product, Category, Brand, MVSalesProductData, MVSalesDaily,MVDataMartProduct
from .models import WBDocument
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count, Q
from django.utils.formats import number_format
from django.http import HttpResponse
from django.template.loader import render_to_string
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import Http404
from datetime import date
from sales.dash_apps.dailysales.data import get_month_data, get_ytd_data
from .print_utils import (
    build_mtd_table,     # -> str (готовый HTML таблицы)
    build_ytd_table,     # -> str (готовый HTML таблицы)

)

from django.db.models import F

from .wb_docs import download_wb_document, WBDownloadError
from django.http import HttpResponse

from django.contrib import messages





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
    list_filter = ("subj_root_name", "subj_name", "brand_name")
    list_per_page = 25
    ordering = (
        F("total_revenue").desc(nulls_last=True),
    )
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        response = super().changelist_view(request, extra_context=extra_context)

        # Если это не обычный рендер (например, редирект) — просто возвращаем
        if not hasattr(response, "context_data") or "cl" not in response.context_data:
            return response

        cl = response.context_data["cl"]
        qs = cl.queryset

        # определяем: есть ли фильтры/поиск (т.е. scope = "по фильтру")
        # в Jazzmin/Django фильтры лежат в GET; если только "p" (страница) — это не фильтр
        meaningful_keys = [k for k in request.GET.keys() if k not in ("p", "o")]
        scope = "по фильтрам" if meaningful_keys else "все товары"

        agg = qs.aggregate(
            ytd=Sum("current_year_revenue"),
            cnt=Count("product_id"),
            no_sales=Count("product_id", filter=Q(current_year_revenue__isnull=True) | Q(current_year_revenue__lte=0)),
        )

        ytd = agg["ytd"] or 0
        cnt = agg["cnt"] or 0
        no_sales = agg["no_sales"] or 0

        # форматирование “по-человечески”
        ytd_fmt = number_format(ytd, decimal_pos=0, use_l10n=True, force_grouping=True)
        no_sales_share = (no_sales / cnt) if cnt else 0
        no_sales_share_fmt = f"{no_sales_share:.1%}".replace(".", ",")

        response.context_data.update(
            analytics_scope=scope,
            analytics_ytd_revenue=f"{ytd_fmt} ₽",
            analytics_products_count=cnt,
            analytics_no_sales_count=no_sales,
            analytics_no_sales_share=no_sales_share_fmt if cnt else "—",
        )
        return response
    
    class Media:
        css = {"all": ("css/admin_overrides.css",'css/wide-table.css')}
    
    

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


#----------------------
# Документы WB
#----------------------


@admin.register(WBDocument)
class WBDocumentAdmin(admin.ModelAdmin):
    list_display = (
       "creation_time",
       "category",
       "name",
       "extensions",
    #    "viewed",
       "download_link",
    )
    search_fields = ("category", "name","creation_time")
    list_filter = ("category","creation_time", )
    list_per_page = 25
    ordering = ("-creation_time",)
    date_hierarchy = "creation_time"
    actions = ["print_selected_html"]
    
    readonly_fields = (
        "id",
        "creation_time",
        "category",
        "name",
        "extensions",
        "service_name",
        "viewed",
        "fetched_at",
        "download_button",
    )
    
    fieldsets = (
        ("📄 Документ", {
            "fields": (
                ("category", "name"),
                ("creation_time", "viewed"),
            )
        }),
        ("💾 Файл WB", {
            "fields": (
                "service_name",
                "extensions",
                "download_button",
            )
        }),
        ("⚙️ Техническая информация", {
            "classes": ("collapse",),
            "fields": (
                "id",
                "fetched_at",
            )
        }),
    )

    
    class Media:
        css = {"all": ("css/admin_overrides.css",'css/wide-table.css')}
    
    @admin.action(description="🖨️ Печать")
    def print_selected_html(self, request, queryset):
        docs = queryset.order_by("-creation_time")

        html = render_to_string(
            "admin/sales/wbdocument/wbdocuments_print.html",
            {
                "title": "Документы WB",
                "generated_at": datetime.now(),  
                "rows": docs,                   
                "count": docs.count(),
            },
            request=request,
        )
        return HttpResponse(html)
    
    @admin.display(description="Скачать", ordering=False)
    def download_link(self, obj: WBDocument):
        # extensions у тебя строка типа "zip" или "xml,zip"
        ext = (obj.extensions or "").split(",")[0].strip()
        if not obj.service_name or not ext:
            return "-"

        url = reverse("admin:wb_document_download", args=[obj.pk])
        return format_html('<a class="button" href="{}">Скачать</a>', url)


   
    @admin.display(description="")
    def download_button(self, obj: WBDocument):
        ext = (obj.extensions or "").split(",")[0].strip()
        if not obj.service_name or not ext:
            return format_html(
                '<div style="padding:10px 12px;border-radius:12px;'
                'background:rgba(239,68,68,.06);border:1px solid rgba(239,68,68,.18);'
                'color:#991b1b;font-weight:700;">'
                'Нет service_name или extensions — скачать нельзя'
                '</div>'
            )
        url = reverse("admin:wb_document_download", args=[obj.pk])
        return format_html(
            '<a href="{}" class="button" '
            'style="padding:8px 14px;border-radius:12px;font-weight:700;">'
            'Скачать файл</a>',
            url,
        )

    # 🚫 запретим добавление/изменение (это витрина)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # открыть карточку можно, но редактировать нельзя
        return True

    # def has_delete_permission(self, request, obj=None):
    #     return False

    # --- добавляем url в админку ---
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "download/<int:pk>/",
                self.admin_site.admin_view(self.download_view),
                name="wb_document_download",
            )
        ]
        return custom + urls
        
    # --- добавляем url в админку ---
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "download/<int:pk>/",
                self.admin_site.admin_view(self.download_view),
                name="wb_document_download",
            )
        ]
        return custom + urls

    # --- view скачивания ---
    def download_view(self, request, pk: int):
        obj = self.get_object(request, pk)
        if obj is None:
            self.message_user(request, "Документ не найден", level=messages.ERROR)
            # вернём назад в список
            from django.shortcuts import redirect
            return redirect("..")

        ext = (obj.extensions or "").split(",")[0].strip()
        if not obj.service_name or not ext:
            self.message_user(request, "Нет service_name или extension", level=messages.ERROR)
            from django.shortcuts import redirect
            return redirect("..")

        try:
            filename, content = download_wb_document(obj.service_name, ext)
        except WBDownloadError as e:
            self.message_user(request, f"WB download error: {e}", level=messages.ERROR)
            from django.shortcuts import redirect
            return redirect("..")

        resp = HttpResponse(content, content_type="application/octet-stream")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
    
    # чтобы в шаблоне можно было подсветить “не просмотрено”
    def get_changelist_instance(self, request):
        cl = super().get_changelist_instance(request)
        return cl


    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        response = super().changelist_view(request, extra_context=extra_context)

        if not hasattr(response, "context_data") or "cl" not in response.context_data:
            return response

        cl = response.context_data["cl"]
        qs = cl.queryset

        meaningful_keys = [k for k in request.GET.keys() if k not in ("p", "o")]
        scope = "по фильтрам" if meaningful_keys else "все"

        agg = qs.aggregate(
            docs=Count("id"),
            unviewed=Count("id", filter=Q(viewed=False)),
            categories=Count("category", distinct=True),
        )

        docs = agg["docs"] or 0
        unviewed = agg["unviewed"] or 0
        categories = agg["categories"] or 0

        share = (unviewed / docs) if docs else 0
        share_fmt = f"{share:.1%}".replace(".", ",")

        response.context_data.update(
            analytics_scope=scope,
            analytics_docs_count=number_format(docs, decimal_pos=0, use_l10n=True, force_grouping=True),
            analytics_unviewed_count=number_format(unviewed, decimal_pos=0, use_l10n=True, force_grouping=True),
            analytics_unviewed_share=share_fmt if docs else "—",
            analytics_categories_count=number_format(categories, decimal_pos=0, use_l10n=True, force_grouping=True),
        )

        return response