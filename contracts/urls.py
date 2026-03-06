# contracts/urls.py
from django.urls import path
from . import views


app_name = "contracts"

urlpatterns = [
    path(
        "conditions/<int:condition_id>/accruals-preview/",
        views.condition_accruals_preview,
        name="condition_accruals_preview",
    ),
    
    path(
        "contracts/<int:contract_id>/reconciliation-preview/",
        views.contract_reconciliation_preview,
        name="contract_reconciliation_preview",
    ),
]