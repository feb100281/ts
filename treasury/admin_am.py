"""Админка «Правил разноски» зарубежных компаний."""
from collections import defaultdict
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Count, Sum
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import AmMode, AmResolver, AmRule, CfData, TransitAccount


def _rerun(owner_id, log=None):
    from utils.bsparsers.am.resolve import resolve
    lines = []
    resolve(owner_id, log=lines.append)
    return "; ".join(x.strip() for x in lines)


@admin.register(TransitAccount)
class TransitAccountAdmin(admin.ModelAdmin):
    list_display = ("account", "comment")
    search_fields = ("account", "comment")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self.message_user(request, "Чтобы операции пересобрались с учётом счёта, нажмите «Переразнести» "
                                   "в «Правилах разноски».")


class AmRuleInline(admin.TabularInline):
    model = AmRule
    extra = 1
    fields = ("order", "text_regex", "contract", "cf_item_dt", "cf_item_cr", "hits")
    readonly_fields = ("hits",)
    autocomplete_fields = ("contract", "cf_item_dt", "cf_item_cr")


@admin.register(AmResolver)
class AmResolverAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "rules_count", "rows", "comment")
    list_filter = ("owner",)
    search_fields = ("cp__name", "cp__tax_id", "comment", "rules__text_regex")
    autocomplete_fields = ("cp",)
    list_select_related = ("cp", "owner")
    inlines = [AmRuleInline]
    actions = ["rerun"]
    change_list_template = "admin/treasury/amresolver/change_list.html"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n=Count("rules", distinct=True), h=Sum("rules__hits"))

    @admin.display(description="Контрагент", ordering="cp__name")
    def name(self, obj):
        return str(obj)

    @admin.display(description="Правил", ordering="n")
    def rules_count(self, obj):
        return obj.n

    @admin.display(description="Строк", ordering="h")
    def rows(self, obj):
        return obj.h or 0

    def get_changeform_initial_data(self, request):
        return {k: request.GET[k] for k in ("owner", "cp") if request.GET.get(k)}

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self.message_user(request, "Переразнесено: " + _rerun(form.instance.owner_id))

    @admin.action(description="Переразнести операции компании по правилам")
    def rerun(self, request, queryset):
        for owner_id in sorted(set(queryset.values_list("owner_id", flat=True))):
            self.message_user(request, _rerun(owner_id))

    def get_urls(self):
        return [path("unassigned/", self.admin_site.admin_view(self.unassigned_view),
                     name="treasury_amresolver_unassigned"),
                path("rerun-all/", self.admin_site.admin_view(self.rerun_all_view),
                     name="treasury_amresolver_rerun_all")] + super().get_urls()

    def rerun_all_view(self, request):
        from django.shortcuts import redirect
        from corporate.models import Owners
        if request.method == "POST":
            for o in Owners.objects.exclude(country="RU").exclude(country__isnull=True):
                self.message_user(request, f"{o}: {_rerun(o.pk)}")
        return redirect("admin:treasury_amresolver_changelist")

    def unassigned_view(self, request):
        """Операции без договора, сгруппированные по контрагенту, шаблону назначения и направлению."""
        from utils.bsparsers.am.translate import template
        owner = request.GET.get("owner")
        qs = (CfData.objects.exclude(owner__country="RU").exclude(owner__isnull=True)
              .filter(contract__isnull=True, manual=False).exclude(splits__isnull=False))
        if owner:
            qs = qs.filter(owner_id=owner)
        resolvers = {(o, c): i for i, o, c in AmResolver.objects.values_list("id", "owner_id", "cp_id")}
        groups = defaultdict(lambda: dict(n=0, s=Decimal(0), sample=None))
        for r in qs.values("id", "owner_id", "owner__name", "cp_id", "cp__name", "cp_bs_name", "temp", "temp_ru",
                           "dt", "cr").iterator():
            incoming = (r["dt"] or 0) > 0
            tpl = template(r["temp"] or "")[0].strip()
            key = (r["owner_id"], r["cp_id"], r["cp_id"] or (r["cp_bs_name"] or ""), tpl, incoming)
            g = groups[key]
            g["n"] += 1
            g["s"] += (r["dt"] if incoming else r["cr"]) or 0
            if g["sample"] is None:
                g["sample"] = r
        rows = []
        for (o, cp, _, tpl, inc), g in sorted(groups.items(), key=lambda kv: -kv[1]["n"])[:300]:
            s = g["sample"]
            rid = resolvers.get((o, cp))
            if rid:
                link = reverse("admin:treasury_amresolver_change", args=[rid])
            else:
                link = reverse("admin:treasury_amresolver_add") + f"?owner={o}" + (f"&cp={cp}" if cp else "")
            ops = reverse("admin:treasury_cfdata_changelist") + f"?owner__id__exact={o}&contract__isnull=True"
            ops += f"&cp__id__exact={cp}" if cp else f"&q={s['id']}"
            rows.append(dict(owner=s["owner__name"], cp=s["cp__name"] or "", bs_name=s["cp_bs_name"] or "",
                             tpl=tpl, ru=s["temp_ru"] or "", incoming=inc, n=g["n"], s=g["s"],
                             has_rules=bool(rid), link=link, ops=ops))
        from corporate.models import Owners
        ctx = dict(self.admin_site.each_context(request), title="Неразнесённые шаблоны", rows=rows,
                   total=sum(g["n"] for g in groups.values()), groups=len(groups),
                   owners=Owners.objects.exclude(country="RU").exclude(country__isnull=True), owner=owner,
                   opts=self.model._meta)
        return TemplateResponse(request, "admin/treasury/amresolver/unassigned.html", ctx)


@admin.register(AmMode)
class AmModeAdmin(admin.ModelAdmin):
    list_display = ("owner", "on", "switched_at")
    readonly_fields = ("switched_at",)

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if "on" in form.changed_data:
            obj.switched_at = timezone.now()
        super().save_model(request, obj, form, change)
