from datetime import date

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count

from counterparties.models import Counterparty


@login_required
@user_passes_test(lambda u: u.is_staff)
def fx_status(request):
    from macro.models import CurrencyRate

    today = date.today()
    has_fx_today = CurrencyRate.objects.filter(date=today).exists()

    return JsonResponse({
        "ok": True,
        "date": str(today),
        "has_fx_today": bool(has_fx_today),
        "admin_url": f"/admin/macro/currencyrate/?date__exact={today}",
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def cp_issues_status(request):
    base = Counterparty.objects.all()

    qs_no_contracts = (
        base.annotate(contracts_cnt=Count("contracts", distinct=True))
            .filter(contracts_cnt=0)
            .order_by("name")
    )
    no_contracts_total = qs_no_contracts.count()
    no_contracts_sample = list(qs_no_contracts.values("id", "name", "tax_id")[:3])

    qs_no_glyph = (base.filter(logo__isnull=True) | base.filter(logo="")).distinct().order_by("name")
    no_glyph_total = qs_no_glyph.count()
    no_glyph_sample = list(qs_no_glyph.values("id", "name", "tax_id")[:3])

    return JsonResponse({
        "ok": True,
        "no_contracts": {
            "total": no_contracts_total,
            "sample": no_contracts_sample,
            "admin_url": "/admin/counterparties/counterparty/?has_contract=0",
        },
        "no_glyph": {
            "total": no_glyph_total,
            "sample": no_glyph_sample,
            "admin_url": "/admin/counterparties/counterparty/?logo__isnull=1",
        },
    })
    
    

# -----------------------------
# Казначейство: CF документы
# -----------------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def treasury_status(request):
    # IMPORTANT: путь в админке строим динамически через meta,
    # чтобы не гадать app_label/model_name.
    from treasury.models import CfData  # <-- если приложение называется иначе, поменяй import

    app = CfData._meta.app_label
    model = CfData._meta.model_name
    changelist = f"/admin/{app}/{model}/"

    qs = CfData.objects.all()

    qs_no_contract = qs.filter(contract__isnull=True)
    qs_no_cfitem = qs.filter(cfitem__isnull=True)
    qs_no_cp_final = qs.filter(cp_final__isnull=True)

    return JsonResponse({
        "ok": True,
        "no_contract": {
            "total": qs_no_contract.count(),
            "admin_url": f"{changelist}?contract__isnull=1",
        },
        "no_cfitem": {
            "total": qs_no_cfitem.count(),
            "admin_url": f"{changelist}?cfitem__isnull=1",
        },
        "no_cp_final": {
            "total": qs_no_cp_final.count(),
            "admin_url": f"{changelist}?cp_final__isnull=1",
        },
    })
