# budget/models.py
from django.db import models, connection
from django.conf import settings
from corporate.models import COA, CfItems
from contracts.models import Contracts 
import json



# Дефолтные JSON


def cf_json():
    sql = """
    WITH base AS (
    SELECT
        CASE
            WHEN item = '122000 Зачет расходов на реализацию WB' THEN 45
            ELSE 3
        END AS acc_id,
        subconto_id,
        item,
        regexp_replace(trim(subitem), '\s+', ' ', 'g') AS subitem,
        COALESCE(SUM(amount) FILTER (
            WHERE date_from >= current_date - interval '1 month'
        ), 0) AS m1,
        COALESCE(SUM(amount) FILTER (
            WHERE date_from >= current_date - interval '3 months'
        ) / 3.0, 0) AS m3,
        COALESCE(SUM(amount) FILTER (
            WHERE date_from >= current_date - interval '6 months'
        ) / 6.0, 0) AS m6
    FROM public.cf_to_csv
    GROUP BY
        subconto_id,
        item,
        regexp_replace(trim(subitem), '\s+', ' ', 'g')
),
subitems_json AS (
    SELECT
        item,
        jsonb_object_agg(
            subconto_id::text || ' | ' || subitem,
            jsonb_build_object(
                'acc_id', acc_id,
                'subconto_id', subconto_id,
                'subitem', subitem,
                'use', false,
                'means', jsonb_build_object(
                    '1M', jsonb_build_object('value', round(m1, 2), 'use', false),
                    '3M', jsonb_build_object('value', round(m3, 2), 'use', false),
                    '6M', jsonb_build_object('value', round(m6, 2), 'use', false),
                    'M fixed', jsonb_build_object('value', 0.0, 'use', false),
                    'Manual', jsonb_build_object(
                    'value', jsonb_build_array(
                        jsonb_build_object('2026-01-01', 0.0)
                    ),
                    'use', false
                )
                )
            )
        ) AS subitems
    FROM base
    GROUP BY item
)
SELECT jsonb_object_agg(
    item,
    jsonb_build_object(
        'use', false,
        'subitems', subitems
    )
)
FROM subitems_json;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

    data = row[0] if row else []

    if data is None:
        return []

    if isinstance(data, str):
        return json.loads(data)

    return data


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
        "monthly_adjustments": {
            "7": 1.20,
            "8": 1.10,
            "11": 1.10
        },

        "scenario": "base",
        "scenarios": {
            "base": 1.0,
            "optimistic": 1.10,
            "conservative": 0.90
        }
    }


def wbcost_json():
    return {
        "discout_vat_share": [{"historical": True, "n_monthes": 6, "Manual": 0.0}],
        "marketplace_comission": [{"historical": True, "n_monthes": 6,"Manual": 0.0}],
        "buyback_share": [{"historical": True, "n_monthes": 6,"Manual": 0.0}],
        "cost_per_unit": 0.0,
        "average_unit_price": [{"historical": True, "n_monthes": 6, "Manual": 0.0}],
        "delivery_unit_cost": [{"historical": True, "n_monthes": 6, "Manual": 0.0}],
        "storage_unit_costs": [{"historical": True, "n_monthes": 6, "Manual": 0.0}], 
        "penalty_unit_costs": [{"historical": True, "n_monthes": 6, "Manual": 0.0}],  
        "deduction": [{"historical": True, "n_monthes": 6, "Manual": 0.0}],  
        "cashback_commision": [{"historical": True, "n_monthes": 6, "Manual": 0.0}],
        "cashback_commision_programm_ratio": 10.0,           
    }


# class BudgetVersion(models.Model):
#     class BudgetType(models.TextChoices):
#         BASELINE = "baseline", "Базовый план"
#         ROLLING = "rolling", "Текущий прогноз"
#         ADHOC = "adhoc", "Ad-hoc"

#     number = models.CharField(
#         max_length=250,
#         unique=True,
#         verbose_name="Версия бюджета",
#     )
#     budget_type = models.CharField(
#         max_length=20,
#         choices=BudgetType.choices,
#         default=BudgetType.BASELINE,
#         verbose_name="Тип бюджета",
#     )
#     description = models.TextField(
#         blank=True,
#         verbose_name="Описание",
#     )
#     date_from = models.DateField(
#         verbose_name="Дата начала",
#     )
#     date_to = models.DateField(
#         verbose_name="Дата окончания",
#     )
#     revenue_param = models.JSONField(
#         default=revenue_json,
#         verbose_name="Параметры доходной части",
#     )
#     wb_costs_params = models.JSONField(
#         default=wbcost_json,
#         verbose_name="Параметры расходной части WB",
#     )
#     cf_params = models.JSONField(
#         default=cf_json,
#         verbose_name="Параметры планирования CF",
#     )
#     report = models.JSONField(
#         null=True, blank=True,
#         verbose_name="Отчет по бюджету",
#     )
    
    


#     class Meta:
#         verbose_name = "Версия бюджета"
#         verbose_name_plural = "Версии бюджетов"
#         ordering = ["-date_from", "number"]

#     def __str__(self):
#         return f"{self.number} | {self.get_budget_type_display()} | {self.date_from} - {self.date_to}"


class BudgetVersion(models.Model):
    class BudgetType(models.TextChoices):
        BASELINE = "baseline", "Базовый план"
        ROLLING = "rolling", "Текущий прогноз"
        ADHOC = "adhoc", "Ad-hoc"

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        APPROVED = "approved", "Утвержден"
        ARCHIVED = "archived", "Архив"

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
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус",
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
    cf_params = models.JSONField(
        default=cf_json,
        verbose_name="Параметры планирования CF",
    )
    report = models.JSONField(
        null=True, blank=True,
        verbose_name="Отчет по бюджету",
    )
    needs_recalculation = models.BooleanField(
        default=False,
        verbose_name="Требует пересчета",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата утверждения",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_budget_versions",
        verbose_name="Утвердил",
    )

    class Meta:
        verbose_name = "Версия бюджета"
        verbose_name_plural = "Версии бюджетов"
        ordering = ["-date_from", "number"]

    def __str__(self):
        return (
            f"{self.number} | {self.get_budget_type_display()} | "
            f"{self.get_status_display()} | {self.date_from} - {self.date_to}"
        )



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