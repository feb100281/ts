# ts/views.py
from datetime import date
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.db.models import Q

from contracts.models import Contracts, Conditions, CfItemAuto
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
    
    
@login_required
@user_passes_test(lambda u: u.is_staff)
def contracts_issues_status(request):
    qs_no_accrual = Contracts.objects.filter(conditions__isnull=True).distinct()

    return JsonResponse({
        "ok": True,
        "no_accrual_fn": {
            "total": qs_no_accrual.count(),
            "admin_url": "/admin/contracts/contracts/?has_accrual_fn=no",
        },
    })
    


@login_required
@user_passes_test(lambda u: u.is_staff)
def accruals_control_status(request):
    today = date.today()

    # Активные условия на сегодня
    active_conditions = (
        Conditions.objects
        .filter(date_start__lte=today)
        .filter(Q(date_finish__isnull=True) | Q(date_finish__gte=today))
        .select_related("accounting_method", "contract")
    )

    # 1) Accrual активные
    accrual_contract_ids = (
        active_conditions
        .filter(accounting_method__code="accrual")
        .values_list("contract_id", flat=True)
        .distinct()
    )
    accrual_total = accrual_contract_ids.count()

    # 2) Cash based активные
    cash_contract_ids = (
        active_conditions
        .filter(accounting_method__code="cash_based")
        .values_list("contract_id", flat=True)
        .distinct()
    )
    cash_total = cash_contract_ids.count()

    # 3) Cash based без автоматизации CF
    cash_without_cf_total = (
        Contracts.objects
        .filter(id__in=cash_contract_ids)
        .annotate(cf_auto_cnt=Count("cfitemauto", distinct=True))
        .filter(cf_auto_cnt=0)
        .count()
    )

    # 4) Договоры без условий начисления
    no_conditions_total = Contracts.objects.filter(conditions__isnull=True).distinct().count()

    return JsonResponse({
        "ok": True,
        "month": today.strftime("%Y-%m"),
        "accrual": {
            "total": accrual_total,
            "admin_url": "/admin/contracts/contracts/?acc_method=accrual_active",
        },
        "cash_based": {
            "total": cash_total,
            "admin_url": "/admin/contracts/contracts/?acc_method=cash_active",
        },
        "cash_without_cf": {
            "total": cash_without_cf_total,
            "admin_url": "/admin/contracts/contracts/?acc_method=cash_active",
        },
        "no_conditions": {
            "total": no_conditions_total,
            "admin_url": "/admin/contracts/contracts/?has_accrual_fn=no",
        },
    })





