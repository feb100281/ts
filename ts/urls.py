# ts/urls.py
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path,include

from .views import fx_status, cp_issues_status, treasury_status, contracts_issues_status
from .admin_exports import export_pl_for_csv, export_arap_to_date

login_view = auth_views.LoginView.as_view(
    template_name="admin/landing.html",
    redirect_authenticated_user=False,
)

urlpatterns = [
    path("admin/fx-status/", fx_status, name="fx_status"),
    path("admin/cp-issues-status/", cp_issues_status, name="cp_issues_status"),
    path("admin/treasury-status/", treasury_status, name="treasury_status"),
    path("admin/contracts-issues-status/", contracts_issues_status, name="contracts_issues_status"),
    path("admin/export/pl-for-csv/", admin.site.admin_view(export_pl_for_csv), name="export_pl_for_csv",),
    path("admin/export/arap-to-date/", admin.site.admin_view(export_arap_to_date), name="export_arap_to_date",),
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

