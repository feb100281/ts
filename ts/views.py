from datetime import date
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse

from macro.models import CurrencyRate  

@staff_member_required
def admin_today(request):
    today = date.today()

    # Проверка: есть ли курс на сегодня
    fx_exists = CurrencyRate.objects.filter(date=today).exists()  
    fx_missing_today = 0 if fx_exists else 1

    # Ссылка на админку со списком курсов (фильтр по сегодняшней дате)
    fx_url = reverse("admin:macro_currencyrate_changelist") + f"?date__exact={today.isoformat()}"

    items = {
        "fx_missing_today": fx_missing_today,
    }

    data = {
        "date": today.isoformat(),
        "total": sum(items.values()),
        "items": items,
        "lists": {"fx": {"url": fx_url}},
    }
    return JsonResponse(data)
