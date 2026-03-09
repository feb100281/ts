# contracts/urls.py
from django.urls import path
from . import views
from contracts.accruals.report import accruals_report
from contracts.reconciliation.portfolio_report import debt_report


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
    

    path("accruals-report/", accruals_report, 
         name="accruals_report"),
    
     path(
            "debt-report/",
            debt_report,
            name="debt_report",
        ),
]