"""Разноска зарубежных компаний: транзитные счета, режим, неразнесённые шаблоны."""
from collections import defaultdict
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Count, Sum
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import AmMode, CfData, TransitAccount


@admin.register(TransitAccount)
class TransitAccountAdmin(admin.ModelAdmin):
    list_display = ("account", "comment")
    search_fields = ("account", "comment")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self.message_user(request, "Счёт сохранён. Операции пересоберутся при следующей разноске (шестерёнка, "
                                   "загрузка выписки или сохранение договора).")


def unassigned_view(request):
    """Операции без договора: по контрагенту, шаблону назначения и направлению."""
    from utils.bsparsers.am.translate import template
    from corporate.models import Owners
    owner = request.GET.get("owner")
    qs = (CfData.objects.exclude(owner__country="RU").exclude(owner__isnull=True)
          .filter(contract__isnull=True, manual=False).exclude(splits__isnull=False))
    if owner:
        qs = qs.filter(owner_id=owner)
    groups = defaultdict(lambda: dict(n=0, s=Decimal(0), sample=None))
    for r in qs.values("id", "owner_id", "owner__name", "cp_id", "cp__name", "cp_bs_name", "temp", "temp_ru",
                       "dt", "cr").iterator():
        incoming = (r["dt"] or 0) > 0
        tpl = template(r["temp"] or "")[0].strip()
        g = groups[(r["owner_id"], r["cp_id"], r["cp_id"] or (r["cp_bs_name"] or ""), tpl, incoming)]
        g["n"] += 1
        g["s"] += (r["dt"] if incoming else r["cr"]) or 0
        if g["sample"] is None:
            g["sample"] = r
    rows = []
    for (o, cp, _, tpl, inc), g in sorted(groups.items(), key=lambda kv: -kv[1]["n"])[:300]:
        x = g["sample"]
        if cp:
            link = reverse("admin:contracts_contracts_changelist") + f"?cp__id__exact={cp}"
            label = "договоры контрагента"
        else:
            link = reverse("admin:treasury_counterpartyaccount_add")
            label = "привязать счёт"
        ops = reverse("admin:treasury_cfdata_changelist") + f"?owner__id__exact={o}&contract__isnull=True"
        ops += f"&cp__id__exact={cp}" if cp else f"&q={x['id']}"
        rows.append(dict(owner=x["owner__name"], cp=x["cp__name"] or "", bs_name=x["cp_bs_name"] or "",
                         tpl=tpl, ru=x["temp_ru"] or "", incoming=inc, n=g["n"], s=g["s"],
                         link=link, label=label, ops=ops))
    ctx = dict(admin.site.each_context(request), title="Неразнесённые шаблоны", rows=rows,
               total=sum(g["n"] for g in groups.values()), groups=len(groups),
               owners=Owners.objects.exclude(country="RU").exclude(country__isnull=True), owner=owner)
    return TemplateResponse(request, "admin/treasury/cfdata/unassigned.html", ctx)


@admin.register(AmMode)
class AmModeAdmin(admin.ModelAdmin):
    list_display = ("owner", "on", "switched_at")
    readonly_fields = ("switched_at",)

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if "on" in form.changed_data:
            obj.switched_at = timezone.now()
        super().save_model(request, obj, form, change)
