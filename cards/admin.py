# cards/admin.py

import os

from django.contrib import admin
from django.db.models import Count, Q, F, Sum
from django.utils.html import format_html

from .models import (
    Lot,
    LotFile,
    UpdDocument,
    UpdDocumentFile,
    WbProduct,
)


class LotFileInline(admin.TabularInline):
    model = LotFile
    extra = 0
    fields = ('name', 'file_link', 'uploaded_at')
    readonly_fields = ('file_link', 'uploaded_at')

    def file_link(self, obj):
        if obj.file:
            url = obj.file.url
            return format_html(
                '<a href="{}" target="_blank">📄 {}</a>',
                url,
                os.path.basename(obj.file.name)
            )
        return '-'

    file_link.short_description = 'Файл'


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

    fields = ('name', 'file', 'file_link', 'uploaded_at')
    readonly_fields = ('file_link', 'uploaded_at')

    def file_link(self, obj):
        if obj and obj.file:
            return format_html(
                '<a href="{}" target="_blank" style="background:#f1f5f9; padding:4px 8px; border-radius:4px; text-decoration:none;">📄 Просмотр</a>',
                obj.file.url
            )
        return '-'

    file_link.short_description = 'Файл'
    
    

class UpdProblemFilter(admin.SimpleListFilter):
    title = 'Проблемы в УПД'
    parameter_name = 'upd_problem'

    def lookups(self, request, model_admin):
        return (
            ('nm_missing', 'Нет nm_id'),
            ('chrt_missing', 'Нет chrt_id / размер'),
            ('name_mismatch', 'Не совпало название'),
            ('vat_mismatch', 'Проблема НДС'),
            ('has_any_problem', 'Есть любая проблема'),
            ('no_problem', 'Без проблем'),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if value == 'nm_missing':
            return queryset.filter(nm_missing__gt=0)

        if value == 'chrt_missing':
            return queryset.filter(chrt_missing__gt=0)

        if value == 'name_mismatch':
            return queryset.filter(name_mismatch__gt=0)

        if value == 'vat_mismatch':
            return queryset.filter(vat_mismatch__gt=0)

        if value == 'has_any_problem':
            return queryset.filter(
                Q(nm_missing__gt=0)
                | Q(chrt_missing__gt=0)
                | Q(name_mismatch__gt=0)
                | Q(vat_mismatch__gt=0)
            )

        if value == 'no_problem':
            return queryset.filter(
                nm_missing=0,
                chrt_missing=0,
                name_mismatch=0,
                vat_mismatch=0,
            )

        return queryset


@admin.register(UpdDocument)
class UpdDocumentAdmin(admin.ModelAdmin):
    change_list_template = "admin/cards/upddocument/change_list.html"
    date_hierarchy = "date"

    list_display = (
       'counterparty_short',
        # '__str__',
        'upd_link',
        'lot',
        'total_amount_vatadd_display',
        'total_qty_display',
        'lines_count_display',
        'nm_missing_count',
        'chrt_missing_count',
        # 'name_mismatch_count',
        'vat_mismatch_count',
        'dash_link',
    )
    
    list_display_links = (
        'counterparty_short',
        'upd_link',
    )

    list_filter = (
        UpdProblemFilter,

        'lot',
        'counterparty',
    )

    search_fields = (
        'number',
        'comment',
        'income_lines__upd_sa_name',
        'income_lines__upd_title',
        'income_lines__nm__nm_id',
    )

    autocomplete_fields = (
        'lot',
        'counterparty',
        'contract',
    )

    inlines = [
        UpdDocumentFileInline,
    ]

    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)

    #     return qs.annotate(
    #         total_amount_vatadd=Sum('income_lines__upd_amount_vatadd'),
    #         total_qty=Sum('income_lines__upd_qty'),
    #         lines_count=Count('income_lines', distinct=True),

    #         nm_missing=Count(
    #             'income_lines',
    #             filter=Q(income_lines__nm__isnull=True),
    #             distinct=True,
    #         ),
    #         chrt_missing=Count(
    #             'income_lines',
    #             filter=Q(income_lines__chrt__isnull=True),
    #             distinct=True,
    #         ),
    #         name_mismatch=Count(
    #             'income_lines',
    #             filter=Q(income_lines__name_match=False),
    #             distinct=True,
    #         ),
    #         vat_mismatch=Count(
    #             'income_lines',
    #             filter=(
    #                 Q(income_lines__upd_vat_rate__isnull=False)
    #                 & Q(income_lines__upd_vat_rate__gt=0)
    #                 & ~Q(income_lines__upd_vat_rate=F('income_lines__card_vat_rate'))
    #             ),
    #             distinct=True,
    #         ),
    #     )

    # def changelist_view(self, request, extra_context=None):
    #     cl = self.get_changelist_instance(request)
    #     full_queryset = cl.get_queryset(request)

    #     total_stats = full_queryset.aggregate(

    #         total_amount_vatadd=Sum(
    #             'income_lines__upd_amount_vatadd'
    #         ),

    #         total_qty=Sum(
    #             'income_lines__upd_qty'
    #         ),

    #         total_lines_count=Count(
    #             'income_lines'
    #         ),

    #         total_nm_missing=Count(
    #             'income_lines',
    #             filter=Q(income_lines__nm__isnull=True)
    #         ),

    #         total_chrt_missing=Count(
    #             'income_lines',
    #             filter=Q(income_lines__chrt__isnull=True)
    #         ),

    #         total_name_mismatch=Count(
    #             'income_lines',
    #             filter=Q(income_lines__name_match=False)
    #         ),

    #         total_vat_mismatch=Count(
    #             'income_lines',
    #             filter=(
    #                 Q(income_lines__upd_vat_rate__isnull=False)
    #                 &
    #                 Q(income_lines__upd_vat_rate__gt=0)
    #                 &
    #                 ~Q(
    #                     income_lines__upd_vat_rate=F(
    #                         'income_lines__card_vat_rate'
    #                     )
    #                 )
    #             )
    #         ),
    #     )

    #     extra_context = extra_context or {}

    #     extra_context['total_stats'] = {
    #         'amount_vatadd': total_stats['total_amount_vatadd'] or 0,
    #         'qty': total_stats['total_qty'] or 0,
    #         'lines_count': total_stats['total_lines_count'] or 0,
    #         'nm_missing': total_stats['total_nm_missing'] or 0,
    #         'chrt_missing': total_stats['total_chrt_missing'] or 0,
    #         'name_mismatch': total_stats['total_name_mismatch'] or 0,
    #         'vat_mismatch': total_stats['total_vat_mismatch'] or 0,
    #     }

    #     return super().changelist_view(
    #         request,
    #         extra_context=extra_context
    #     )
    
    
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.annotate(
            total_amount_vatadd=Sum('income_lines__upd_amount_vatadd'),
            total_qty=Sum('income_lines__upd_qty'),
            lines_count=Count('income_lines', distinct=True),

            nm_missing=Count(
                'income_lines',
                filter=Q(income_lines__nm__isnull=True),
                distinct=True,
            ),
            # Сумма по позициям без nm_id
            nm_missing_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=Q(income_lines__nm__isnull=True),
            ),
            
            chrt_missing=Count(
                'income_lines',
                filter=Q(income_lines__chrt__isnull=True),
                distinct=True,
            ),
            # Сумма по позициям без chrt_id
            chrt_missing_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=Q(income_lines__chrt__isnull=True),
            ),
            
            name_mismatch=Count(
                'income_lines',
                filter=Q(income_lines__name_match=False),
                distinct=True,
            ),
            # Сумма по позициям с несовпадением названия
            name_mismatch_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=Q(income_lines__name_match=False),
            ),
            
            vat_mismatch=Count(
                'income_lines',
                filter=(
                    Q(income_lines__upd_vat_rate__isnull=False)
                    & Q(income_lines__upd_vat_rate__gt=0)
                    & ~Q(income_lines__upd_vat_rate=F('income_lines__card_vat_rate'))
                ),
                distinct=True,
            ),
            # Сумма по позициям с проблемой НДС
            vat_mismatch_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=(
                    Q(income_lines__upd_vat_rate__isnull=False)
                    & Q(income_lines__upd_vat_rate__gt=0)
                    & ~Q(income_lines__upd_vat_rate=F('income_lines__card_vat_rate'))
                ),
            ),
        )

    def changelist_view(self, request, extra_context=None):
        cl = self.get_changelist_instance(request)
        full_queryset = cl.get_queryset(request)

        total_stats = full_queryset.aggregate(
            total_amount_vatadd=Sum('income_lines__upd_amount_vatadd'),
            total_qty=Sum('income_lines__upd_qty'),
            total_lines_count=Count('income_lines'),
            
            total_nm_missing=Count(
                'income_lines',
                filter=Q(income_lines__nm__isnull=True)
            ),
            total_nm_missing_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=Q(income_lines__nm__isnull=True)
            ),
            
            total_chrt_missing=Count(
                'income_lines',
                filter=Q(income_lines__chrt__isnull=True)
            ),
            total_chrt_missing_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=Q(income_lines__chrt__isnull=True)
            ),
            
            total_name_mismatch=Count(
                'income_lines',
                filter=Q(income_lines__name_match=False)
            ),
            total_name_mismatch_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=Q(income_lines__name_match=False)
            ),
            
            total_vat_mismatch=Count(
                'income_lines',
                filter=(
                    Q(income_lines__upd_vat_rate__isnull=False)
                    & Q(income_lines__upd_vat_rate__gt=0)
                    & ~Q(income_lines__upd_vat_rate=F('income_lines__card_vat_rate'))
                )
            ),
            total_vat_mismatch_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=(
                    Q(income_lines__upd_vat_rate__isnull=False)
                    & Q(income_lines__upd_vat_rate__gt=0)
                    & ~Q(income_lines__upd_vat_rate=F('income_lines__card_vat_rate'))
                )
            ),
        )

        total_amount = total_stats['total_amount_vatadd'] or 0
        
        extra_context = extra_context or {}
        extra_context['total_stats'] = {
            'amount_vatadd': total_amount,
            'qty': total_stats['total_qty'] or 0,
            'lines_count': total_stats['total_lines_count'] or 0,
            
            'nm_missing': total_stats['total_nm_missing'] or 0,
            'nm_missing_amount': total_stats['total_nm_missing_amount'] or 0,
            'nm_missing_percent': self._calc_percent(total_stats['total_nm_missing_amount'], total_amount),
            
            'chrt_missing': total_stats['total_chrt_missing'] or 0,
            'chrt_missing_amount': total_stats['total_chrt_missing_amount'] or 0,
            'chrt_missing_percent': self._calc_percent(total_stats['total_chrt_missing_amount'], total_amount),
            
            'name_mismatch': total_stats['total_name_mismatch'] or 0,
            'name_mismatch_amount': total_stats['total_name_mismatch_amount'] or 0,
            'name_mismatch_percent': self._calc_percent(total_stats['total_name_mismatch_amount'], total_amount),
            
            'vat_mismatch': total_stats['total_vat_mismatch'] or 0,
            'vat_mismatch_amount': total_stats['total_vat_mismatch_amount'] or 0,
            'vat_mismatch_percent': self._calc_percent(total_stats['total_vat_mismatch_amount'], total_amount),
        }

        return super().changelist_view(request, extra_context=extra_context)
    
    @staticmethod
    def _calc_percent(amount, total):
        """Расчет процента от общей суммы"""
        if not total or total == 0:
            return 0
        return round((amount or 0) / total * 100, 1)
    
    
    @admin.display(description='Контрагент', ordering='counterparty__name')
    def counterparty_short(self, obj):

        if not obj.counterparty:
            return '-'

        name = str(obj.counterparty)

        if ' (ИНН:' in name:
            name = name.split(' (ИНН:')[0]

        return name

    @staticmethod
    def format_money(value):
        value = value or 0
        return f'{value:,.2f}'.replace(',', ' ') + ' ₽'
    
    @admin.display(description='УПД', ordering='number')
    def upd_link(self, obj):

        return format_html(
            '''
            <div style="line-height:1.15;">
                
                <div style="
                    font-size:14px;
                    font-weight:700;
                    color:#0f172a;
                ">
                    № {} 
                    <span style="
                        color:#6b7280;
                        font-weight:600;
                        font-size:12px;
                    ">
                        (id: {})
                    </span>
                </div>

                <div style="
                    margin-top:3px;
                    font-size:11px;
                    color:#64748b;
                    font-weight:500;
                ">
                    от {}
                </div>

            </div>
            ''',
            obj.number,
            obj.id,
            obj.date.strftime("%d.%m.%Y")
        )


    @staticmethod
    def format_number(value):
        value = value or 0
        return f'{value:,.2f}'.replace(',', ' ')

    def problem_cell(self, value):
        value = value or 0

        if value > 0:
            return format_html(
                '<span class="upd-problem-cell">{}</span>',
                value
            )

        return format_html(
            '<span class="upd-ok-cell">0</span>'
        )

    @admin.display(description='Сумма с НДС', ordering='total_amount_vatadd')
    def total_amount_vatadd_display(self, obj):
        return self.format_money(obj.total_amount_vatadd)

    @admin.display(description='Кол-во товаров', ordering='total_qty')
    def total_qty_display(self, obj):
        return self.format_number(obj.total_qty)

    @admin.display(description='Строк УПД', ordering='lines_count')
    def lines_count_display(self, obj):
        return obj.lines_count or 0

    @admin.display(description='Нет nm_id', ordering='nm_missing')
    def nm_missing_count(self, obj):
        return self.problem_cell(obj.nm_missing)

    @admin.display(description='Нет chrt_id', ordering='chrt_missing')
    def chrt_missing_count(self, obj):
        return self.problem_cell(obj.chrt_missing)

    @admin.display(description='Не совпало название', ordering='name_mismatch')
    def name_mismatch_count(self, obj):
        return self.problem_cell(obj.name_mismatch)

    @admin.display(description='Проблема НДС', ordering='vat_mismatch')
    def vat_mismatch_count(self, obj):
        return self.problem_cell(obj.vat_mismatch)

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