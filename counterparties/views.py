# counterparties/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import Http404

from .models import Tenant, Counterparty

TEMPLATE_LANDING = "admin/landing.html"


def landing_view(request):
    """
    Лендинг: выбор роли (manager | tenant) + логин/пароль.
    Менеджер УК -> админка, Арендатор -> /portal/<counterparty_id>/
    """
    if request.method == "POST":
        role = request.POST.get("role")
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next") or None

        if role not in {"manager", "tenant"}:
            messages.error(request, "Не выбрана роль.")
            return render(request, TEMPLATE_LANDING, status=400)

        user = authenticate(request, username=username, password=password)
        if not user:
            messages.error(request, "Неверные логин или пароль.")
            return render(request, TEMPLATE_LANDING, status=401)

        if not user.is_active:
            messages.error(request, "Учётная запись отключена.")
            return render(request, TEMPLATE_LANDING, status=403)

        login(request, user)

        if role == "manager":
            if user.is_staff:
                return redirect(next_url or "admin:index")
            logout(request)
            messages.error(request, "У вас нет прав менеджера (is_staff=False).")
            return render(request, TEMPLATE_LANDING, status=403)

        # role == "tenant"
        tenant = getattr(user, "tenant", None)
        if not tenant:
            logout(request)
            messages.error(request, "Для вашей учётной записи не найден кабинет арендатора.")
            return render(request, TEMPLATE_LANDING, status=403)

        return redirect(next_url or "tenant_portal", slug=str(tenant.counterparty_id))

    # GET
    return render(request, TEMPLATE_LANDING)


@login_required
def tenant_portal_view(request, slug: str):
    """
    Кабинет арендатора.
    Доступ: сам арендатор (user.tenant.counterparty_id == id) или staff.
    """
    try:
        counterparty = Counterparty.objects.get(id=int(slug))
    except (Counterparty.DoesNotExist, ValueError):
        raise Http404("Кабинет не найден")

    if not request.user.is_staff:
        tenant = getattr(request.user, "tenant", None)
        if not tenant or tenant.counterparty_id != counterparty.id:
            messages.error(request, "Нет доступа к этому кабинету.")
            return redirect("landing")

    try:
        tenant = Tenant.objects.select_related("counterparty").get(counterparty=counterparty)
    except Tenant.DoesNotExist:
        raise Http404("Кабинет не найден")

    return render(request, "admin/portal_stub.html", {"tenant": tenant})


def tenant_select_view(request):
    return redirect("landing")


def logout_view(request):
    logout(request)
    messages.success(request, "Вы вышли из системы.")
    next_url = request.GET.get("next") or "landing"  # можно поставить "admin:login", если так нужно
    return redirect(next_url)
