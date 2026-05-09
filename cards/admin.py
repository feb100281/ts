from django.contrib import admin
from django.db.models import Count, Q, F
from django.utils.html import format_html
from .models import WbProduct
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    Lot,
    LotFile,
    UpdDocument,
    UpdDocumentFile,
    WbCardRaw,
    WbSizes
)


class LotFileInline(admin.TabularInline):
    model = LotFile
    extra = 0
    fields = (
        'name',
        'file',
        'uploaded_at',
    )
    readonly_fields = (
        'uploaded_at',
    )


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'description',
    )

    search_fields = (
        'name',
        'description',
    )

    inlines = [
        LotFileInline,
    ]


class UpdDocumentFileInline(admin.TabularInline):
    model = UpdDocumentFile
    extra = 0
    fields = (
        'name',
        'file',
        'uploaded_at',
    )
    readonly_fields = (
        'uploaded_at',
    )


@admin.register(UpdDocument)

class UpdDocumentAdmin(admin.ModelAdmin):

    list_display = (
        '__str__',
        'date',
        'lot',
        'counterparty',
        'contract',
        'comment',
        'nm_missing_count',
        'chrt_missing_count',
        'name_mismatch_count',
        'vat_mismatch_count', 
        'dash_link',       
    )
    list_filter = (
        'date',
        'lot',
        'counterparty',
    )
    search_fields = (
        'number',
        'comment',
    )
    autocomplete_fields = (
        'lot',
        'counterparty',
        'contract',
    )
    inlines = [
        UpdDocumentFileInline,
    ]
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            nm_missing=Count(
                'income_lines',
                filter=Q(income_lines__nm__isnull=True),
            ),
            chrt_missing=Count(
                'income_lines',
                filter=Q(income_lines__chrt__isnull=True),
            ),
            name_mismatch=Count(
                'income_lines',
                filter=Q(income_lines__name_match=False),
            ),
            vat_mismatch=Count(
                'income_lines',
                filter=(
                    Q(income_lines__upd_vat_rate__isnull=False)
                    &
                    Q(income_lines__upd_vat_rate__gt=0)
                    &
                    ~Q(income_lines__upd_vat_rate=F('income_lines__card_vat_rate'))
                ),
            ),
        )

    @admin.display(description='Нет nm_id')
    def nm_missing_count(self, obj):
        return obj.nm_missing

    @admin.display(description='Нет chrt_id')
    def chrt_missing_count(self, obj):
        return obj.chrt_missing

    @admin.display(description='Не совпало название')
    def name_mismatch_count(self, obj):
        return obj.name_mismatch

    @admin.display(description='Проблема НДС')
    def vat_mismatch_count(self, obj):
        return obj.vat_mismatch
    
    @admin.display(description='Разбор')
    def dash_link(self, obj):
        url = f"/apps/app/cards_app/?object_id={obj.id}"
        return format_html(
            '<a class="button" href="{}" target="_blank">Открыть</a>',
            url
        )
    class Media:

        css = {
            "all": (
                "css/admin_overrides.css",
                "css/wide-table.css",
            )
        }

 

@admin.register(WbProduct)

class WbProductAdmin(admin.ModelAdmin):

    list_display = (
        'card_id',
        'sa_name',
        'sa_pid',
        'title_short',
        'brand',
        'subject_name',
        'vat_rate',
        'discount_vat',
        'has_parent',
        'sizes_display',
    )

    list_filter = (
        'brand',
        'subject_name',
        'has_parent',
        'discount_vat',
        'origin_country',
        'gender',
    )

    search_fields = (
        'card__nm_id',
        'sa_name',
        'sa_pid',
        'title',
        'alternative_name',
        'tnved',
    )

    readonly_fields = (
        'card',
        'nm_pid',
        'sa_name',
        'sa_pid',
        'title',
        'alternative_name',
        'brand',
        'subject_name',
        'subject_id',
        'has_parent',
        'vat_rate',
        'discount_vat',
        'tnved',
        'gender',
        'origin_country',
        'available_sizes',
        'photo_hq',
        'photo_preview',
        'cert_end_date',
        'wb_created_at',
        'wb_updated_at',
        'updated_at',
    )

    fields = readonly_fields
    ordering = (
        'sa_name',
    )

    def has_add_permission(self, request):

        return False

    def has_delete_permission(self, request, obj=None):

        return False

    def title_short(self, obj):

        if not obj.title:

            return ''

        return obj.title[:80]

    title_short.short_description = 'Название'

    def sizes_display(self, obj):

        return ', '.join(obj.available_sizes or [])

    sizes_display.short_description = 'Размеры'

    def photo_preview(self, obj):

        if not obj.photo_hq:

            return '-'

        return format_html(

            '<img src="{}" style="max-height: 180px; max-width: 180px;" />',

            obj.photo_hq

        )

    photo_preview.short_description = 'Фото'
    
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
                "css/wide-table.css",
                "css/manual_admin_groups.css",
            )
        }
    
    


