# accounting_analysis/services/registry.py

from accounting_analysis.services.scripts.account_45 import run_account_45

ANALYSIS_REGISTRY = {
    "account_45": run_account_45,
}

