
# run_fixed_payments.py
import os
import django
from types import SimpleNamespace
from datetime import date
import pandas as pd
from pprint import pprint
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ts.settings")
django.setup()

from contracts.accruals.calculators.fixed_payments import preview
from contracts.models import Contracts, Conditions
from ..engine import preview_accruals

co = SimpleNamespace(
    id=1,
    amount="545454.54",
    vat_mode="exclusive",
    date_start=date(2025, 10, 12),
    date_finish=date(2025, 12, 31),
    params={
        "amount": "545454.54",
        "vat_rate": "20",
        "amount_basis": "month",
    },
)

conditions = (
        Conditions.objects
        .filter(contract=32)
        .order_by("date_start", "id")
    )

pprint(conditions)


ad = "2025-10-12"

d = preview(cond=co, anchor_date=ad)
print(d)

result = d

df = pd.DataFrame(result["rows"])
pprint(result["rows"])
def accurals(
    condition_id:int,
    contract_id:int,
    date_start:date,
    date_finish:date,
    fn_name:str,
    fn_json:json = None,
    vat_mode:int = None,
    vat_json:int = None,
    acc_st:int = None,
    acc_bs:int = None,
    subconto_bs:int = None,
    acc_pl:int = None,
    subconto_pl:int = None
):
    args = ...
   