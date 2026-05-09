from django.contrib import admin

from django.utils.html import format_html
from .models import WbProduct

from .models import (
    Lot,
    LotFile,
    UpdDocument,
    UpdDocumentFile,
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
        'number',
        'date',
        'lot',
        'counterparty',
        'contract',
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

# Register your models here.
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