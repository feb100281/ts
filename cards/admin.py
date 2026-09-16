# cards/admin.py

import os
from django.db.models.functions import Cast
from django.contrib import admin
from django.db.models import Count, Q, F, Sum, ExpressionWrapper, DecimalField
from django.utils.html import format_html
from .reporting.builder import MissingFieldsReportGenerator
from .models import (
    Lot, LotFile, UpdDocument, UpdDocumentFile, WbProduct
)
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse
from .forms import UpdReconciliationForm, ArticlesAnalysisForm
from .reconciliation import run_reconciliation
from .models import WODashboard
from .reporting.registry_exporter import generate_registry_response
from .reporting.registry_pdf import generate_registry_pdf
from .exports.single_upd_exporter import SingleUpdExporter

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
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    inlines = [LotFileInline]


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
                Q(nm_missing__gt=0) | Q(chrt_missing__gt=0) | 
                Q(name_mismatch__gt=0) | Q(vat_mismatch__gt=0)
            )
        if value == 'no_problem':
            return queryset.filter(
                nm_missing=0, chrt_missing=0, name_mismatch=0, vat_mismatch=0
            )
        return queryset


@admin.register(UpdDocument)
class UpdDocumentAdmin(admin.ModelAdmin):
    change_list_template = "admin/cards/upddocument/change_list.html"
    date_hierarchy = "date"
    actions = ['export_complete_package', 'export_registry_excel',  'export_registry_pdf', 'export_upd_separate_files']

    list_display = (
        'counterparty_short',
        'upd_link',
        'dash_link',
        # 'lot',
        'total_amount_vatadd_display',
        'total_amount_vatless_display',
        'total_man_cost_display',
        'cost_diff_display',
        'cost_diff_percent_display',
        'total_qty_display',
        'lines_count_display',
        'nm_missing_count',
        'chrt_missing_count',
        'vat_mismatch_count',
       
    )
    
    list_display_links = ('counterparty_short', 'upd_link')

    list_filter = ('counterparty',)

    search_fields = (
        'number', 'comment',
        'income_lines__upd_sa_name',
        'income_lines__upd_title',
        'income_lines__nm__nm_id',
    )

    autocomplete_fields = ('counterparty', 'contract')
    inlines = [UpdDocumentFileInline]


    
    
    def get_queryset(self, request):
        man_cost_expr = ExpressionWrapper(
            F('income_lines__man_cost_per_unit') * F('income_lines__upd_qty'),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )

        qs = super().get_queryset(request).annotate(
            total_amount_vatadd=Sum('income_lines__upd_amount_vatadd'),
            total_amount_vatless=Sum('income_lines__upd_amount_vatless'),
            total_man_cost=Sum(man_cost_expr),
            total_qty=Sum('income_lines__upd_qty'),
            lines_count=Count('income_lines'),
            nm_missing=Count('income_lines', filter=Q(income_lines__nm__isnull=True)),
            chrt_missing=Count('income_lines', filter=Q(income_lines__chrt__isnull=True)),
            vat_mismatch=Count(
                'income_lines',
                filter=(
                    Q(income_lines__upd_vat_rate__isnull=False)
                    & Q(income_lines__upd_vat_rate__gt=0)
                    & (
                        ~Q(
                                income_lines__upd_vat_rate=Cast(
                                    F('income_lines__card_vat_rate'),
                                    DecimalField(max_digits=10, decimal_places=2)
                                )
                            )
                                                )
                    & ~(
                        Q(income_lines__upd_vat_rate__in=[20, 22])
                        & Q(income_lines__card_vat_rate__isnull=True)
                    )
                )
            ),
        )

        return qs.annotate(
            total_cost_diff=ExpressionWrapper(
                F('total_man_cost') - F('total_amount_vatless'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            ),
            total_cost_diff_percent=ExpressionWrapper(
                (F('total_man_cost') - F('total_amount_vatless')) * 100 / F('total_amount_vatless'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            ),
        )
    
    def changelist_view(self, request, extra_context=None):
        cl = self.get_changelist_instance(request)
        full_queryset = cl.get_queryset(request)

        # Получаем ID всех УПД в текущей выборке
        upd_ids = list(full_queryset.values_list('id', flat=True))
        
        man_cost_expr = ExpressionWrapper(
            F('income_lines__man_cost_per_unit') * F('income_lines__upd_qty'),
            output_field=DecimalField(max_digits=18, decimal_places=2)
        )

        # Общая статистика
        total_stats = full_queryset.aggregate(
            total_amount_vatadd=Sum('income_lines__upd_amount_vatadd'),
            total_qty=Sum('income_lines__upd_qty'),
            total_lines_count=Count('income_lines'),
            total_amount_vatless=Sum('income_lines__upd_amount_vatless'),
            total_man_cost=Sum(man_cost_expr),
            
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
                    & ~(
                        Q(income_lines__upd_vat_rate__in=[20, 22])
                        & Q(income_lines__card_vat_rate__isnull=True)
                    )
                )
            ),
            total_vat_mismatch_amount=Sum(
                'income_lines__upd_amount_vatadd',
                filter=(
                    Q(income_lines__upd_vat_rate__isnull=False)
                    & Q(income_lines__upd_vat_rate__gt=0)
                    & ~Q(income_lines__upd_vat_rate=F('income_lines__card_vat_rate'))
                    & ~(
                        Q(income_lines__upd_vat_rate__in=[20, 22])
                        & Q(income_lines__card_vat_rate__isnull=True)
                    )
                )
            ),
        )

        total_amount = total_stats['total_amount_vatadd'] or 0
        total_amount_vatless = total_stats['total_amount_vatless'] or 0
        total_man_cost = total_stats['total_man_cost'] or 0
        cost_diff = total_man_cost - total_amount_vatless
        
        extra_context = extra_context or {}
        extra_context['total_stats'] = {
            # Базовая статистика
            'amount_vatadd': total_amount,
            'qty': total_stats['total_qty'] or 0,
            'lines_count': total_stats['total_lines_count'] or 0,
            'upd_count': len(upd_ids),
            
            # Проблемы
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
            
            'amount_vatless': total_amount_vatless,
            'man_cost': total_man_cost,
            'cost_diff': cost_diff,
            'cost_diff_percent': self._calc_percent(cost_diff, total_amount_vatless),
            
            'cost_diff_abs': abs(cost_diff),
            'cost_diff_percent': self._calc_percent(cost_diff, total_amount_vatless),
            'cost_diff_percent_abs': abs(self._calc_percent(cost_diff, total_amount_vatless)),
        }

        return super().changelist_view(request, extra_context=extra_context)
    
    
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reconcile/', self.admin_site.admin_view(self.reconcile_view), name='cards_upddocument_reconcile'),
            path('analyze-articles/', self.admin_site.admin_view(self.analyze_articles_view), name='cards_upddocument_analyze_articles'), 
        ]
        return custom_urls + urls
    


    @admin.action(description='📊 Выгрузить реестр документов (Excel)')
    def export_registry_excel(self, request, queryset):
        """
        Экшен для выгрузки реестра документов в Excel
        """
        upd_ids = list(queryset.values_list('id', flat=True))
        return generate_registry_response(upd_ids, format_type='excel')
    
    @admin.action(description='📄 Выгрузить реестр документов (PDF)')
    def export_registry_pdf(self, request, queryset):
        """
        Экшен для выгрузки реестра документов в PDF
        """
        upd_ids = list(queryset.values_list('id', flat=True))
        return generate_registry_response(upd_ids, format_type='pdf')
    
    
    @admin.action(description='📁 Выгрузить УПД отдельными файлами (Excel)')
    def export_upd_separate_files(self, request, queryset):
        """
        Экшен для выгрузки каждой УПД отдельным Excel-файлом
        """
        if queryset.count() == 1:
            return SingleUpdExporter.generate_response(queryset.first())
        else:
            return SingleUpdExporter.generate_zip_response(queryset)
    
    def analyze_articles_view(self, request):
        """Вьюха для анализа по артиклям из Excel"""
        from .forms import ArticlesAnalysisForm
        from .services.article_analyzer import ArticleAnalyzer
        
        if request.method == 'POST':
            form = ArticlesAnalysisForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    excel_file = request.FILES['excel_file']
                    articles = form.get_articles()
                    
                    analyzer = ArticleAnalyzer(articles)
                    output = analyzer.to_excel()
                    
                    response = HttpResponse(
                        output.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename=article_analysis_report.xlsx'
                    return response
                except Exception as e:
                    from django.contrib import messages
                    messages.error(request, f'Ошибка: {str(e)}')
        else:
            form = ArticlesAnalysisForm()
        
        return render(request, 'admin/cards/upddocument/analyze_articles.html', {'form': form})

    
    
    def reconcile_view(self, request):
        """Вьюха для сверки всех УПД с файлом 1С"""
        from .forms import UpdReconciliationForm
        from .reconciliation import run_reconciliation
        
        if request.method == 'POST':
            form = UpdReconciliationForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    excel_file = request.FILES['excel_file']
                    output = run_reconciliation(excel_file)
                    
                    response = HttpResponse(
                        output.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = 'attachment; filename=upd_reconciliation_report.xlsx'
                    return response
                except Exception as e:
                    from django.contrib import messages
                    messages.error(request, f'Ошибка: {str(e)}')
        else:
            form = UpdReconciliationForm()
        
        return render(request, 'admin/cards/upddocument/reconcile.html', {'form': form})

    
    @staticmethod
    def _calc_percent(amount, total):
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
    
    @staticmethod
    def format_money_nowrap(value):
        value = value or 0
        text = f'{value:,.2f}'.replace(',', ' ') + ' ₽'
        return format_html(
            '<span style="white-space:nowrap;">{}</span>',
            text
        )
    

    
    @admin.display(description='УПД', ordering='number')
    def upd_link(self, obj):
        return format_html(
            '''
            <div class="upd-number-cell">
                <div class="upd-number-main">№ {}</div>
                <div class="upd-number-meta">id: {}</div>
                <div class="upd-number-date">от {}</div>
            </div>
            ''',
            obj.number,
            obj.id,
            obj.date.strftime("%d.%m.%Y")
        )
        
    
    
    @admin.action(description='📦 Выгрузить полный пакет (оба отчета + PDF)')
    def export_complete_package(self, request, queryset):
        upd_ids = list(queryset.values_list('id', flat=True))
        generator = MissingFieldsReportGenerator()
        response = generator.get_report_response( upd_ids)
        return response

    @staticmethod
    def format_number(value):
        value = value or 0
        return f'{value:,.2f}'.replace(',', ' ')

    def problem_cell(self, value):
        value = value or 0
        if value > 0:
            return format_html('<span class="upd-problem-cell">{}</span>', value)
        return format_html('<span class="upd-ok-cell">0</span>')

    @admin.display(description='Сумма с НДС', ordering='total_amount_vatadd')
    def total_amount_vatadd_display(self, obj):
        return self.format_money_nowrap(obj.total_amount_vatadd)

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
    
    
    @admin.display(description='Сумма без НДС', ordering='total_amount_vatless')
    def total_amount_vatless_display(self, obj):
        return self.format_money_nowrap(obj.total_amount_vatless)


    @admin.display(description='Упр. с/сть', ordering='total_man_cost')
    def total_man_cost_display(self, obj):
        return self.format_money_nowrap(obj.total_man_cost)


    @admin.display(description='Разница ₽', ordering='total_cost_diff')
    def cost_diff_display(self, obj):
        diff = obj.total_cost_diff or 0
        color = '#dc2626' if diff > 0 else '#16a34a'

        text = f'{abs(diff):,.2f}'.replace(',', ' ') + ' ₽'

        return format_html(
            '<span style="font-weight:700; color:{}; white-space:nowrap;">{}</span>',
            color,
            text
        )


    @admin.display(description='Разница %', ordering='total_cost_diff_percent')
    def cost_diff_percent_display(self, obj):
        percent = obj.total_cost_diff_percent or 0
        color = '#dc2626' if percent > 0 else '#16a34a'

        return format_html(
            '<span style="font-weight:700; color:{}; white-space:nowrap;">{}%</span>',
            color,
            f'{abs(percent):.1f}'
        )

    class Media:
        css = {
            "all": ("css/admin_overrides.css", "css/wide-table.css")
        }





@admin.register(WbProduct)
class WbProductAdmin(admin.ModelAdmin):
    list_display = (
        'card_id', 'sa_name', 'sa_pid', 'title_short',
        'brand', 'subject_name', 'vat_rate', 'discount_vat',
        'has_parent', 'sizes_display',
    )
    list_filter = ('brand', 'subject_name', 'has_parent', 'discount_vat', 'origin_country', 'gender')
    search_fields = ('card__nm_id', 'sa_name', 'sa_pid', 'title', 'alternative_name', 'tnved')
    readonly_fields = (
        'card', 'nm_pid', 'sa_name', 'sa_pid', 'title', 'alternative_name',
        'brand', 'subject_name', 'subject_id', 'has_parent', 'vat_rate',
        'discount_vat', 'tnved', 'gender', 'origin_country', 'available_sizes',
        'photo_hq', 'photo_preview', 'cert_end_date', 'wb_created_at',
        'wb_updated_at', 'updated_at',
    )
    fields = readonly_fields
    ordering = ('sa_name',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def title_short(self, obj):
        return obj.title[:80] if obj.title else ''
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
            "all": ("css/admin_overrides.css", "css/wide-table.css", "css/manual_admin_groups.css")
        }
    
    
   
# cards/admin.py


# cards/admin.py

from django.contrib import admin
from django.utils.html import format_html

from .models import WODashboard


@admin.register(WODashboard)
class WODashboardAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/cards/wodashboard/wo_dashboard.html"
    )

    def has_add_permission(
        self,
        request
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None
    ):
        return False

    def get_queryset(
        self,
        request
    ):
        return (
            self.model.objects.none()
        )

