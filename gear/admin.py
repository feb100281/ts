# gear/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import SegmentsSales, DailySales, CostsControl, Stats, Loans


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


@admin.register(DailySales)
class DaylySalesDashboardAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/gear/dailysales/dailysales.html"
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

@admin.register(CostsControl)
class CostsControlDashboardAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/gear/costscontrol/costscontrol.html"
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



@admin.register(Stats)
class StatsDashboardAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/gear/stats/stats.html"
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
        
        

@admin.register(Loans)
class LoansDashboardAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/gear/loans/loans.html"
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

