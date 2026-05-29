from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from unfold.decorators import display

from unfold.admin import (
    ModelAdmin,
    TabularInline,
)

from unfold.decorators import display
from unfold.contrib.forms.widgets import WysiwygWidget
from jsoneditor.forms import JSONEditor

from .models import (
    Report,
    Section,
    SlideRegistered,
    ReportConstructor,
)


# ==========================================================
# INLINE
# ==========================================================


class ReportConstructorInline(TabularInline):
    model = ReportConstructor

    extra = 0

    tab = True

    autocomplete_fields = (
        "section",
        "slide",
    )

    fields = (
        "order",
        "section",
        "slide",
        "is_active",
    )

    formfield_overrides = {models.JSONField: {"widget": JSONEditor}}


# ==========================================================
# REPORT
# ==========================================================


@admin.register(Report)
class ReportAdmin(ModelAdmin):

    list_display = (
    "report_header",
    "report_type_badge",
    "company",
    "author",
    "report_actions",
    "updated_at",
    )

    list_filter = (
        "report_type",
        "company",
    )

    search_fields = (
        "title",
        "subtitle",
        "description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        ReportConstructorInline,
    ]

    fieldsets = (
        (
            "Основное",
            {
                "classes": ["tab"],
                "fields": (
                    "title",
                    "subtitle",
                    "description",
                ),
            },
        ),
        (
            "Метаданные",
            {
                "classes": ["tab"],
                "fields": (
                    "report_type",
                    "author",
                    "company",
                    "date_from",
                    "date_to",
                ),
            },
        ),
        (
            "Стиль",
            {
                "classes": ["tab"],
                "fields": (
                    "css",
                    "slide_style",
                ),
            },
        ),
        (
            "Система",
            {
                "classes": [
                    "tab",
                    "collapse",
                ],
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        models.JSONField: {
            "widget": JSONEditor,
        },
    }

    # ======================================================
    # PRETTY LIST DISPLAY
    # ======================================================

    @display(
        description="Тип",
        label={
            "WE": "success",
            "AH": "warning",
            "WE": "info",
        },
    )
    def report_type_badge(self, obj):

        return obj.report_type

    

    @display(
        description="Действия",
        dropdown=True,
    )
    def report_actions(self, obj):
        return {
            "title": "Открыть",
            "width": 220,
            "items": [
                {
                    "title": "Открыть отчет",
                    "link": f"/apps/app/rpt_app/?object_id={obj.id}",
                },
                {
                    "title": "Скачать PDF",
                    "link": f"/reports/report/{obj.id}/pdf/",
                },
            ],
        }
        
    @display(
    description="Отчет",
    header=True,
    )
    def report_header(self, obj):
        return [
            obj.title,
            obj.subtitle or obj.description or None,
            obj.report_type,
        ]


# ==========================================================
# SLIDES
# ==========================================================


@admin.register(SlideRegistered)
class SlideRegisteredAdmin(ModelAdmin):

    list_display = (
        "title",
        "python_path",
        "active_badge",
        "updated_at",
    )

    list_filter = ("is_active",)

    search_fields = (
        "title",
        "python_path",
        "description",
    )

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }

    @display(
        description="Активен",
        boolean=True,
    )
    def active_badge(self, obj):
        return obj.is_active


# ==========================================================
# SECTION
# ==========================================================


@admin.register(Section)
class SectionAdmin(ModelAdmin):

    search_fields = ("title",)
