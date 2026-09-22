# budget/signals.py
# budget/signals.py
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import BudgetVersion
from .engine import main as make_budget
@receiver(post_save, sender=BudgetVersion)
def recalc_budget_after_save(sender, instance, **kwargs):
    transaction.on_commit(lambda: make_budget(instance.id))