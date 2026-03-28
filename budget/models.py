from django.db import models
from corporate.models import COA, CfItems
from contracts.models import Contracts 



# Дефолтные JSON

def revenue_json():
    return {
        "seasonality_mode": "multiplicative",
        "changepoint_prior_scale": 0.08,
        "seasonality_prior_scale": 10.0,
        "holidays_prior_scale": 10.0,
        "interval_width": 0.8,
        "yearly_seasonality": True,
        "weekly_seasonality": True,
        "daily_seasonality": False,
        "add_monthly_seasonality": True,
        "monthly_period": 30.5,
        "monthly_fourier_order": 5,
    }


def wbcost_json():
    return {
        "Discount VAT share": [{"12M calculation": True, "Manual": 0.0}],
        "Marketplace Comission": [{"12M calculation": True, "Manual": 0.0}],
        "Cost Per Unit": 0.0,
        "Average Unit Price": [{"12M calculation": True, "Manual": 0.0}],
        "Delivery Fee costs per unit sold": [{"12M calculation": True, "Manual": 0.0}],
        "Storage Fee costs per unit sold": [{"12M calculation": True, "Manual": 0.0}],
        "Marketplace cost escalator": 0.0,
    }


class BudgetVersion(models.Model):
    class BudgetType(models.TextChoices):
        BASELINE = "baseline", "Базовый план"
        ROLLING = "rolling", "Текущий прогноз"
        ADHOC = "adhoc", "Ad-hoc"

    number = models.CharField(
        max_length=250,
        unique=True,
        verbose_name="Версия бюджета",
    )
    budget_type = models.CharField(
        max_length=20,
        choices=BudgetType.choices,
        default=BudgetType.BASELINE,
        verbose_name="Тип бюджета",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
    )
    date_from = models.DateField(
        verbose_name="Дата начала",
    )
    date_to = models.DateField(
        verbose_name="Дата окончания",
    )
    revenue_param = models.JSONField(
        default=revenue_json,
        verbose_name="Параметры доходной части",
    )
    wb_costs_params = models.JSONField(
        default=wbcost_json,
        verbose_name="Параметры расходной части WB",
    )

    class Meta:
        verbose_name = "Версия бюджета"
        verbose_name_plural = "Версии бюджетов"
        ordering = ["-date_from", "number"]

    def __str__(self):
        return f"{self.number} | {self.get_budget_type_display()} | {self.date_from} - {self.date_to}"


class Gl(models.Model):
    version = models.ForeignKey(
        BudgetVersion,
        on_delete=models.CASCADE,
        related_name="gl_entries",
        verbose_name="Версия бюджета",
    )
    date = models.DateField(
        verbose_name="Дата",
    )
    acc = models.ForeignKey(
        COA,
        on_delete=models.CASCADE,
        related_name="gl_entries",
        verbose_name="Счет",
    )
    subconto = models.ForeignKey(
        CfItems,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="gl_entries",
        verbose_name="Субконто",
    )
    contract = models.ForeignKey(
        Contracts,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="gl_entries",
        verbose_name="Договор",
    )
    dt = models.BigIntegerField(
        default=0,
        verbose_name="Дебет, коп.",
    )
    cr = models.BigIntegerField(
        default=0,
        verbose_name="Кредит, коп.",
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Описание",
    )
    chapter = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Раздел",
    )

    class Meta:
        verbose_name = "Проводка GL"
        verbose_name_plural = "Проводки GL"
        ordering = ["date", "id"]
        indexes = [
            models.Index(fields=["version", "date"]),
            models.Index(fields=["acc"]),
            models.Index(fields=["contract"]),
            models.Index(fields=["subconto"]),
        ]

    def __str__(self):
        return f"{self.date} | {self.acc} | dt={self.dt} cr={self.cr}"