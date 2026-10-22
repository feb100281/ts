# reports/admin.py
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from jsoneditor.forms import JSONEditor

from django.shortcuts import render
from django.urls import path
from django.http import JsonResponse
import importlib
import json


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
    
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",  
            )
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
        "preview_btn", 
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
    
    def preview_btn(self, obj):
        # Просто ссылка на Dash приложение с ID слайда
        url = f"/apps/app/rpt_app/?slide_id={obj.id}"
        return format_html('<a href="{}" target="_blank">👁️ Preview</a>', url)
    preview_btn.short_description = "Preview"
    
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'preview/<int:slide_id>/',
                self.admin_site.admin_view(self.slide_preview_page),
                name='slide_preview',
            ),
        ]
        return custom_urls + urls
    
    def slide_preview_page(self, request, slide_id):
        """Страница превью слайда - в iframe с Dash"""
        from .models import SlideRegistered
        slide = SlideRegistered.objects.get(id=slide_id)
        
        # Создаем URL для Dash приложения с этим слайдом
        dash_preview_url = f"/apps/app/rpt_app/?slide_id={slide_id}&preview=true"
        
        return render(request, 'admin/slide_preview.html', {
            'slide': slide,
            'dash_url': dash_preview_url,
        })
        
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",  
            )
        }


# ==========================================================
# SECTION
# ==========================================================

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):

    search_fields = (
        "title", 
    )
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",  
            )
        }


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