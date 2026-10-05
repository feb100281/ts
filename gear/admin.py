# gear/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import SegmentsSales, DailySales, CostsControl, Stats, Loans, ManPack, TelegramAccess


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




@admin.register(ManPack)
class ManPackDashboardAdmin(admin.ModelAdmin):

    change_list_template = (
        "admin/gear/manpack/manpack.html"
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return self.model.objects.none()


@admin.register(TelegramAccess)
class TelegramAccessAdmin(admin.ModelAdmin):
    """Заявки появляются сами, когда человек пишет боту. Доступ — галочкой."""

    list_display = ("full_name", "username", "bot", "is_allowed", "comment", "requests",
                    "last_seen", "tg_id")
    list_editable = ("is_allowed", "comment")
    list_filter = ("bot", "is_allowed")
    search_fields = ("full_name", "username", "comment", "tg_id")
    readonly_fields = ("tg_id", "bot", "full_name", "username", "requests", "created_at",
                       "last_seen")
    actions = ("allow", "revoke")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Разрешить доступ")
    def allow(self, request, queryset):
        queryset.update(is_allowed=True)

    @admin.action(description="Закрыть доступ")
    def revoke(self, request, queryset):
        queryset.update(is_allowed=False)
