from django.db import models
from utils.choises import CURRENCY_CHOISE
from .services.checko_bank import get_bank_data_by_bik, CheckoBankClientError
from .services.checko_company import get_company_data_by_inn, CheckoCompanyClientError
from mptt.models import MPTTModel, TreeForeignKey
from django.core.validators import RegexValidator


#----- СОБСТВЕННИКИ ----#
class Owners(models.Model):
    name = models.CharField(max_length=255, verbose_name="Наименование", unique=True)
    inn = models.CharField(max_length=255, verbose_name="ИНН", unique=True)
    kpp = models.CharField(max_length=255, verbose_name="КПП", null=True, blank=True)
    ogrn = models.CharField(max_length=255, verbose_name="ОГРН", null=True, blank=True)
    address = models.TextField(verbose_name="Адрес", null=True, blank=True)
    phone = models.CharField(
        max_length=255, verbose_name="Телефон", null=True, blank=True
    )
    email = models.EmailField(verbose_name="Email", null=True, blank=True)
    website = models.URLField(verbose_name="Сайт", null=True, blank=True)
    full_name = models.CharField(
        max_length=500,
        verbose_name="Полное наименование",
        null=True,
        blank=True,
    )
    ceo_name = models.CharField(
        max_length=255,
        verbose_name="Руководитель",
        null=True,
        blank=True,
    )
    ceo_post = models.CharField(
        max_length=255,
        verbose_name="Должность",
        null=True,
        blank=True,
    )
    ceo_record_date = models.CharField(
        max_length=20,
        verbose_name="Дата назначения",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Собственник"
        verbose_name_plural = "Собственники"

    def __str__(self):
        return self.name

    def fill_from_inn(self):
        if not self.inn:
            return

        try:
            data = get_company_data_by_inn(self.inn)
        except (CheckoCompanyClientError, Exception):
            return

        if not data:
            return

        self.kpp = data.get("kpp") or self.kpp
        self.ogrn = data.get("ogrn") or self.ogrn
        self.address = data.get("address") or self.address
        self.phone = data.get("phone") or self.phone
        self.email = data.get("email") or self.email
        self.website = data.get("website") or self.website
        self.full_name = data.get("full_name") or self.full_name
        self.ceo_name = data.get("ceo_name") or self.ceo_name
        self.ceo_post = data.get("ceo_post") or self.ceo_post
        self.ceo_record_date = data.get("ceo_record_date") or self.ceo_record_date



#----- БАНКИ ----#
class Bank(models.Model):
    name = models.CharField(max_length=255, verbose_name="Наименование")
    bik = models.CharField(max_length=9, verbose_name="БИК", unique=True)
    
    logo = models.CharField(
        max_length=1,
        verbose_name="Логотип (глиф)",
        null=True,
        blank=True,
        help_text="Символ-глиф банка",
    )
    
    address = models.TextField(verbose_name="Адрес", null=True, blank=True)
    corr_account = models.CharField(
        max_length=20, verbose_name="Кор. счёт", null=True, blank=True
    )
    inn = models.CharField(max_length=12, verbose_name="ИНН", null=True, blank=True)
    kpp = models.CharField(max_length=9, verbose_name="КПП", null=True, blank=True)
    type = models.CharField(max_length=50, verbose_name="Тип", null=True, blank=True)
    name_eng = models.CharField(
        max_length=255, verbose_name="Наименование (англ.)", null=True, blank=True
    )

    class Meta:
        verbose_name = "Банк"
        verbose_name_plural = "Банки"

    def __str__(self):
        return f"{self.name} ({self.bik})"


    def fill_from_bik(self):
        if not self.bik:
            return
        try:
            data = get_bank_data_by_bik(self.bik)
        except (CheckoBankClientError, Exception):
            return

        if not data:
            return

        self.name = data["name"]
        self.name_eng = data.get("name_eng") or self.name_eng
        self.address = data.get("address") or self.address
        self.corr_account = data.get("corr_account") or self.corr_account
        self.type = data.get("type") or self.type

    def save(self, *args, **kwargs):
        if self.bik and not self.name:
            self.fill_from_bik()
        super().save(*args, **kwargs)



#----- БАНКОВСКИЕ СЧЕТА ----#
class BankAccount(models.Model):

    corporate = models.ForeignKey(
        Owners, on_delete=models.CASCADE, verbose_name="Собственник"
    )
    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        verbose_name="Банк",
        related_name="accounts",
        null=True,
        blank=True,
    )
    bik = models.CharField(max_length=9, verbose_name="БИК")
    account = models.CharField(max_length=255, verbose_name="Счет", unique=True)
    currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOISE, verbose_name="Валюта", default="RUB"
    )

    class Meta:
        verbose_name = "Банковский счет"
        verbose_name_plural = "Банковские счета"

    def __str__(self):
        return f"{self.bank or self.bik} ({self.account})"

    def _fill_bank_from_bik(self):
        if not self.bik or self.bank_id:
            return

        try:
            bank_data = get_bank_data_by_bik(self.bik)
        except (CheckoBankClientError, Exception):
            return

        if not bank_data:
            return

        bank, _ = Bank.objects.get_or_create(
            bik=bank_data["bik"],
            defaults={
                "name": bank_data["name"],
                "name_eng": bank_data.get("name_eng"),
                "address": bank_data.get("address"),
                "corr_account": bank_data.get("corr_account"),
                "type": bank_data.get("type"),
            },
        )
        self.bank = bank

    def save(self, *args, **kwargs):
        if self.bik and not self.bank_id:
            self._fill_bank_from_bik()
        super().save(*args, **kwargs)


#----- CHART OF ACCOUNTS ----#



six_digits = RegexValidator(
    regex=r"^\d{6}$",
    message="Код должен состоять ровно из 6 цифр",
)

class COA(MPTTModel):
    code = models.CharField(
        "Код",
        max_length=6,
        unique=True,
        validators=[six_digits],
        help_text='6 цифр - уникальный'
    )
    name = models.CharField("Наименование", max_length=255)

    parent = TreeForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родитель",
    )

    is_active = models.BooleanField(default=True)
    
    desctiption = models.TextField("Описание",null=True,blank=True)

    class MPTTMeta:
        order_insertion_by = ["code"]

    class Meta:
        verbose_name = "Счет"
        verbose_name_plural = "План счетов"

    def __str__(self):
        return f"{self.code} {self.name}"


class СfItems(MPTTModel):
    code = models.CharField(
        "Код",
        max_length=6,
        unique=True,
        validators=[six_digits],
        help_text='6 цифр - уникальный'
    )
    name = models.CharField("Наименование", max_length=255)

    parent = TreeForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родитель",
    )

    is_active = models.BooleanField(default=True)
    
    desctiption = models.TextField("Описание",null=True,blank=True)

    class MPTTMeta:
        order_insertion_by = ["code"]

    class Meta:
        verbose_name = "Статья ДС"
        verbose_name_plural = "Статьи ДС"

    def __str__(self):
        return f"{self.code} {self.name}"