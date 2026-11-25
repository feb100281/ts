# gear/middleware.py
"""Доступ к закрытым Dash-приложениям по правам пользователя.

Адреса django-plotly-dash (/apps/app/<имя>/…) сами права не проверяют: пункт в
админке скрыт, но прямая ссылка открывается. Для приложений из PROTECTED_APPS
требуем вход и право на просмотр соответствующего раздела.
"""
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden

# имя приложения → право (выдаётся в админке пользователю или группе)
PROTECTED_APPS = {
    "manpack_app": "gear.view_manpack",
}


class DashAppAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith("/apps/app/"):
            name = path[len("/apps/app/"):].split("/", 1)[0]
            perm = PROTECTED_APPS.get(name)
            if perm:
                user = getattr(request, "user", None)
                if user is None or not user.is_authenticated:
                    return redirect_to_login(request.get_full_path())
                if not (user.is_superuser or user.has_perm(perm)):
                    return HttpResponseForbidden(
                        "Нет доступа к разделу «Управленческий пакет». "
                        "Обратитесь к администратору.")
        return self.get_response(request)
