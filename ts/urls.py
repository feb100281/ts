# ts/urls.py
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth.decorators import permission_required

from .views import fx_status, cp_issues_status, treasury_status
from contracts.views import contracts_issues_status
from .admin_exports import (
    export_pl_for_csv,
    export_arap_to_date,
    export_contracts_gl_check,
    export_manpack,
    export_management_pack,
    export_cf_csv,
    export_pl_csv,
    api_budgets,                   
    export_budget_analysis,        
)


from inventories.views import export_stocks_excel, export_stocks_map

def export_view(view, perm):
    """Ссылка из меню «Экспорт»: сотрудник админки + отдельное право.

    admin_view сам по себе пускает любого, у кого стоит «статус персонала»,
    поэтому без второй проверки адрес выгрузки открыт всем сотрудникам —
    даже тем, кому в админке видна только пара справочников. Права
    заведены в gear.Exports, раздаются пользователю или группе как обычно.
    """
    guarded = permission_required("gear.%s" % perm, raise_exception=True)(view)
    return admin.site.admin_view(guarded)


login_view = auth_views.LoginView.as_view(
    template_name="admin/landing.html",
    redirect_authenticated_user=False,
)

urlpatterns = [
    path("admin/fx-status/", fx_status, name="fx_status"),
    path("admin/cp-issues-status/", cp_issues_status, name="cp_issues_status"),
    path("admin/treasury-status/", treasury_status, name="treasury_status"),
    path("admin/contracts-issues-status/", contracts_issues_status, name="contracts_issues_status"),
    path("admin/export/pl-for-csv/", export_view(export_pl_for_csv, "export_gl"), name="export_pl_for_csv",),
    path("admin/export/arap-to-date/", export_view(export_arap_to_date, "export_arap"), name="export_arap_to_date",),
    path("admin/export/contracts-gl-check/", export_view(export_contracts_gl_check, "export_contracts_check"), name="export_contracts_gl_check",),
    path("admin/export/stocks/", export_view(export_stocks_excel, "export_stocks"), name="export_stocks"),
    path("admin/export/stocks-map/", export_view(export_stocks_map, "export_stocks"), name="export_stocks_map"),
    path("admin/export/manpack/", export_view(export_manpack, "export_manpack"), name="export_manpack"),
    path("admin/export/management-pack/", export_view(export_management_pack, "export_management_pack"), name="export_management_pack"),
    path("admin/export/management-pack/cf-csv/", export_view(export_cf_csv, "export_management_pack"), name="export_cf_csv"),
    path("admin/export/management-pack/pl-csv/", export_view(export_pl_csv, "export_management_pack"), name="export_pl_csv"),
    path("admin/api/budgets/", export_view(api_budgets, "export_budget_analysis"), name="api_budgets"),
    path("admin/export/budget-analysis/", export_view(export_budget_analysis, "export_budget_analysis"), name="export_budget_analysis"),
    path("reports/", include("reports.urls")),


    
    path("apps/", include('django_plotly_dash.urls')),

    path("admin/", admin.site.urls),

    path("", login_view, name="landing"),
    path("login/", login_view, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            email_template_name="registration/password_reset_email.txt",
            html_email_template_name="registration/password_reset_email.html",
        ),
        name="password_reset",
    ),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    
    path("contracts/", include("contracts.urls", namespace="contracts")),
    path("tools/", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

