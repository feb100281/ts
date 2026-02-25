# contracts/models.py

from django.db import models
from corporate.models import Owners, CfItems
from counterparties.models import Counterparty
from django.conf import settings
import os
from django.utils.text import slugify
from macro.models import TaxesList
from django.core.exceptions import ValidationError
from django.db.models import Q
from utils.choises import CURRENCY_CHOISE
from decimal import Decimal



# Модели договоров.

# ----------------------------
# Типы договоров
# ----------------------------

class ContractsTitle(models.Model):
    title = models.CharField(max_length=250,verbose_name='Тип договора',unique=True)
    
    class Meta:
        verbose_name = "Тип договора"
        verbose_name_plural = "Типы договоров"

    def __str__(self):
        return self.title
    
    
 
 
class VatMode(models.TextChoices):
    INCLUDED = "included", "НДС включён"
    EXCLUDED = "excluded", "НДС сверху"
    EXEMPT = "exempt", "Без НДС / не облагается"
    UNKNOWN = "unknown", "Не задано"
    
    


class Contracts(models.Model):
    title = models.ForeignKey(ContractsTitle,on_delete=models.DO_NOTHING, verbose_name='Тип документа')
    number = models.CharField(max_length=250,verbose_name='Номер',null=True,blank=True)
    date = models.DateField(verbose_name='Дата договора',null=True,blank=True) 
    owner = models.ForeignKey(Owners,on_delete=models.CASCADE, verbose_name='Компания')
    cp = models.ForeignKey(Counterparty,on_delete=models.CASCADE,verbose_name='Контрагент')   
    date_signed = models.DateField(verbose_name='Дата подписания',null=True,blank=True)
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOISE,
        default="RUB",
        verbose_name="Валюта договора",
    )
    
    pid = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="amendments"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Менеджер договора',
        related_name='managed_by'
        # limit_choices_to={'groups__name': 'Подразделение'}
    )
    is_signed = models.BooleanField(verbose_name='Подписан',null=True,blank=True)
    regex =  models.TextField(verbose_name='RegEx',null=True,blank=True)
    
    class Meta:
        verbose_name = "Договор"
        verbose_name_plural = "Договоры"        

    def __str__(self):
        
        number = 'без номера' if not self.number else self.number
        date = 'без даты' if not self.date else self.date
        
        return f"{self.cp} {self.title} № {number} от {date} (id {self.id})"
    
    @property
    def is_amendment(self):
        return self.pid is not None
    
class ContractItems(models.Model):
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,verbose_name='Договор')
    item = models.CharField(max_length=550,verbose_name='Предмет договора',null=True,blank=True)
    
    class Meta:
        verbose_name = "Предмет договора"
        verbose_name_plural = "Предметы договоров"

    def __str__(self):
        return self.item
    
   


class AccountingMethod(models.Model):
    code = models.SlugField(max_length=50, unique=True, verbose_name="Код", blank=True)
    name = models.CharField(max_length=250, unique=True, verbose_name="Название")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    icon = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        verbose_name="Иконка/эмодзи",
        # help_text="Например: 🧾 или 💳 или ✅"
    )

    is_active = models.BooleanField(default=True, verbose_name="Активен?")

    class Meta:
        verbose_name = "Метод учёта"
        verbose_name_plural = "Методы учёта"
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = slugify(self.name)[:50]
        super().save(*args, **kwargs)
    
    
    

PERIOD_CHOICES = (
    ("week", "Неделя"),
    ("month", "Месяц"),
    ("quarter", "Квартал"),
    ("year", "Год"),
)

PAY_RULE_CHOICES = (
    ("month", "За месяц"),
    ("quarter", "За квартал"),
    ("half_year", "За полугодие"),
    ("year", "За год"),
    ("m2", "За 2 месяца"),
    ("m3", "За 3 месяца"),
    ("m4", "За 4 месяца"),
    ("custom", "Другое (см. params)"),
)

PAY_TIMING_CHOICES = (
    ("prepay", "Предоплата"),
    ("postpay", "Постоплата"),
)




class Conditions(models.Model):
    contract = models.ForeignKey(
        Contracts,
        on_delete=models.CASCADE,
        verbose_name="Договор",
        related_name="conditions",
    )
    
    
    
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Сумма"
    )
    
    period = models.CharField(
        max_length=10,
        choices=PERIOD_CHOICES,
        default="month",
        null=True,
        blank=True,
        verbose_name="Период начисления"
    )
    
    
    # ----------------------------
    # Оплата (платежный календарь)
    # ----------------------------
    pay_rule = models.CharField(
        max_length=20,
        choices=PAY_RULE_CHOICES,
        default="month",
        verbose_name="Период оплаты",
    )

    pay_timing = models.CharField(
        max_length=10,
        choices=PAY_TIMING_CHOICES,
        default="postpay",
        verbose_name="Тип оплаты",
    )

    pay_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="День оплаты",
        # help_text="Число месяца (1–31)"
    )

    pay_offset_months = models.IntegerField(
        default=1,
        verbose_name="Смещение",
        help_text="Напр. 1 = платить в след. мес"
    )

    pay_offset_days = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Смещение, дней",
        help_text="Напр. +10 дней от расчетной даты"
    )

    # ----------------------------
    # Неустойка
    # ----------------------------
    penalty_rate_day = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Неустойка, % в день",
        help_text="Напр. 0.1 = 0.1% в день"
    )

    date_start = models.DateField(verbose_name="Дата начала", null=True, blank=True)
    date_finish = models.DateField(verbose_name="Дата окончания", null=True, blank=True)

    accounting_method = models.ForeignKey(
        AccountingMethod,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Метод учёта",
        related_name="conditions",
    )

    # НДС: ссылка на налог + режим применения
    tax = models.ForeignKey(
        TaxesList,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Налог (например НДС)",
    )

    vat_mode = models.CharField(
        max_length=20,
        choices=VatMode.choices,
        default=VatMode.UNKNOWN,
        verbose_name="Режим НДС",
    )

    params = models.JSONField("Параметры", null=True, blank=True)

    class Meta:
        verbose_name = "Условие договора"
        verbose_name_plural = "Условия договоров"
        indexes = [
            models.Index(fields=["contract"]),
            models.Index(fields=["date_start", "date_finish"]),
        ]

    # def __str__(self):
    #     return f"Условия: {self.contract} ({self.date_start} - {self.date_finish or '∞'})"
    def __str__(self):
        c = self.contract

        cp = getattr(c.cp, "name", "") if c and c.cp_id else ""
        number = c.number or "без номера"
        cdate = c.date.strftime("%d.%m.%Y") if c and c.date else "без даты"

        start = self.date_start.strftime("%d.%m.%Y") if self.date_start else "—"
        finish = self.date_finish.strftime("%d.%m.%Y") if self.date_finish else "∞"

        period_txt = self.get_period_display() if self.period else ""
        pay_txt = self.get_pay_timing_display() if self.pay_timing else ""

        # метод учёта
        am = self.accounting_method
        if am:
            # если ты добавила icon в AccountingMethod — покажет её
            am_txt = f"{getattr(am, 'icon', '') or ''} {am.name}".strip()
        else:
            am_txt = "метод не задан"

        meta_parts = [x for x in [am_txt, period_txt, pay_txt] if x]
        meta = " • " + " • ".join(meta_parts) if meta_parts else ""

        # return f"Условия: {cp} • Договор № {number} от {cdate}{meta} (с {start} по {finish})"
        return f"Условия с {start} по {finish}: Договор № {number}{meta}"

    def clean(self):
        super().clean()

        if self.date_start and self.date_finish and self.date_finish < self.date_start:
            raise ValidationError({"date_finish": "Дата окончания не может быть раньше даты начала."})
        
        if self.pay_day is not None and not (1 <= self.pay_day <= 31):
            raise ValidationError({"pay_day": "День оплаты должен быть от 1 до 31."})

        # проверка пересечения периодов для одного договора
        if self.contract_id and self.date_start:
            qs = Conditions.objects.filter(contract_id=self.contract_id).exclude(pk=self.pk)

            start = self.date_start
            finish = self.date_finish

            overlap = qs.filter(Q(date_finish__isnull=True) | Q(date_finish__gte=start))
            if finish is not None:
                overlap = overlap.filter(date_start__lte=finish)

            if overlap.exists():
                raise ValidationError("Периоды условий пересекаются для этого договора.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    
  

class ContractFileType(models.TextChoices):
    CONTRACT = "contract", "Договор"
    ADDITIONAL = "additional", "Доп. соглашение"
    ACT = "act", "Акт"
    RECONCILIATION = "reconciliation", "Акт сверки"
    INVOICE = "invoice", "Счёт"
    OTHER = "other", "Другое"


def document_upload_path(instance, filename):
    contract = instance.contract

    cp_name = getattr(contract.cp, "name", None)
    cp = slugify(cp_name) if cp_name else str(contract.cp_id)

    number = slugify(contract.number) if contract.number else "б/н"
    date = contract.date.strftime("%Y-%m-%d") if contract.date else "б/д"

    doc_type = getattr(instance, "doc_type", None) or "other"
    return os.path.join("la", cp, f"{number}_{date}", doc_type, filename)

# class ContractFiles(models.Model):
#     contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,related_name='files')
#     description = models.TextField(verbose_name='описание',null=True,blank=True)
#     file = models.FileField(upload_to=document_upload_path, verbose_name="Файл документа", null=True, blank=True) 
    
#     class Meta:
#         verbose_name = "Файл"
#         verbose_name_plural = "Файлы"

#     def __str__(self):
#         if self.file:
#             return os.path.basename(self.file.name)
#         return self.description[:40] if self.description else "Файл"




class ContractFiles(models.Model):
    contract = models.ForeignKey(Contracts, on_delete=models.CASCADE, related_name="files")

    doc_type = models.CharField(
        max_length=32,
        choices=ContractFileType.choices,
        default=ContractFileType.OTHER,
        verbose_name="Тип документа",
    )
    doc_date = models.DateField(null=True, blank=True, verbose_name="Дата документа")
    doc_number = models.CharField(max_length=120, null=True, blank=True, verbose_name="Номер документа")

    description = models.TextField(verbose_name="Комментарий", null=True, blank=True)

    file = models.FileField(
        upload_to=document_upload_path,
        verbose_name="Файл",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"
        indexes = [
            models.Index(fields=["contract", "doc_type"]),
            models.Index(fields=["doc_date"]),
        ]

    def __str__(self):
        parts = []

        # Тип документа (человеческое название)
        if self.doc_type:
            parts.append(self.get_doc_type_display())

        # Номер
        if self.doc_number:
            parts.append(f"№ {self.doc_number}")

        # Дата
        if self.doc_date:
            parts.append(f"от {self.doc_date.strftime('%d.%m.%Y')}")

        # fallback — имя файла
        if not parts and self.file:
            return os.path.basename(self.file.name)

        return " — ".join(parts)
class CfItemAuto(models.Model):
    contract = models.ForeignKey(Contracts,on_delete=models.CASCADE,verbose_name='Договор')
    regex =  models.CharField(max_length=500,verbose_name='RegEx',null=True,blank=True)
    defaultcfdt = models.ForeignKey(CfItems,on_delete=models.CASCADE, verbose_name='Статья CF по дефолту для Дт',null=True,blank=True,related_name="contracts_default_dt", )
    defaultcfcr = models.ForeignKey(CfItems,on_delete=models.CASCADE, verbose_name='Статья CF по дефолту для Кт',null=True,blank=True,related_name="contracts_default_cr", )
    
    class Meta:
        verbose_name = "⚙️ Автоматизация"
        verbose_name_plural = "⚙️ Автоматизация"

    def __str__(self):
        return str(self.contract)

    
    
    