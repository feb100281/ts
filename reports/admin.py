from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from jsoneditor.forms import JSONEditor

from .models import (
    Report,
    Section,
    SlideRegistered,
    ReportConstructor,
)


# ==========================================================
# INLINES
# ==========================================================

class ReportConstructorInline(admin.TabularInline):
    model = ReportConstructor
    extra = 0

    autocomplete_fields = [
        "section",
        "slide",
    ]

    fields = (
        "order",
        "section",
        "slide",
        "filters",
        "is_active",
    )

    # formfield_overrides = {
    #     models.JSONField: {"widget": JSONEditor},
    # }
   


# ==========================================================
# REPORT
# ==========================================================

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):

    list_display = (
    "title",
    "report_type",
    "author",
    "company",
    "date_from",
    "date_to",
    "dash_link",
    "pdf_link",
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
            "General",
            {
                "fields": (
                    "title",
                    "subtitle",
                    "description",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "report_type",
                    "author",
                    "company",
                    "date_from",
                    "date_to",
                )
            },
        ),
        (
            "Style",
            {
                "classes": ("collapse",),
                "fields": (
                    "css",
                    "slide_style",
                )
            },
        ),
        (
            "System",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    formfield_overrides = {
        models.JSONField: {
            "widget": JSONEditor
        }
    }

    @admin.display(description="Report")
    def dash_link(self, obj):

        url = (
            f"/apps/app/rpt_app/"
            f"?object_id={obj.id}"
        )

        return format_html(
            '<a class="button" '
            'href="{}" '
            'target="_blank">'
            'Open'
            '</a>',
            url,
        )
    @admin.display(description="PDF")
    def pdf_link(self, obj):

        url = (
            f"/reports/report/"
            f"{obj.id}/pdf/"
        )

        return format_html(
            '<a class="button" '
            'href="{}" '
            'target="_blank">'
            'Download PDF'
            '</a>',
            url
        )


# ==========================================================
# SLIDES
# ==========================================================

@admin.register(SlideRegistered)
class SlideRegisteredAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "python_path",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "title",
        "python_path",
        "description",
    )


# ==========================================================
# SECTION
# ==========================================================

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):

    search_fields = (
        "title", 
    )


# # ==========================================================
# # REPORT CONSTRUCTOR
# # ==========================================================

# @admin.register(ReportConstructor)
# class ReportConstructorAdmin(admin.ModelAdmin):

#     list_display = (
#         "report",
#         "order",
#         "section",
#         "slide",
#         "is_active",
#     )

#     list_filter = (
#         "section",
#         "is_active",
#     )

#     autocomplete_fields = (
#         "report",
#         "section",
#         "slide",
#     )