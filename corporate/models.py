# corporate/models.py

from django.db import models
from .services.checko_bank import get_bank_data_by_bik, CheckoBankClientError
from .services.checko_company import get_company_data_by_inn, CheckoCompanyClientError
from mptt.models import MPTTModel, TreeForeignKey
from django.core.validators import RegexValidator
from utils.choises import CURRENCY_FLAGS, CURRENCY_SYMBOLS, CURRENCY_CHOISE
from copy import deepcopy


#----- СОБСТВЕННИКИ ----#
class Owners(models.Model):
    name = models.CharField(max_length=255, verbose_name="Наименование собственника", unique=True)
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
    bik = models.CharField(max_length=9, verbose_name="БИК", unique=True, help_text="9 цифр, без пробелов")
    
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

#----- Функции для работы с планом счетов ----#

class COAFn(models.Model):
    name = models.CharField(verbose_name='Имя функции', unique=True, max_length=100)
    python_path = models.CharField(verbose_name='Функция локальная', unique=True, max_length=250)
    server_path = models.CharField(verbose_name='Функция на сервере', unique=True, max_length=250)
    condition_template = models.JSONField(verbose_name='Параметры', default=dict)
    description = models.TextField(verbose_name='Описание', help_text='Описание обязательно')

    class Meta:
        verbose_name = "Функция плана счетов"
        verbose_name_plural = "Функции планов счетов"

    def __str__(self):
        return self.name



#----- CHART OF ACCOUNTS ----#

six_digits = RegexValidator(
    regex=r"^\d{6}$",
    message="Код должен состоять ровно из 6 цифр",
)


thre_digits = RegexValidator(
    regex=r"^\d{4}$",
    message="Код должен состоять ровно из 3 цифр",
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


class CfItems(MPTTModel):
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
    
    mapping = models.ForeignKey(COA,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Mapping',help_text='Маппинг для распределения по плану счетов')
    
    desctiption = models.TextField("Описание",null=True,blank=True)

    class MPTTMeta:
        order_insertion_by = ["code"]

    class Meta:
        verbose_name = "Статья ДС"
        verbose_name_plural = "Статьи ДС"

    def __str__(self):
        return f"{self.code} {self.name}"
    


#----- План счетов работа функции ----#

class ConditionsCOA(models.Model):
    coa = models.ForeignKey(
        COA,
        on_delete=models.CASCADE,
        verbose_name="Счет",
        related_name="conditions_source_acc",
    )

    fn = models.ForeignKey(
        COAFn,
        on_delete=models.SET_NULL,
        verbose_name='Функция плана счетов',
        null=True,
        blank=True
    )

    param_json = models.JSONField(
        verbose_name='Параметры',
        default=dict,
        blank=True
    )

    acc_pl = models.ForeignKey(
        COA,
        on_delete=models.SET_NULL,
        verbose_name='Счет PL',
        null=True,
        blank=True,
        related_name='conditions_pl_target'
    )

    subconto_pl = models.ForeignKey(
        CfItems,
        on_delete=models.SET_NULL,
        verbose_name='Субконто PL',
        null=True,
        blank=True,
        related_name='conditions_subconto_pl_target'
    )

    acc_bs = models.ForeignKey(
        COA,
        on_delete=models.SET_NULL,
        verbose_name='Счет BS',
        null=True,
        blank=True,
        related_name='conditions_bs_target'
    )

    subconto_bs = models.ForeignKey(
        CfItems,
        on_delete=models.SET_NULL,
        verbose_name='Субконто BS',
        null=True,
        blank=True,
        related_name='conditions_subconto_bs_target'
    )

    class Meta:
        verbose_name = "Списание"
        verbose_name_plural = "Списания"

    def __str__(self):
        return f"{self.coa} -> {self.fn or 'без функции'}"

    def save(self, *args, **kwargs):
        should_copy_template = False

        if self.fn_id:
            if self.pk is None:
                should_copy_template = True
            else:
                old = type(self).objects.filter(pk=self.pk).only("fn_id").first()
                if old and old.fn_id != self.fn_id:
                    should_copy_template = True

        if should_copy_template:
            self.param_json = deepcopy(self.fn.condition_template or {})

        self.full_clean()
        return super().save(*args, **kwargs)


    
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
    # bik = models.CharField(max_length=9, verbose_name="БИК")
    account = models.CharField(max_length=255, verbose_name="Счет", unique=True)
    currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOISE, verbose_name="Валюта", default="RUB"
    )
    bs_acc = models.ForeignKey(COA, verbose_name = "Балансовый счет", on_delete=models.CASCADE,null=True,blank=True)
    is_active = models.BooleanField('Активный',null=True,blank=True)

    class Meta:
        verbose_name = "Банковский счет"
        verbose_name_plural = "Банковские счета"

    # def __str__(self):
    #     return f"{self.bank} ({self.account})"
    def __str__(self):
        bank = self.bank.name if self.bank else "—"
        acc = self.account
        code = (self.currency or "").upper()
        flag = CURRENCY_FLAGS.get(code, "")
        sym = CURRENCY_SYMBOLS.get(code, "")
        return f"{bank} | {acc} • {flag}{sym} {code}".strip()

    
class Countries(models.Model):
    name = models.CharField(verbose_name='Наименование',max_length=100)
    code = models.CharField(max_length=3,verbose_name='Код старны',null=True,blank=True)
    emojy_flag = models.CharField(max_length=20,verbose_name='Флаг',null=True,blank=True)
    currency_code = models.CharField(max_length=3,verbose_name='Код валюты',null=True,blank=True)
    regex_patterns = models.TextField(verbose_name='Поисковая модель',null=True,blank=True,help_text='RegEx')
    
    class Meta:
        verbose_name = "География"
        verbose_name_plural = "География"

    def __str__(self): 
        return self.get_country
    
    @property
    def get_currency(self):
        if self.currency_code and self.emojy_flag:
            return f"{self.emojy_flag} {self.currency_code}"
        return self.name

    @property
    def get_country(self):
        if self.code and self.emojy_flag:
            return f"{self.emojy_flag} {self.code}"
        return self.name
           

class Subconto(MPTTModel):
    code = models.CharField(
        "Код",
        max_length=4,
        unique=True,
        validators=[thre_digits],
        help_text='4 цифры - уникальный'
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
    rgex = models.CharField("ReGex", max_length=255,null=True,blank=True)
    
    # mapping = models.ForeignKey(COA,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Mapping',help_text='Маппинг для распределения по плану счетов')
    
    desctiption = models.TextField("Описание",null=True,blank=True)

    class MPTTMeta:
        order_insertion_by = ["code"]

    class Meta:
        verbose_name = "Субконто"
        verbose_name_plural = "Субконто справочник"

    def __str__(self):
        return f"{self.code} {self.name}"