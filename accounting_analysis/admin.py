# accounting_analysis/admin.py

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from django.db.models import Count

from .models import AccountingAnalysis, AnalysisScript, AccountingMetric
from accounting_analysis.services.runner import run_analysis



@admin.register(AccountingAnalysis)
class AccountingAnalysisAdmin(admin.ModelAdmin):
    change_list_template = "admin/accounting_analysis/accountinganalysis/change_list.html"
    change_form_template = "admin/accounting_analysis/accountinganalysis/change_form.html"

    list_display = (
        "name",
        "script",
        "account",
        "colored_status",
        "run_button",
        "report_link",
        "created_at",
    )
    list_filter = ("status", "script", "account")
    search_fields = ("name", "account")
    readonly_fields = (
        "status",
        "error_text",
        "report_file",
        "created_at",
        "created_by",
    )

    fieldsets = (
        ("Основное", {
            "fields": ("name", "file", "script", "account")
        }),
        ("Результат", {
            "fields": ("status", "report_file", "error_text"),
        }),
        ("Служебное", {
            "fields": ("created_by", "created_at"),
        }),
    )

    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
            )
        }

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        if obj.report_file:
            obj.report_file.delete(save=False)

        if obj.file:
            obj.file.delete(save=False)

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.report_file:
                obj.report_file.delete(save=False)

            if obj.file:
                obj.file.delete(save=False)

        super().delete_queryset(request, queryset)

    def colored_status(self, obj):
        styles = {
            "new": ("#fef3c7", "#92400e", "Новый"),
            "done": ("#dcfce7", "#166534", "Готов"),
            "error": ("#fee2e2", "#991b1b", "Ошибка"),
        }
        bg, color, label = styles.get(obj.status, ("#f3f4f6", "#374151", obj.get_status_display()))
        return format_html(
            '<span style="padding:3px 8px;border-radius:2px;'
            'background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            bg, color, label
        )
    colored_status.short_description = "Статус"

    def report_link(self, obj):
        if obj.report_file:
            return format_html(
                '<a href="{}" target="_blank" '
                'style="font-weight:700;text-decoration:none;">📄 Скачать</a>',
                obj.report_file.url
            )
        return format_html('<span style="color:#9ca3af;">—</span>')
    report_link.short_description = "Отчет"

    def run_button(self, obj):
        url = reverse("admin:accounting-analysis-run", args=[obj.id])
        return format_html(
            '<a class="button" href="{}" '
            'style="padding:4px 10px;border-radius:2px;">▶ Запустить</a>',
            url
        )
    run_button.short_description = "Анализ"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "run/<int:analysis_id>/",
                self.admin_site.admin_view(self.run_analysis_view),
                name="accounting-analysis-run",
            ),
        ]
        return custom_urls + urls

    def run_analysis_view(self, request, analysis_id):
        obj = AccountingAnalysis.objects.get(pk=analysis_id)

        try:
            run_analysis(obj)
            self.message_user(request, "✅ Анализ выполнен", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ Ошибка: {e}", messages.ERROR)

        return redirect(request.META.get("HTTP_REFERER", "../"))

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)

        extra_context["total_count"] = qs.count()
        extra_context["new_count"] = qs.filter(status="new").count()
        extra_context["done_count"] = qs.filter(status="done").count()
        extra_context["error_count"] = qs.filter(status="error").count()

        return super().changelist_view(request, extra_context=extra_context)


@admin.register(AnalysisScript)
class AnalysisScriptAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
            )
        }


@admin.register(AccountingMetric)
class AccountingMetricAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "metric_name",
        "value",
        "period",
        "analysis",
    )
    list_filter = ("account", "metric_name", "period")
    search_fields = ("account", "metric_name")
    
    
    
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
            )
        }


