# grossbook/models.py
from django.db import models
from utils.choises import CURRENCY_CHOISE
from corporate.models import Owners,COA,CfItems
from contracts.models import Contracts
from counterparties.models import Counterparty
from django.conf import settings
from django.core.exceptions import ValidationError



#Модель для ручных проводок

class Manual(models.Model):
    id = models.BigAutoField(primary_key=True)

    pid = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="pid_manual"
    )
    date = models.DateField(verbose_name='Дата')
    owner = models.ForeignKey(Owners, on_delete=models.CASCADE,verbose_name='Компания')
    acc = models.ForeignKey(COA, on_delete=models.CASCADE,verbose_name='Счет')
    contract = models.ForeignKey(Contracts, on_delete=models.CASCADE,verbose_name='Договор')
    dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Дт',default=0.0)
    cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Кт',default=0.0)
    currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOISE, verbose_name="Валюта", default="RUB"
    )
    cfitem = models.ForeignKey(CfItems, on_delete=models.CASCADE,verbose_name='Статья CF',null=True,blank=True)
    temp = models.TextField(verbose_name='Описание операции')
    
    class Meta:        
        verbose_name = "Проводка"
        verbose_name_plural = "Ручные проводки"

    def __str__(self):
        return f"{self.date} на сумму: ({self.currency}{(self.dt - self.cr):,.0f})"
    
    
    
    


class LoanAdjustment(models.Model):
    """
    Контрольная точка управленческого расчёта займа.

    Это НЕ банковская операция и НЕ бухгалтерская проводка.
    На adjustment_date расчётный остаток займа принудительно
    устанавливается равным principal_balance и interest_balance.

    Со следующего календарного дня проценты начисляются уже
    на исправленный остаток тела.
    """

    class Reason(models.TextChoices):
        REPAYMENT_REALLOCATION = (
            "repayment_reallocation",
            "Исправление распределения платежа",
        )
        OPENING_BALANCE = (
            "opening_balance",
            "Корректировка начального остатка",
        )
        ACCOUNTING_RECONCILIATION = (
            "accounting_reconciliation",
            "Корректировка по результатам сверки",
        )
        OTHER = (
            "other",
            "Другое",
        )

    id = models.BigAutoField(primary_key=True)

    contract = models.ForeignKey(
        Contracts,
        on_delete=models.CASCADE,
        related_name="loan_adjustments",
        verbose_name="Договор",
    )

    adjustment_date = models.DateField(
        verbose_name="Дата корректировки",
        db_index=True,
    )

    principal_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Остаток тела после корректировки",
        help_text="Сумма в валюте договора, не в копейках.",
    )

    interest_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        verbose_name="Остаток процентов после корректировки",
        default=0,
        help_text="Сумма в валюте договора, не в копейках.",
    )

    reason = models.CharField(
        max_length=40,
        choices=Reason.choices,
        default=Reason.ACCOUNTING_RECONCILIATION,
        verbose_name="Причина",
    )

    comment = models.TextField(
        verbose_name="Комментарий",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Учитывать в расчёте",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_loan_adjustments",
        verbose_name="Создал",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Изменено",
    )

    class Meta:
        db_table = "grossbook_loanadjustment"
        verbose_name = "Корректировка займа"
        verbose_name_plural = "Корректировки займов"
        ordering = (
            "-adjustment_date",
            "-id",
        )
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "contract",
                    "adjustment_date",
                ),
                condition=models.Q(is_active=True),
                name="uniq_active_loan_adjustment_contract_date",
            ),
            models.CheckConstraint(
                condition=models.Q(principal_balance__gte=0),
                name="loan_adjustment_principal_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(interest_balance__gte=0),
                name="loan_adjustment_interest_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=(
                    "contract",
                    "adjustment_date",
                    "is_active",
                ),
                name="loan_adj_contract_date_idx",
            ),
        ]

    def clean(self):
        errors = {}

        if self.principal_balance is not None and self.principal_balance < 0:
            errors["principal_balance"] = (
                "Остаток тела не может быть отрицательным."
            )

        if self.interest_balance is not None and self.interest_balance < 0:
            errors["interest_balance"] = (
                "Остаток процентов не может быть отрицательным."
            )

        if not (self.comment or "").strip():
            errors["comment"] = "Укажите основание корректировки."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.adjustment_date} · {self.contract} · "
            f"тело {self.principal_balance:,.2f} · "
            f"проценты {self.interest_balance:,.2f}"
        )

    
    
            
    
# class Settlements(models.Model):
#     id = models.UUIDField(primary_key=True)
#     date_from = models.DateField(verbose_name='Дата')
#     pid = models.ForeignKey(Contracts,on_delete=models.DO_NOTHING,verbose_name='Основной договор',related_name='pid_contract', null=True,blank=True)
#     contract = models.ForeignKey(Contracts,on_delete=models.DO_NOTHING,verbose_name='Договор',related_name='contract', null=True,blank=True)
#     cp = models.ForeignKey(Counterparty,on_delete=models.DO_NOTHING,verbose_name='Контрагент',related_name='cp_name', null=True,blank=True)
#     st = models.ForeignKey(COA,on_delete=models.DO_NOTHING,verbose_name='Счет',related_name='account', null=True,blank=True)
#     description = models.TextField(verbose_name='Описание',null=True,blank=True)
#     dt = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Дт')
#     cr = models.DecimalField(max_digits=12,decimal_places=2,verbose_name='Кр')
    
#     class Meta:
#         managed = False
#         db_table = '"gl"."mv_accurals"'
#         verbose_name = "Взаиморасчеты"
#         verbose_name_plural = "Взаиморасчеты"

#     def __str__(self):
#         return f"{self.date_from:} на сумму: ({(self.dt - self.cr):,.0f})"
    

