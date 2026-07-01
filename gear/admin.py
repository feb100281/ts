from django.contrib import admin
from django.utils.html import format_html

from .models import SegmentsSales


@admin.register(SegmentsSales)
class SegmentsSalesDashboardAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/gear/segmentssales/segments_sales.html"
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
