# gear/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import SegmentsSales, DailySales, CostsControl, Stats, Loans, ManPack, TelegramAccess, TelegramQuestion


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

    change_list_template = "admin/gear/telegramaccess/change_list.html"
    list_display = ("person", "bot_badge", "status", "is_allowed", "comment", "requests",
                    "last_seen")
    list_display_links = ("person",)
    list_editable = ("is_allowed", "comment")
    list_filter = ("bot", "is_allowed")
    search_fields = ("full_name", "username", "comment", "tg_id")
    readonly_fields = ("tg_id", "bot", "full_name", "username", "requests", "created_at",
                       "last_seen")
    actions = ("allow", "revoke", "print_selected")
    list_per_page = 100

    @admin.display(description="Telegram", ordering="full_name")
    def person(self, obj):
        nick = format_html('<span class="tga-nick">@{}</span>', obj.username) if obj.username else ""
        return format_html('<span class="tga-name">{}</span>{}',
                           obj.full_name or f"ID {obj.tg_id}", nick)

    @admin.display(description="Помощник", ordering="bot")
    def bot_badge(self, obj):
        return format_html('<span class="tga-bot tga-bot-{}">{}</span>', obj.bot,
                           obj.get_bot_display())

    @admin.display(description="Статус", ordering="is_allowed")
    def status(self, obj):
        return format_html('<span class="tga-st tga-st-{}">{}</span>',
                           "on" if obj.is_allowed else "wait",
                           "Доступ есть" if obj.is_allowed else "Ждёт решения")

    # ---- сводка над списком
    def changelist_view(self, request, extra_context=None):
        import os
        rows = []
        for code, title in TelegramAccess.BOTS:
            qs = TelegramAccess.objects.filter(bot=code)
            rows.append({
                "title": title, "code": code,
                "allowed": qs.filter(is_allowed=True).count(),
                "waiting": qs.filter(is_allowed=False).count(),
                "username": os.getenv(f"TELEGRAM_BOT_USERNAME_{code.upper()}",
                                      f"tr_{code}_bot"),
            })
        ctx = {"tga_bots": rows, "tga_waiting": sum(r["waiting"] for r in rows)}
        return super().changelist_view(request, extra_context={**(extra_context or {}), **ctx})

    # ---- печать списка
    def get_urls(self):
        from django.urls import path
        return [path("print/", self.admin_site.admin_view(self.print_view),
                     name="gear_telegramaccess_print")] + super().get_urls()

    def _print(self, request, queryset):
        from django.shortcuts import render
        from datetime import datetime
        groups = []
        for code, title in TelegramAccess.BOTS:
            people = list(queryset.filter(bot=code, is_allowed=True)
                          .order_by("comment", "full_name"))
            if people:
                groups.append({"title": title, "people": people})
        return render(request, "admin/gear/telegramaccess/print.html", {
            "groups": groups, "now": datetime.now(),
            "total": sum(len(g["people"]) for g in groups)})

    def print_view(self, request):
        return self._print(request, TelegramAccess.objects.all())

    @admin.action(description="Печать списка: у кого есть доступ (из выбранных)")
    def print_selected(self, request, queryset):
        return self._print(request, queryset)

    def has_add_permission(self, request):
        return False

    def _set(self, obj, allowed):
        """Меняет доступ и сообщает человеку в Telegram."""
        from .telegram_notify import access_changed
        if obj.is_allowed != allowed:
            obj.is_allowed = allowed
            obj.save(update_fields=["is_allowed"])
        access_changed(obj.tg_id, obj.bot, allowed)

    def save_model(self, request, obj, form, change):
        changed = change and "is_allowed" in getattr(form, "changed_data", [])
        super().save_model(request, obj, form, change)
        if changed:
            from .telegram_notify import access_changed
            access_changed(obj.tg_id, obj.bot, obj.is_allowed)

    @admin.action(description="Разрешить доступ")
    def allow(self, request, queryset):
        for obj in queryset.filter(is_allowed=False):
            self._set(obj, True)

    @admin.action(description="Закрыть доступ")
    def revoke(self, request, queryset):
        for obj in queryset.filter(is_allowed=True):
            self._set(obj, False)


@admin.register(TelegramQuestion)
class TelegramQuestionAdmin(admin.ModelAdmin):
    """Журнал вопросов к ботам. Только чтение, только суперпользователь."""

    change_list_template = "admin/gear/telegramquestion/change_list.html"
    list_display = ("asked_at", "who", "bot_badge", "question", "seconds", "cost", "has_file",
                    "is_error")
    list_display_links = None
    list_filter = ("bot", ("asked_at", admin.DateFieldListFilter), "is_error", "has_file",
                   "access")
    search_fields = ("text", "access__comment", "access__full_name", "access__username")
    date_hierarchy = "asked_at"
    list_select_related = ("access",)
    list_per_page = 100
    actions = None

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    has_view_permission = lambda self, request, obj=None: self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @staticmethod
    def _name(a):
        return a.comment or a.full_name or a.username or f"ID {a.tg_id}"

    @admin.display(description="Кто", ordering="access__comment")
    def who(self, obj):
        a = obj.access
        nick = format_html('<span class="tga-nick">@{}</span>', a.username) if a.username else ""
        return format_html('<span class="tga-name">{}</span>{}', self._name(a), nick)

    @admin.display(description="Помощник", ordering="bot")
    def bot_badge(self, obj):
        return format_html('<span class="tga-bot tga-bot-{}">{}</span>', obj.bot,
                           obj.get_bot_display())

    @admin.display(description="Вопрос")
    def question(self, obj):
        return format_html('<span class="tgq-text">{}</span>', obj.text)

    @admin.display(description="Стоимость, $", ordering="cost_usd")
    def cost(self, obj):
        return "—" if obj.cost_usd is None else f"{obj.cost_usd:.3f}"

    def changelist_view(self, request, extra_context=None):
        """Сводка по людям — по тем же фильтрам, что и список."""
        from django.db.models import Count, Q, Sum
        resp = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = resp.context_data["cl"].queryset
        except (AttributeError, KeyError):
            return resp
        rows = (qs.order_by().values("access_id", "bot")
                .annotate(n=Count("id"), err=Count("id", filter=Q(is_error=True)),
                          files=Count("id", filter=Q(has_file=True)), cost=Sum("cost_usd"))
                .order_by("-n"))
        people = {a.pk: a for a in TelegramAccess.objects.filter(
            pk__in=[r["access_id"] for r in rows])}
        bots = dict(TelegramAccess.BOTS)
        summary = [{"name": self._name(people[r["access_id"]]), "bot": bots.get(r["bot"]),
                    "code": r["bot"], "n": r["n"], "err": r["err"], "files": r["files"],
                    "cost": r["cost"] or 0} for r in rows if r["access_id"] in people]
        resp.context_data.update(
            tgq_rows=summary, tgq_total=sum(r["n"] for r in summary),
            tgq_cost=sum(r["cost"] for r in summary), tgq_days=TelegramQuestion.KEEP_DAYS)
        return resp
