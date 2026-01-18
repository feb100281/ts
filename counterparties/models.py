from django.db import models
from django.contrib.auth.models import User
from utils.choises import COUNTRY_CHOICES

class Gr(models.Model):
    name = models.CharField(max_length=30, verbose_name='Группа')
    description = models.TextField(null=True, blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Группа контрагентов'
        verbose_name_plural = 'Группы контрагентов'

    def __str__(self):
        return self.name


class Counterparty(models.Model):
    tax_id   = models.CharField(max_length=250, verbose_name='ИНН', unique=True)
    name     = models.CharField(max_length=250, verbose_name='Контрагент', db_index=True)
    logo     = models.CharField(max_length=10, verbose_name='Логотип (глиф)', blank=True, null=True)
    logo_svg = models.TextField(verbose_name='Логотип (SVG)', blank=True, null=True)
    gr       = models.ForeignKey('Gr', on_delete=models.PROTECT, verbose_name='Группа', null=True, blank=True)

    ceo = models.CharField(max_length=250, verbose_name='Руководитель', null=True, blank=True)
    ceo_post = models.CharField(max_length=250, verbose_name='Должность руководителя', null=True, blank=True)
    ceo_record_date = models.CharField(max_length=50, verbose_name='Дата записи в ЕГРЮЛ (рук.)', null=True, blank=True)
    ceo_hidden_by_fns = models.BooleanField(default=False, verbose_name='ФИО скрыто ФНС', null=True, blank=True)
    manager_is_org = models.BooleanField(default=False, verbose_name='Управляющая организация', null=True, blank=True)

    # --- ОКВЭД ---
    okved_code    = models.CharField("ОКВЭД (код)", max_length=20, blank=True, null=True)
    okved_name    = models.CharField("ОКВЭД (наименование)", max_length=350, blank=True, null=True)
    okved_version = models.CharField("ОКВЭД (версия)", max_length=10, blank=True, null=True)
    
    okopf_code = models.CharField("Код ОКОПФ", max_length=10, null=True,blank=True)
    okopf_name = models.CharField("Наименование ОПФ (ОКОПФ)", max_length=255, null=True,blank=True)

    # --- Факторы риска ---
    risk_disq_persons        = models.BooleanField("Дисквалифицированные лица", blank=True, null=True)
    risk_mass_directors      = models.BooleanField("Массовые руководители", blank=True, null=True)
    risk_mass_founders       = models.BooleanField("Массовые учредители", blank=True, null=True)
    risk_illegal_fin         = models.BooleanField("Нелегальная фин. деятельность", blank=True, null=True)
    risk_illegal_fin_status  = models.CharField("Статус нелегал. фин.", max_length=250, blank=True, null=True)
    risk_sanctions           = models.BooleanField("Санкции", blank=True, null=True)
    risk_sanctions_countries = models.CharField("Страны санкций (список)", max_length=500, blank=True, null=True)
    risk_sanctioned_founder  = models.BooleanField("Санкции в отношении учредителя", blank=True, null=True)
    risk_json = models.JSONField("Риски (сырые данные)", blank=True, null=True)

    was_notes = models.JSONField(default=dict, null=True, blank=True, verbose_name='История изменённых полей')
    adress = models.CharField(max_length=250, verbose_name='Адрес', blank=True, null=True)
    country = models.CharField(max_length=20, choices=COUNTRY_CHOICES, verbose_name='Страна', default='RU')
    email = models.CharField(max_length=250, null=True, blank=True)
    website = models.URLField(max_length=200, verbose_name='Сайт', blank=True, null=True)
    tel = models.CharField(max_length=250, verbose_name='Тел.', blank=True, null=True)
    ogrn = models.CharField(max_length=250, verbose_name='ОГРН', blank=True, null=True)
    kpp = models.CharField(max_length=250, verbose_name='КПП/ОКПО', blank=True, null=True)
    region = models.CharField(max_length=250, verbose_name='Регион', blank=True, null=True)
    fullname = models.CharField(max_length=350, verbose_name='Полн. Наименование', blank=True, null=True)
    taxregime = models.CharField(max_length=250, verbose_name='Налоговый режим', blank=True, null=True)
    
    
    checko_updated_at = models.DateTimeField(
        "Данные ФНС обновлены",
        null=True,
        blank=True,
        help_text="Дата последнего обновления данных из ФНС / Checko"
    )

    class Meta:
        verbose_name = 'Контрагент'
        verbose_name_plural = 'Контрагенты'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (ИНН: {self.tax_id})"
    
    def name_without_inn(self):
        return self.name


class Tenant(models.Model):
    user = models.OneToOneField(User, verbose_name='Ответ. лицо', on_delete=models.CASCADE, related_name="tenant")
    counterparty = models.OneToOneField(Counterparty, verbose_name='Контрагент', on_delete=models.CASCADE, related_name="tenant")

    class Meta:
        verbose_name = 'Кабинет контрагента'
        verbose_name_plural = 'Кабинеты контрагентов'
        ordering = ['counterparty']

    def __str__(self):
        return f"👤 Личный кабинет: {self.counterparty.name}"


class CounterpartyFinancialYear(models.Model):
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.CASCADE,
        related_name="financials",
        verbose_name="Контрагент",
    )
    year = models.PositiveIntegerField("Год", db_index=True)

    revenue = models.DecimalField("Выручка", max_digits=18, decimal_places=2, null=True, blank=True)
    net_profit = models.DecimalField("Чистая прибыль", max_digits=18, decimal_places=2, null=True, blank=True)
    equity = models.DecimalField("Собственный капитал", max_digits=18, decimal_places=2, null=True, blank=True)
    payables = models.DecimalField("Кредиторская задолженность", max_digits=18, decimal_places=2, null=True, blank=True)
    share_capital = models.DecimalField("Уставный капитал", max_digits=18, decimal_places=2, null=True, blank=True)

    cf_operating = models.DecimalField("ДДС от операц. деят-ти", max_digits=18, decimal_places=2, null=True, blank=True)
    
    liabilities_long = models.DecimalField(
        "Долгосрочные обязательства (1400)",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    liabilities_short = models.DecimalField(
        "Краткосрочные обязательства (1500)",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    source = models.CharField("Источник данных", max_length=100, blank=True, null=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Финансовый год контрагента"
        verbose_name_plural = "Финансовые годы контрагентов"
        # unique_together = ("counterparty", "year")
        ordering = ["-year"]

    def __str__(self):
        return f"{self.counterparty.name} – {self.year}"
